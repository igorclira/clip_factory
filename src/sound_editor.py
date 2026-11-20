"""
Clip Factory — Dedicated Sound Editor (Rule-Checked JSON Sound Plan + Peak Alignment)

Extracts timeline clip_events from a Remotion props JSON (accounting for 8-frame
TransitionSeries overlap), feeds clip_events + sound_library.json + music_library.json +
config/sound_rules.md + recent_sound_plans.json into Gemini, enforces all sound_rules.md
constraints programmatically (valid files, meme density, no stacking, variety, peak_sec
sync 1 frame early), saves sound_plan_<channel>_<date>.json, updates recent_sound_plans.json,
and injects `soundPlan` into the Remotion props file.

Usage:
    python src/sound_editor.py --props <remotion_props.json> --project-dir <channel_dir>
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from gemini_utils import get_available_models, log_token_usage

CORE_ROOT = Path(__file__).resolve().parent.parent
SHARED_DIR = CORE_ROOT / "shared_assets"
SOUND_LIB_PATH = SHARED_DIR / "sound_library.json"
MUSIC_LIB_PATH = SHARED_DIR / "music_library.json"
TRANSITION_FRAMES = 8


class CutPoint(BaseModel):
    start_s: float = Field(description="Start second on global timeline to drop music -15 dB before punchline")
    end_s: float = Field(description="End second on global timeline when music returns")


class MusicPlan(BaseModel):
    file: str = Field(description="Exact filename from music_library.json (or empty string if none fits)")
    start_s: float = Field(default=0.0, description="Start offset in seconds inside the music track")
    gain_db: float = Field(default=-18.0, description="Base music gain in dB (typically -16 to -22)")
    duck_under_game_audio_db: float = Field(default=-10.0, description="Additional dB ducking (-8 to -12) during important game audio/speech")
    cut_points: list[CutPoint] = Field(default_factory=list, description="0.3-0.6s music drops before punchlines")


PlacementType = Literal[
    "on_impact",
    "after_impact",
    "before_moment",
    "under_freeze_frame",
    "end_card",
    "bed",
]
MontageModeType = Literal["funny", "action", "hybrid"]


class SoundEvent(BaseModel):
    t: float = Field(description="Exact global timeline second of the target visual event")
    file: str = Field(description="Exact filename from sound_library.json")
    category: Literal["impact", "transition", "meme", "sfx"]
    placement: PlacementType = Field(
        default="on_impact",
        description="Timing intent: on_impact (0ms), after_impact (+250ms reaction beat), before_moment (anticipation/riser), under_freeze_frame, end_card, or bed",
    )
    trigger: str = Field(
        default="",
        description="Matching trigger moment (e.g. fail, crash, anticlimax, overkill, chase, flex, awkward_silence, betrayal, escape, kill, near_miss, cliffhanger)",
    )
    gain_db: float = Field(default=0.0, description="Gain adjustment in dB (-12 to +3)")
    reason: str = Field(description="Specific clip_event or beat_tag this sound answers, tying library meaning to the moment")


class FinalMix(BaseModel):
    target_lufs: float = Field(default=-14.0)
    true_peak_db: float = Field(default=-1.0)


class SoundPlan(BaseModel):
    montage_mode: MontageModeType = Field(default="funny")
    music: MusicPlan
    events: list[SoundEvent]
    final_mix: FinalMix


def load_feedback_constraints(project_dir: Path) -> tuple[set[tuple[str, str]], set[str], list[dict[str, str]]]:
    """Read optional feedback/placements.csv to extract banned (sound_id, trigger) pairs, disabled sounds, and boosted pairs."""
    csv_path = project_dir / "feedback" / "placements.csv"
    if not csv_path.is_file():
        return set(), set(), []

    rows: list[dict[str, str]] = []
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rows.append(row)
    except Exception as exc:
        print(f"  [Feedback] Could not read {csv_path}: {exc}")
        return set(), set(), []

    low_counts: Counter[str] = Counter()
    recent_video_ids: list[str] = []
    for r in rows:
        vid = (r.get("video_id") or "").strip()
        if vid and (not recent_video_ids or recent_video_ids[-1] != vid):
            recent_video_ids.append(vid)
    recent_window = set(recent_video_ids[-20:])

    banned_pairs: set[tuple[str, str]] = set()
    boosted_seen: set[tuple[str, str]] = set()
    boosted_pairs: list[dict[str, str]] = []

    for r in rows:
        sid = (r.get("sound_id") or "").strip()
        trig = (r.get("trigger") or "").strip()
        vid = (r.get("video_id") or "").strip()
        try:
            rating = int(float(r.get("rating") or 0))
        except ValueError:
            continue
        if not sid:
            continue
        if rating <= 2:
            low_counts[sid] += 1
            if vid in recent_window and trig:
                banned_pairs.add((sid, trig))
        elif rating >= 5 and trig and (sid, trig) not in boosted_seen:
            boosted_seen.add((sid, trig))
            boosted_pairs.append({"sound_id": sid, "trigger": trig})

    disabled_sounds = {sid for sid, cnt in low_counts.items() if cnt >= 3}
    return banned_pairs, disabled_sounds, boosted_pairs


def extract_clip_events(props: dict[str, Any]) -> tuple[float, list[dict[str, Any]], list[dict[str, Any]]]:
    """Map per-segment cues onto global composition seconds (matching TransitionSeries timing)."""
    fps = float(props.get("fps") or 30)
    trans_sec = TRANSITION_FRAMES / fps
    segs = props.get("segments") or []

    events: list[dict[str, Any]] = []
    speech_windows: list[dict[str, Any]] = []
    cursor = 0.0

    for idx, seg in enumerate(segs):
        rate = float(seg.get("playbackRate") or 1.0)
        dur = max(0.5, (float(seg["endSec"]) - float(seg["startSec"])) / rate)
        prev = segs[idx - 1] if idx > 0 else None
        is_jump = bool(prev and prev.get("author") == seg.get("author"))
        trans_kind = seg.get("transitionIn") or ("none" if is_jump else "slide")

        if idx > 0 and trans_kind != "none":
            cursor = max(0.0, cursor - trans_sec)
            events.append({
                "t": round(cursor, 2),
                "type": "cut",
                "detail": f"Transition ({trans_kind}) into @{seg.get('author', 'creator')}",
            })
        elif idx > 0:
            events.append({
                "t": round(cursor, 2),
                "type": "jump_cut",
                "detail": f"Jump cut inside @{seg.get('author', 'creator')}",
            })

        if idx == 0:
            events.append({
                "t": 0.05,
                "type": "hook",
                "detail": f"Opening frame hook (@{seg.get('author', 'creator')})",
            })

        for z in seg.get("zooms") or []:
            events.append({
                "t": round(cursor + float(z["atSec"]), 2),
                "type": "zoom",
                "detail": f"Camera zoom ({z.get('mode', 'smooth')} {z.get('scale', 1.25)}x) in @{seg.get('author')}",
            })

        for sh in seg.get("shakes") or []:
            events.append({
                "t": round(cursor + float(sh["atSec"]), 2),
                "type": "impact",
                "detail": f"Impact / screen shake in @{seg.get('author')}",
            })

        for cap in seg.get("captions") or []:
            c_start = round(cursor + float(cap["startSec"]), 2)
            c_end = round(cursor + float(cap["endSec"]), 2)
            if cap.get("role") == "editorial":
                events.append({
                    "t": c_start,
                    "type": "punchline",
                    "detail": f"Editorial comedic popup '{cap.get('text')}' in @{seg.get('author')}",
                })
            else:
                speech_windows.append({
                    "start_s": c_start,
                    "end_s": c_end,
                    "speaker": cap.get("role"),
                    "text": cap.get("text"),
                })

        for fr in seg.get("freezes") or []:
            events.append({
                "t": round(cursor + float(fr["atSec"]), 2),
                "type": "freeze",
                "detail": f"Freeze frame ({fr.get('durationSec', 1.5)}s) in @{seg.get('author')}",
            })

        for si in seg.get("silences") or []:
            s_start = round(cursor + float(si["startSec"]), 2)
            s_end = round(cursor + float(si["endSec"]), 2)
            events.append({
                "t": s_start,
                "type": "silence",
                "detail": f"AudioVacuum silence ({s_start:.2f}-{s_end:.2f}s) in @{seg.get('author')}",
            })

        for bt in seg.get("beatTags") or []:
            events.append({
                "t": round(cursor + float(bt.get("atSec", 0.0)), 2),
                "type": "beat_tag",
                "detail": (
                    f"[{bt.get('trigger', '')}/{bt.get('humor_type', 'none')}/E{bt.get('energy', 3)}] "
                    f"{bt.get('note', '')} (@{seg.get('author')})"
                ),
            })

        if seg.get("bgmFile"):
            events.append({
                "t": round(cursor, 2),
                "type": "bgm_override_segment",
                "detail": f"Segment plays custom music '{seg['bgmFile']}' from {round(cursor,2)}s to {round(cursor+dur,2)}s",
            })

        cursor += dur

    total_duration = round(cursor, 2)
    events.append({
        "t": round(max(0.5, total_duration - 0.35), 2),
        "type": "ending",
        "detail": "Final punchline / clean ending button to help video loop",
    })
    events.sort(key=lambda x: x["t"])
    return total_duration, events, speech_windows


def extract_segment_summaries(props: dict[str, Any]) -> list[dict[str, Any]]:
    """Build per-segment comedy & dialogue summaries across ALL segments (global timeline seconds)."""
    fps = float(props.get("fps") or 30)
    trans_sec = TRANSITION_FRAMES / fps
    segs = props.get("segments") or []

    summaries: list[dict[str, Any]] = []
    cursor = 0.0

    for idx, seg in enumerate(segs):
        rate = float(seg.get("playbackRate") or 1.0)
        dur = max(0.5, (float(seg["endSec"]) - float(seg["startSec"])) / rate)
        prev = segs[idx - 1] if idx > 0 else None
        is_jump = bool(prev and prev.get("author") == seg.get("author"))
        trans_kind = seg.get("transitionIn") or ("none" if is_jump else "slide")

        if idx > 0 and trans_kind != "none":
            cursor = max(0.0, cursor - trans_sec)

        seg_start = round(cursor, 2)
        seg_end = round(cursor + dur, 2)

        # Group consecutive same-speaker caption chunks into readable dialogue turns
        turns: list[dict[str, Any]] = []
        for cap in seg.get("captions") or []:
            role = cap.get("role", "streamer")
            if role == "editorial":
                continue
            c_start = round(cursor + float(cap["startSec"]), 2)
            c_end = round(cursor + float(cap["endSec"]), 2)
            txt = str(cap.get("text") or "").strip()
            if not txt:
                continue
            if turns and turns[-1]["role"] == role and (c_start - turns[-1]["end_s"]) <= 0.65:
                turns[-1]["end_s"] = c_end
                turns[-1]["text"] += f" {txt}"
            else:
                turns.append({"role": role, "start_s": c_start, "end_s": c_end, "text": txt})

        dialogue_lines = [
            f"[{t['role']} {t['start_s']:.2f}-{t['end_s']:.2f}s] {t['text']}"
            for t in turns
        ]
        zoom_modes = [
            f"{z.get('mode', 'smooth')} {z.get('scale', 1.25)}x @{round(cursor + float(z['atSec']), 2)}s"
            for z in (seg.get("zooms") or [])
        ]
        editorial_popups = [
            f"'{c.get('text')}' @{round(cursor + float(c['startSec']), 2)}s"
            for c in (seg.get("captions") or [])
            if c.get("role") == "editorial"
        ]
        beat_tags = [
            {
                "t": round(cursor + float(bt.get("atSec", 0.0)), 2),
                "trigger": bt.get("trigger", ""),
                "humor_type": bt.get("humor_type", "none"),
                "energy": bt.get("energy", 3),
                "placement_hint": bt.get("placement_hint", "on_impact"),
                "note": bt.get("note", ""),
            }
            for bt in (seg.get("beatTags") or [])
        ]

        summaries.append({
            "id": seg.get("id", f"seg_{idx+1}"),
            "author": seg.get("author", "creator"),
            "start_s": seg_start,
            "end_s": seg_end,
            "playbackRate": rate,
            "has_bgm_override": bool(seg.get("bgmFile")),
            "comedy_beat_summary": seg.get("comedyBeatSummary", ""),
            "beat_tags": beat_tags,
            "zoom_modes": zoom_modes,
            "editorial_popups": editorial_popups,
            "dialogue_lines": dialogue_lines,
        })
        cursor += dur

    return summaries


def call_gemini_resilient(client: genai.Client, models: list[str], prompt: str) -> SoundPlan:
    last_err: Exception | None = None
    for attempt in range(3):
        for m in models:
            try:
                print(f"[SoundEditor] Designing sound plan ({m})...")
                resp = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=SoundPlan,
                        temperature=0.35,
                    ),
                )
                log_token_usage("SoundEditor", m, resp)
                return SoundPlan.model_validate_json(resp.text)
            except Exception as exc:
                last_err = exc
                err_str = str(exc)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "404" in err_str:
                    print(f"  [Fallback] {m} exhausted/unavailable; switching immediately...")
                    continue
                wait_s = 6 * (attempt + 1)
                print(f"  [Fallback] {m} failed ({err_str[:120]}); waiting {wait_s}s...")
                time.sleep(wait_s)
    raise RuntimeError(f"SoundEditor failed across all models: {last_err}")


def build_compact_sounds(
    sound_lib: list[dict[str, Any]],
    montage_mode: MontageModeType = "funny",
    disabled_sounds: set[str] | None = None,
    allow_gta_native: bool = False,
) -> list[dict[str, Any]]:
    """Return curated semantic roster filtered by mode, bans, and length (playback capped via max_duration_s)."""
    disabled_sounds = disabled_sounds or set()

    def _mode_compatible(sound_mode: str) -> bool:
        if montage_mode == "hybrid":
            return True
        return sound_mode in (montage_mode, "both")

    fields = (
        "id",
        "file",
        "category",
        "meaning",
        "trigger_moments",
        "humor_type",
        "montage_mode",
        "energy",
        "placement",
        "copyright_risk",
        "freshness",
        "dedupe_group",
        "length_s",
        "align_mode",
    )
    out: list[dict[str, Any]] = []
    for s in sound_lib:
        if not s.get("curated_semantic"):
            continue
        if not _mode_compatible(s.get("montage_mode", "both")):
            continue
        if not allow_gta_native and s.get("gta_native"):
            continue
        if s.get("id") in disabled_sounds or s["file"] in disabled_sounds:
            continue
        is_meme = s.get("category") == "meme"
        is_long_ok = s.get("placement") in ("bed", "end_card", "before_moment")
        ok_len = (not is_meme) or is_long_ok or float(s.get("length_s") or 0) <= 12.0
        if not ok_len:
            continue
        out.append({k: s.get(k) for k in fields})
    return out


def compute_hybrid_turn_t(segment_summaries: list[dict[str, Any]] | None, total_duration: float) -> float:
    """Return the comedic turn timestamp for hybrid mode: latest fail/anticlimax/cliffhanger beat_tag, else last 30s."""
    turn_triggers = {"fail", "anticlimax", "cliffhanger"}
    candidates: list[float] = []
    for seg in segment_summaries or []:
        for bt in seg.get("beat_tags") or []:
            if str(bt.get("trigger", "")).strip().lower() in turn_triggers:
                candidates.append(float(bt.get("t", 0.0)))
    if candidates:
        return max(candidates)
    return max(0.0, total_duration - 30.0)


def enforce_rules_and_align(
    raw_plan: SoundPlan,
    sound_by_file: dict[str, dict[str, Any]],
    music_by_file: dict[str, dict[str, Any]],
    recently_used_memes: set[str],
    total_duration: float,
    montage_mode: MontageModeType = "funny",
    banned_pairs: set[tuple[str, str]] | None = None,
    disabled_sounds: set[str] | None = None,
    allow_gta_native: bool = False,
    segment_summaries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate against sound_library/music_library & enforce mode-aware rules, dedupe groups, copyright caps & alignment."""
    banned_pairs = banned_pairs or set()
    disabled_sounds = disabled_sounds or set()

    music_dict = raw_plan.music.model_dump()
    if music_dict["file"] and music_dict["file"] not in music_by_file:
        print(f"  [Guardrail] Dropped invalid music file '{music_dict['file']}'")
        music_dict["file"] = ""
    music_dict["gain_db"] = max(-28.0, min(-8.0, float(music_dict["gain_db"])))
    music_dict["duck_under_game_audio_db"] = max(-18.0, min(-4.0, float(music_dict["duck_under_game_audio_db"])))
    cut_points: list[dict[str, float]] = list(music_dict.get("cut_points") or [])

    # Mode-aware meme caps (funny: max 3 per 30s capped at 4; action: max 1 per 30s capped at 2; hybrid: max 2)
    if montage_mode == "action":
        max_memes = min(2, max(1, round(1.0 * total_duration / 30.0)))
    elif montage_mode == "hybrid":
        max_memes = 2
    else:
        max_memes = min(4, max(3, round(3.0 * total_duration / 30.0)))

    hybrid_turn_t = compute_hybrid_turn_t(segment_summaries, total_duration) if montage_mode == "hybrid" else 0.0

    # Sort candidate events chronologically
    sorted_events = sorted(raw_plan.events, key=lambda e: e.t)

    # Build case-insensitive alias lookup (preferring curated_semantic entries on stem collisions)
    sound_by_alias: dict[str, dict[str, Any]] = {}
    for m in sorted(sound_by_file.values(), key=lambda x: bool(x.get("curated_semantic"))):
        keys = [m["file"], Path(m["file"]).stem]
        if m.get("id"):
            sid = str(m["id"])
            keys.extend([sid, f"{sid}.mp3", f"{sid}.wav"])
        for k in keys:
            sound_by_alias[k.strip().lower()] = m

    accepted: list[dict[str, Any]] = []
    game_duck_windows: list[dict[str, float]] = []
    used_memes_in_video: set[str] = set()
    used_dedupe_groups: set[str] = set()
    last_meme_t = -999.0
    meme_count = 0
    high_copyright_count = 0

    for ev in sorted_events:
        meta = sound_by_file.get(ev.file) or sound_by_alias.get(ev.file.strip().lower())
        if not meta:
            print(f"  [Guardrail] Dropped unknown sound '{ev.file}'")
            continue
        resolved_file = meta["file"]
        if resolved_file != ev.file:
            print(f"  [Alias] Resolved '{ev.file}' -> '{resolved_file}'")

        sound_id = meta.get("id", Path(resolved_file).stem)
        trigger = (ev.trigger or "").strip().lower()
        copyright_risk = meta.get("copyright_risk", "medium")
        dedupe_group = meta.get("dedupe_group", "")

        if meta.get("gta_native") and not allow_gta_native:
            print(f"  [Guardrail GTA] Skipped GTA-native stinger '{resolved_file}'")
            continue
        if sound_id in disabled_sounds or resolved_file in disabled_sounds:
            print(f"  [Guardrail Feedback] Skipped disabled sound '{sound_id}' (3+ low ratings)")
            continue
        if trigger and (sound_id, trigger) in banned_pairs:
            print(f"  [Guardrail Feedback] Skipped banned pair ({sound_id}, {trigger})")
            continue
        if copyright_risk == "high" and high_copyright_count >= 2:
            print(f"  [Guardrail Copyright] Skipped '{resolved_file}' (already hit max 2 high-risk sounds)")
            continue

        t = round(max(0.0, min(total_duration - 0.1, float(ev.t))), 3)
        cat = meta["category"]

        # Rule #8, #3 & Hybrid turn gating
        if cat == "meme":
            if montage_mode == "hybrid" and t < hybrid_turn_t - 0.05:
                print(f"  [Guardrail Hybrid] Skipped meme '{resolved_file}' at {t}s (before turn_t={hybrid_turn_t:.2f}s)")
                continue
            if resolved_file in recently_used_memes:
                print(f"  [Guardrail R8] Skipped '{resolved_file}' (used in last 3 videos)")
                continue
            if resolved_file in used_memes_in_video:
                print(f"  [Guardrail R8] Skipped duplicate meme '{resolved_file}' in same video")
                continue
            if dedupe_group and dedupe_group in used_dedupe_groups:
                print(f"  [Guardrail Dedupe] Skipped '{resolved_file}' (near-duplicate group '{dedupe_group}' already used)")
                continue
            if meme_count >= max_memes:
                print(f"  [Guardrail R3] Skipped '{resolved_file}' (already hit max {max_memes} memes for mode={montage_mode})")
                continue
            if t - last_meme_t < 5.0:
                print(f"  [Guardrail R3] Skipped '{resolved_file}' at {t}s (<5s since previous meme at {last_meme_t}s)")
                continue

        # Rule #7: No stacking (no 2 memes or >2 SFX within 0.5s)
        nearby = [a for a in accepted if abs(a["t"] - t) < 0.5]
        if cat == "meme" and any(a["category"] == "meme" for a in nearby):
            print(f"  [Guardrail R7] Skipped stacked meme '{resolved_file}' at {t}s")
            continue
        if len(nearby) >= 2:
            print(f"  [Guardrail R7] Skipped '{resolved_file}' at {t}s (>2 SFX within 0.5s)")
            continue

        # Rule #2 + Semantic placement: combine placement intent with acoustic onset/peak alignment
        placement = ev.placement or meta.get("placement", "on_impact")
        align_mode = meta.get("align_mode", "peak")
        length_s = float(meta.get("length_s") or 1.0)

        if placement in ("bed", "end_card", "before_moment"):
            max_duration_s = round(min(length_s, 10.0), 3)
        elif cat == "meme":
            max_duration_s = round(min(length_s, 2.4), 3)
        else:
            max_duration_s = round(min(length_s, 4.0), 3)

        effective_t = t
        if placement == "after_impact":
            effective_t = min(total_duration - 0.1, t + 0.25)
        elif placement == "before_moment":
            lead = min(3.0, max(0.4, length_s if align_mode != "onset" else max(length_s, 0.45)))
            effective_t = max(0.0, t - lead)

        if align_mode == "onset":
            onset_sec = float(meta.get("onset_sec") or 0.0)
            raw_play = effective_t - onset_sec
        else:
            peak_sec = float(meta.get("peak_sec") or 0.0)
            raw_play = effective_t - peak_sec - 0.033

        if raw_play >= 0.0:
            play_at_s = round(raw_play, 3)
            trim_start_s = 0.0
        else:
            play_at_s = 0.0
            trim_start_s = round(min(max(0.0, -raw_play), max(0.0, length_s - 0.25)), 3)

        if cat == "meme" and (total_duration - play_at_s) < min(0.9, max_duration_s * 0.55):
            print(f"  [Guardrail Tail] Skipped meme '{resolved_file}' at {play_at_s}s (only {total_duration - play_at_s:.2f}s left before video end)")
            continue

        accepted.append({
            "t": t,
            "play_at_s": play_at_s,
            "trim_start_s": trim_start_s,
            "max_duration_s": max_duration_s,
            "file": resolved_file,
            "sound_id": sound_id,
            "category": cat,
            "placement": placement,
            "trigger": trigger,
            "copyright_risk": copyright_risk,
            "gain_db": max(-15.0, min(4.0, round(float(ev.gain_db), 1))),
            "reason": ev.reason,
        })
        if copyright_risk == "high":
            high_copyright_count += 1
        if cat == "meme":
            used_memes_in_video.add(resolved_file)
            if dedupe_group:
                used_dedupe_groups.add(dedupe_group)
            last_meme_t = t
            meme_count += 1
            game_duck_windows.append({
                "start_s": round(play_at_s, 3),
                "end_s": round(min(total_duration, play_at_s + max_duration_s), 3),
                "db": -10,
            })
            if placement in ("after_impact", "under_freeze_frame", "end_card"):
                c_start = round(max(0.0, t - 0.35), 3)
                c_end = round(t, 3)
                has_overlap = any(
                    not (c_end < float(cp["start_s"]) or c_start > float(cp["end_s"]))
                    for cp in cut_points
                )
                if not has_overlap and c_end > c_start:
                    cut_points.append({"start_s": c_start, "end_s": c_end})

    cut_points.sort(key=lambda c: c["start_s"])
    music_dict["cut_points"] = cut_points

    return {
        "montage_mode": montage_mode,
        "music": music_dict,
        "events": accepted,
        "game_duck_windows": game_duck_windows,
        "final_mix": {
            "target_lufs": -14.0,
            "true_peak_db": -1.0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Dedicated Rule-Checked Sound Editor")
    parser.add_argument("--props", type=Path, required=True, help="Path to remotion_props_*.json")
    parser.add_argument("--project-dir", type=Path, required=True, help="Channel project directory")
    parser.add_argument("--out-plan", type=Path, default=None, help="Optional output path for sound_plan JSON")
    parser.add_argument("--model", default=None, help="Optional Gemini model override")
    parser.add_argument(
        "--mode",
        choices=["auto", "funny", "action", "hybrid"],
        default="auto",
        help="Montage sound mode ('auto' reads props.montageMode, defaulting to 'funny')",
    )
    parser.add_argument("--allow-gta-native", action="store_true", help="Allow GTA-native stingers (Wasted, CJ, etc.)")
    parser.add_argument("--keep-segment-sfx", action="store_true", help="Keep legacy per-segment sfx arrays")
    parser.add_argument("--ignore-recent", action="store_true", help="Ignore recent_sound_plans.json when iterating the same video")
    args = parser.parse_args()

    load_dotenv(CORE_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY missing in clip_factory/.env")

    props_path = args.props.resolve()
    project_dir = args.project_dir.resolve()
    props = json.loads(props_path.read_text(encoding="utf-8"))
    channel_id = props.get("channelId", "gta6")
    montage_mode: MontageModeType = (
        args.mode if args.mode != "auto" else props.get("montageMode", "funny")
    )
    if montage_mode not in ("funny", "action", "hybrid"):
        montage_mode = "funny"
    run_date = next((p for p in props_path.stem.split("_") if len(p) == 10 and p.count("-") == 2), dt.datetime.now().strftime("%Y-%m-%d"))

    sound_lib = json.loads(SOUND_LIB_PATH.read_text(encoding="utf-8"))
    music_lib = json.loads(MUSIC_LIB_PATH.read_text(encoding="utf-8"))
    sound_by_file = {item["file"]: item for item in sound_lib}
    music_by_file = {item["file"]: item for item in music_lib}

    rules_path = project_dir / "config" / "sound_rules.md"
    if not rules_path.is_file():
        raise SystemExit(f"Missing required sound rules file: {rules_path}")
    sound_rules_md = rules_path.read_text(encoding="utf-8")

    banned_pairs, disabled_sounds, boosted_pairs = load_feedback_constraints(project_dir)

    recent_path = project_dir / "workspace" / "03_analysis" / "recent_sound_plans.json"
    recent_plans = json.loads(recent_path.read_text(encoding="utf-8")) if recent_path.exists() else []
    recently_used_memes: set[str] = set()
    if not args.ignore_recent:
        same_video_prefix = f"remotion_props_{channel_id}_{run_date}"
        other_recent = [
            prev for prev in recent_plans
            if not str(prev.get("props_file", "")).startswith(same_video_prefix)
        ]
        for prev in other_recent[-3:]:
            recently_used_memes.update(prev.get("meme_files", []))

    total_duration, clip_events, speech_windows = extract_clip_events(props)
    segment_summaries = extract_segment_summaries(props)
    hook_info = {
        "montage_mode": montage_mode,
        "duration_s": total_duration,
        "hook_0_to_2s": [e for e in clip_events if e["t"] <= 2.2] + [s for s in speech_windows if s["start_s"] <= 2.2],
    }

    compact_sounds = build_compact_sounds(
        sound_lib,
        montage_mode=montage_mode,
        disabled_sounds=disabled_sounds,
        allow_gta_native=args.allow_gta_native,
    )

    prompt = f"""
You are the Sound Editor for `{channel_id}` (9:16 TikTok & YouTube Shorts). Video editing is already handled. Your only job is sound: SFX, punchy mainstream pop-culture memes/reactions, and music.

## Mode & Context
- montage_mode: `{montage_mode}`
  - `funny`: humor is the point (max 3 memes per 30s, capped at 4; reactions, references, ironic stings; SFX as glue).
  - `action`: pace & impact (max 1 meme per 30s, capped at 2; risers, whooshes, bass drops, impacts, announcer calls).
  - `hybrid`: play it straight with action SFX until the comedic turn/fail, then drop 1–2 earned memes on the payoff!
- duration_s and hook (first 2s):
{json.dumps(hook_info, indent=2)}

- segment_summaries (FULL comedic context, structured `beat_tags`, zoom modes, editorial popups, and streamer/NPC dialogue across EVERY segment):
{json.dumps(segment_summaries, indent=2, ensure_ascii=False)}

- clip_events (exact global timestamps):
{json.dumps(clip_events, indent=2)}

- recently_used_memes (DO NOT REUSE any of these — Rule #8):
{json.dumps(sorted(recently_used_memes))}

- feedback_banned_pairs (DO NOT USE these sound_id + trigger pairs):
{json.dumps([{"sound_id": sid, "trigger": tr} for sid, tr in sorted(banned_pairs)])}

- feedback_boosted_pairs (previously rated 5/5 — prefer when fitting):
{json.dumps(boosted_pairs)}

- music_library.json:
{json.dumps(music_lib, indent=2)}

- sound_library.json (curated semantic roster, {len(compact_sounds)} files):
{json.dumps(compact_sounds, separators=(',', ':'))}

- Current rules ({rules_path.name}):
{sound_rules_md}

## Strict Instructions
- LIBRARY LOCK: Choose ONLY exact `file` values from `sound_library.json` and `music_library.json`. Never invent filenames.
- MEANING IS THE JOKE: For every beat (`beat_tags` or `comedy_beat_summary`), match `trigger_moments`, `humor_type`, and `energy` (±1), and read `meaning` in plain English. The sound must *comment on the situation* like a human editor — silence is better than a forced meme.
- COPYRIGHT & DEDUPE DISCIPLINE: Prefer lower `copyright_risk` when two sounds tell the same joke (max 2 `high`-risk sounds per short). Never pick two memes from the same `dedupe_group` in one short. Prefer `evergreen` unless a beat explicitly calls for `trending_2025_2026`.
- **NEVER talk over the funniest streamer or NPC line!** Place spoken voice blips in speech gaps, right after a setup line (`placement: "after_impact"`), or right at a slow-mo/impact onset using `dialogue_lines` timestamps.
- Always put `-15dB` music `cut_points` (`0.3-0.5s` of clean audio) right before major comedic payoffs so the meme pops cleanly.
- Notice if a segment has `has_bgm_override: true` (`bgm_override_segment`), keep global music supportive for the rest of the montage.
- For `events`, specify `t` as the exact visual/comedic beat timestamp and set `placement` accurately (`on_impact`, `after_impact`, `before_moment`, `under_freeze_frame`, `end_card`, `bed`) plus `trigger`. Our engine automatically combines your `placement` intent with each file's measured `onset_sec` / `peak_sec`.
  1. Hook boom/impact on `t=0.05` (Rule #1)
  2. Whooshes on clip `cut` transitions (Rule #2)
  3. Earned, hilarious memes on real `beat_tags` / `punchline` payoffs (in `funny` mode on a 60–85s montage, aim for 3 to 4 distinct segments' comedic `beat_tags` spread >=5s apart across the video; zero stacking, zero duplicate `dedupe_group`)
  4. A crisp short impact hit (NOT a 2s spoken/music meme) on `ending` (Rule #9) — never start a meme with <1.0s left before video end.
- Each event's `reason` must tie the chosen sound's `meaning` to a specific `beat_tag`, `clip_event`, or `segment_summaries` moment.
"""

    client = genai.Client(api_key=api_key)
    avail = get_available_models(client)
    models = ([args.model] if args.model else []) + [
        m for m in ("gemini-3.8-flash", "gemini-3.1-pro-preview", "gemini-3.5-flash-lite") if m in avail and m != args.model
    ]

    raw_plan = call_gemini_resilient(client, models, prompt)
    final_plan = enforce_rules_and_align(
        raw_plan,
        sound_by_file,
        music_by_file,
        recently_used_memes,
        total_duration,
        montage_mode=montage_mode,
        banned_pairs=banned_pairs,
        disabled_sounds=disabled_sounds,
        allow_gta_native=args.allow_gta_native,
        segment_summaries=segment_summaries,
    )

    out_plan_path = args.out_plan or (project_dir / "workspace" / "03_analysis" / f"sound_plan_{channel_id}_{run_date}.json")
    out_plan_path.parent.mkdir(parents=True, exist_ok=True)
    out_plan_path.write_text(json.dumps(final_plan, indent=2, ensure_ascii=False), encoding="utf-8")

    # Update recent_sound_plans.json for Rule #8 variety tracking
    recent_plans.append({
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "props_file": props_path.name,
        "music_file": final_plan["music"]["file"],
        "meme_files": [e["file"] for e in final_plan["events"] if e["category"] == "meme"],
        "events_count": len(final_plan["events"]),
    })
    recent_path.write_text(json.dumps(recent_plans[-25:], indent=2, ensure_ascii=False), encoding="utf-8")

    # Inject soundPlan directly into Remotion props JSON
    props["soundPlan"] = final_plan
    if not args.keep_segment_sfx:
        for seg in props.get("segments", []):
            seg["sfx"] = []
    props_path.write_text(json.dumps(props, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nDone! Sound plan saved -> {out_plan_path}")
    print(f"  Music:  {final_plan['music']['file']} (gain={final_plan['music']['gain_db']}dB, cuts={len(final_plan['music']['cut_points'])})")
    print(f"  Events: {len(final_plan['events'])} rule-checked events ({sum(1 for e in final_plan['events'] if e['category']=='meme')} memes)")
    for ev in final_plan["events"]:
        print(f"    - {ev['play_at_s']:5.2f}s | {ev['category']:10s} | {ev['sound_id']} ({ev['placement']}, {ev['trigger'] or '-'})")
    print(f"  Injected `soundPlan` into {props_path.name}")
    print(f"  Rate these in {project_dir / 'feedback' / 'placements.csv'}")


if __name__ == "__main__":
    main()
