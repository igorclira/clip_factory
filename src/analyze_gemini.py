"""
Clip Factory — Stage 2 (V2): CHM × Red Arcade Multimodal Director (Gemini API -> Remotion Props)

Reads curated_selection_*.json, ensures all selected clips exist locally, runs faster-whisper
via FFmpeg PCM decode, uploads all clips to Gemini Files API so Gemini watches video + audio
together, applies the Classic Hardcore Moments × Red Arcade rubric (directional bounding-box
SnapZoomBox coordinates, ImpactShake, AudioVacuum silence drops, DespairFreeze, TargetSpotlight
'!' alerts/circles, and color-coded Streamer / Funny NPC / Editorial captions), and outputs BOTH:
  - workspace/03_analysis/edit_plan_<channel>_<date>.json (human-readable director plan + curation scores)
  - workspace/03_analysis/remotion_props_<channel>_<date>.json (ready to render directly in Remotion!)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Literal

import numpy as np
import requests
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from gemini_utils import get_available_models, log_token_usage

CORE_ROOT = Path(__file__).resolve().parent.parent


class ZoomCue(BaseModel):
    atSec: float = Field(description="Relative second inside trimmed segment")
    durationSec: float = Field(default=1.0, description="Duration of zoom hold (0.7-2.4s)")
    scale: float = Field(
        default=1.28,
        description="Mode-appropriate zoom scale: aggressive_punch 1.75-2.05, slow_creep 1.45-1.70, snap_hold 1.45-1.75, smooth 1.20-1.40",
    )
    originX: float = Field(description="EXACT horizontal subject coordinate 0-100% (0=left, 50=center, 100=right)")
    originY: float = Field(description="EXACT vertical subject coordinate 0-100% (0=top, 50=center, 100=bottom)")
    mode: Literal["aggressive_punch", "slow_creep", "snap_hold", "smooth"] = Field(
        default="smooth",
        description="Vary per comedic beat: aggressive_punch for brutal hits/mauls, slow_creep for slow-mo disbelief, snap_hold for punchlines, smooth for subtle focus",
    )


class ShakeCue(BaseModel):
    atSec: float = Field(description="Exact impact/climax second inside trimmed segment")
    intensity: int = Field(default=14)
    durationFrames: int = Field(default=8)


class SilenceCue(BaseModel):
    startSec: float = Field(description="CHM AudioVacuum start (0.3-0.4s before impact)")
    endSec: float = Field(description="AudioVacuum end (exact frame of impact)")


class FreezeCue(BaseModel):
    atSec: float = Field(description="Exact fatal/comedy freeze second inside trimmed segment")
    durationSec: float = Field(default=1.4)
    monochrome: bool = Field(default=True)


class SpotlightCue(BaseModel):
    atSec: float
    durationSec: float = Field(default=1.1)
    x: float = Field(description="Subject X coordinate 0-100%")
    y: float = Field(description="Subject Y coordinate 0-100%")
    radius: int = Field(default=78)
    kind: Literal["circle", "alert"] = Field(description="'alert' for Metal Gear '!' icon, 'circle' for animated red ring")


class SfxCue(BaseModel):
    atSec: float = Field(description="Relative second inside trimmed segment")
    sfxTag: str = Field(description="Exact key from available meme_map.json sfx map")
    volume: float = Field(default=0.9)
    reason: str = Field(description="Why this SFX hits here")


class WordCue(BaseModel):
    text: str
    startSec: float
    endSec: float


class CaptionCue(BaseModel):
    startSec: float = Field(description="Relative start second inside trimmed segment")
    endSec: float = Field(description="Tight anti-lingering end second (cut immediately when speech ends!)")
    text: str = Field(description="1 to 3 punchy words max")
    role: Literal["streamer", "npc", "editorial"]
    words: list[WordCue] | None = Field(
        default=None,
        description="Per-word timestamps for karaoke highlighting (matching Whisper timestamps)",
    )
    x: float | None = Field(default=None, description="Optional contextual X% (Red Arcade action callout)")
    y: float | None = Field(default=None, description="Optional contextual Y% (Red Arcade action callout)")
    rotateDeg: float | None = Field(default=None, description="Optional slight tilt (-8 to 8 deg)")


class BeatTag(BaseModel):
    atSec: float = Field(description="Relative second inside trimmed segment where this comedic/action beat lands")
    trigger: Literal[
        "fail",
        "near_miss",
        "anticlimax",
        "overkill",
        "chase",
        "flex",
        "awkward_silence",
        "betrayal",
        "escape",
        "crash",
        "kill",
        "cliffhanger",
    ] = Field(description="Situational trigger type matching sound_library trigger_moments")
    humor_type: Literal["irony", "escalation", "anticlimax", "reaction", "absurd", "none"] = Field(
        default="reaction",
        description="Comedic mechanism (or 'none' for pure action hype)",
    )
    energy: int = Field(default=3, ge=1, le=5, description="Beat intensity from 1 (quiet/deadpan) to 5 (explosive)")
    placement_hint: Literal[
        "on_impact",
        "after_impact",
        "before_moment",
        "under_freeze_frame",
        "end_card",
        "bed",
    ] = Field(default="on_impact", description="Timing intent relative to the visual beat")
    note: str = Field(description="Short plain-English description of the SITUATION (never name a sound file)")


class SegmentPlan(BaseModel):
    clip_id: str
    source_file: str
    platform: Literal["tiktok", "youtube", "twitch", "reddit"]
    author: str
    curation_score: int = Field(description="0-100 score using CHM × Red Arcade rubric")
    archetype: str = Field(description="e.g. IronicHubris, RogueNPC, PhysicsAnomaly, SelfSabotage, RaidPanic")
    comedy_beat_summary: str = Field(
        default="",
        description="1-sentence description of what makes this segment funny and where the punchline lands",
    )
    beat_tags: list[BeatTag] = Field(
        default_factory=list,
        description="1 to 3 structured comedic/action beat tags handed off to sound_editor.py",
    )
    startSec: float = Field(description="In Medias Res start second inside source_file (0s-2.5s into action)")
    endSec: float = Field(description="Out-point 0.6-2.0s AFTER punchline registers (never cut on a cliffhanger!)")
    cropZoom: float = Field(default=1.0, description=">1.0 ONLY if source video has baked-in black bars (prefer letterboxCrop when 16:9/4:3)")
    streamerCaptionY: int = Field(default=27, description="Top Y% near streamer's mouth (default 27; adjust to avoid baked TikTok banners)")
    playbackRate: float = Field(default=1.0, description="Segment speed multiplier (e.g. 0.58-0.68 for slow-mo disbelief payoff; default 1.0)")
    transitionIn: Literal["slide", "wipe", "none"] | None = Field(
        default=None,
        description="Transition entering this segment ('none' for same-creator slow-mo splits)",
    )
    isolate_vocals: bool = Field(default=False, description="True if GTA car radio or copyrighted/unfitting background music is audible")
    zooms: list[ZoomCue] = Field(default_factory=list)
    shakes: list[ShakeCue] = Field(default_factory=list)
    silences: list[SilenceCue] = Field(default_factory=list)
    freezes: list[FreezeCue] = Field(default_factory=list)
    spotlights: list[SpotlightCue] = Field(default_factory=list)
    sfx: list[SfxCue] = Field(default_factory=list)
    captions: list[CaptionCue] = Field(default_factory=list)
    editorial_rationale: str


class MontagePlan(BaseModel):
    channel_id: str
    theme: str
    montage_mode: Literal["funny", "action", "hybrid"] = Field(
        default="funny",
        description="Overall audio tone: 'funny' (comedy-first), 'action' (hype/pace), or 'hybrid' (serious buildup into comedic turn)",
    )
    title: str
    caption_hashtags: list[str]
    total_target_seconds: float
    segments: list[SegmentPlan]


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:80]


def get_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]
    return float(subprocess.check_output(cmd).decode().strip())


def decode_audio_ffmpeg(video_path: Path, sr: int = 16000) -> np.ndarray:
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(video_path),
        "-f", "f32le", "-acodec", "pcm_f32le", "-ac", "1", "-ar", str(sr), "-",
    ]
    raw = subprocess.check_output(cmd)
    return np.frombuffer(raw, dtype=np.float32)


def download_missing_tiktoks(clips: list[dict[str, Any]], inbox_dir: Path) -> None:
    missing = [c for c in clips if c.get("platform") == "tiktok" and not c.get("local_file")]
    if not missing:
        return
    token = os.getenv("APIFY_TOKEN", "").strip()
    if not token:
        print("[Apify] Cannot download missing TikTok clips — APIFY_TOKEN not set.")
        return

    urls = [c["url"] for c in missing if c.get("url")]
    print(f"[Apify] Downloading {len(urls)} selected TikTok clip(s) via Apify...")
    endpoint = "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"postURLs": urls, "shouldDownloadVideos": True, "resultsPerPage": len(urls)}
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=240)
    resp.raise_for_status()
    items = resp.json()

    by_id = {
        str(item.get("id")): (item.get("mediaUrls") or [None])[0]
        for item in items
        if item.get("id") and item.get("mediaUrls")
    }
    for c in missing:
        cid = str(c["clip_id"])
        dl_url = by_id.get(cid)
        if not dl_url:
            continue
        out_path = inbox_dir / f"tiktok_{sanitize_filename(cid)}.mp4"
        dl_headers = {"Authorization": f"Bearer {token}"} if "api.apify.com" in dl_url else {}
        try:
            with requests.get(dl_url, headers=dl_headers, stream=True, timeout=90) as r:
                r.raise_for_status()
                with out_path.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
            if out_path.stat().st_size > 10_000:
                c["local_file"] = out_path.name
                print(f"  [Apify] Saved {out_path.name}")
            else:
                out_path.unlink(missing_ok=True)
        except requests.RequestException as exc:
            print(f"  [Apify] Download failed for tiktok/{cid}: {exc}")
            out_path.unlink(missing_ok=True)


def transcribe_all(clips: list[dict[str, Any]], inbox_dir: Path) -> dict[str, list[dict[str, Any]]]:
    print("[Whisper] Extracting word-level timestamps locally...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    transcripts: dict[str, list[dict[str, Any]]] = {}
    for c in clips:
        lf = c.get("local_file")
        if not lf:
            continue
        video_path = inbox_dir / lf
        if not video_path.exists():
            continue
        audio_np = decode_audio_ffmpeg(video_path)
        segments, _ = model.transcribe(audio_np, word_timestamps=True)
        words = [
            {"word": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)}
            for seg in segments
            for w in (seg.words or [])
        ]
        transcripts[lf] = words
        print(f"  [Whisper] {lf}: {len(words)} words")
    return transcripts


def build_whisper_captions(
    words: list[dict[str, Any]], seg_start: float, seg_end: float, max_words: int = 3, pause_gap: float = 0.25
) -> list[dict[str, Any]]:
    """Auto-chunk Whisper word timestamps into tight 1-3 word karaoke captions with zero lingering."""
    rel: list[dict[str, Any]] = []
    for w in words:
        if float(w["end"]) <= seg_start or float(w["start"]) >= seg_end or not str(w.get("word", "")).strip():
            continue
        w_start = round(max(0.0, float(w["start"]) - seg_start), 2)
        raw_end = round(min(seg_end - seg_start, float(w["end"]) - seg_start), 2)
        # Clamp abnormally stretched Whisper words (e.g. held syllables across silence gaps)
        if raw_end - w_start > 1.35:
            raw_end = round(min(seg_end - seg_start, w_start + 0.85), 2)
        w_end = max(round(w_start + 0.08, 2), raw_end)
        rel.append({
            "word": str(w["word"]).strip(),
            "start": w_start,
            "end": w_end,
        })
    if not rel:
        return []

    def emit_chunk(buf: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "startSec": buf[0]["start"],
            "endSec": round(max(buf[-1]["end"], buf[0]["start"] + 0.25), 2),
            "text": " ".join(x["word"] for x in buf),
            "role": "streamer",
            "words": [
                {"text": x["word"], "startSec": x["start"], "endSec": x["end"]}
                for x in buf
            ],
        }

    chunks: list[dict[str, Any]] = []
    buf: list[dict[str, Any]] = []
    for w in rel:
        if buf and (len(buf) >= max_words or (w["start"] - buf[-1]["end"]) > pause_gap):
            chunks.append(emit_chunk(buf))
            buf = []
        buf.append(w)
    if buf:
        chunks.append(emit_chunk(buf))
    return chunks


def _attach_karaoke_words(
    cap: dict[str, Any], seg_words: list[dict[str, Any]], seg_start: float, playback_rate: float = 1.0
) -> dict[str, Any]:
    """Ensure streamer/npc captions carry word-level karaoke timings (preferring Whisper alignment)."""
    if cap.get("role") not in ("streamer", "npc") or cap.get("words"):
        return cap
    tokens = str(cap.get("text") or "").split()
    if not tokens:
        return cap

    c_start = float(cap["startSec"])
    c_end = max(c_start + 0.15, float(cap["endSec"]))
    rate = playback_rate if playback_rate and playback_rate > 0 else 1.0

    # Match Whisper words inside this caption window (accounting for playback_rate)
    matched: list[dict[str, Any]] = []
    for w in seg_words:
        ws = round((float(w["start"]) - seg_start) / rate, 2)
        we = round((float(w["end"]) - seg_start) / rate, 2)
        if we >= c_start - 0.12 and ws <= c_end + 0.12 and str(w.get("word", "")).strip():
            clamped_end = min(c_end, max(ws + 0.08, min(we, ws + 1.35)))
            matched.append({
                "text": str(w["word"]).strip(),
                "startSec": round(max(c_start, ws), 2),
                "endSec": round(clamped_end, 2),
            })

    if len(matched) == len(tokens):
        cap["words"] = [
            {"text": tok, "startSec": m["startSec"], "endSec": max(m["endSec"], round(m["startSec"] + 0.08, 2))}
            for tok, m in zip(tokens, matched)
        ]
    else:
        # Proportional duration split across tokens so karaoke highlighting stays smooth
        total_chars = sum(max(1, len(t)) for t in tokens)
        span = max(0.25, c_end - c_start)
        cursor_t = c_start
        word_cues = []
        for idx, tok in enumerate(tokens):
            share = span * (max(1, len(tok)) / total_chars)
            w_end = c_end if idx == len(tokens) - 1 else round(cursor_t + share, 2)
            word_cues.append({
                "text": tok,
                "startSec": round(cursor_t, 2),
                "endSec": round(max(cursor_t + 0.08, w_end), 2),
            })
            cursor_t = w_end
        cap["words"] = word_cues
    return cap


def merge_user_meme_markers(plan: MontagePlan, clips: list[dict[str, Any]]) -> None:
    """Merge user-stamped MEME markers from review_sheet.html into segment beat_tags (preferring user fields within 0.4s)."""
    markers_by_clip: dict[str, list[dict[str, Any]]] = {}
    for c in clips:
        key = str(c.get("local_file") or c.get("clip_id") or "")
        if key:
            markers_by_clip[key] = list(c.get("markers") or [])

    valid_triggers = {
        "fail", "near_miss", "anticlimax", "overkill", "chase", "flex",
        "awkward_silence", "betrayal", "escape", "crash", "kill", "cliffhanger",
    }
    valid_humors = {"irony", "escalation", "anticlimax", "reaction", "absurd", "none"}

    for seg in plan.segments:
        raw_markers = markers_by_clip.get(seg.source_file) or markers_by_clip.get(seg.clip_id) or []
        rate = float(seg.playbackRate or 1.0) or 1.0
        out_dur = max(0.0, (float(seg.endSec) - float(seg.startSec)) / rate)

        for mk in raw_markers:
            if str(mk.get("type", "")).upper() != "MEME":
                continue
            try:
                src_sec = float(mk["sec"])
            except (KeyError, TypeError, ValueError):
                continue
            at_sec = round((src_sec - float(seg.startSec)) / rate, 2)
            if at_sec < 0.0 or at_sec > out_dur:
                continue

            trig = str(mk.get("trigger") or "fail").strip().lower()
            if trig not in valid_triggers:
                trig = "fail"
            hum = str(mk.get("humor_type") or "reaction").strip().lower()
            if hum not in valid_humors:
                hum = "reaction"
            try:
                eng = max(1, min(5, int(mk.get("energy") or 3)))
            except (TypeError, ValueError):
                eng = 3
            note = str(mk.get("note") or "User-stamped comedic beat").strip()

            new_tag = BeatTag(
                atSec=at_sec,
                trigger=trig,  # type: ignore[arg-type]
                humor_type=hum,  # type: ignore[arg-type]
                energy=eng,
                placement_hint="on_impact",
                note=note,
            )
            matched_idx = next(
                (idx for idx, existing in enumerate(seg.beat_tags) if abs(existing.atSec - at_sec) <= 0.4),
                None,
            )
            if matched_idx is not None:
                seg.beat_tags[matched_idx] = new_tag
            else:
                seg.beat_tags.append(new_tag)
        seg.beat_tags.sort(key=lambda bt: bt.atSec)


def plan_to_remotion_props(
    plan: MontagePlan,
    sfx_map: dict[str, Any],
    channel_id: str | None = None,
    transcripts: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    cid = channel_id or plan.channel_id
    theme = "gta6_vaporwave" if "gta" in cid.lower() else "wow_classic"
    remotion_segments = []
    for idx, seg in enumerate(plan.segments, start=1):
        resolved_sfx = []
        for s in seg.sfx:
            entry = sfx_map.get(s.sfxTag)
            if isinstance(entry, dict):
                filename = entry.get("filename") or entry.get("file")
                peak_sec = float(entry.get("peak_sec") or 0.0)
                if filename:
                    aligned_start = round(max(0.0, s.atSec - peak_sec), 3)
                    resolved_sfx.append({"atSec": aligned_start, "file": filename, "volume": s.volume})
            elif isinstance(entry, str):
                resolved_sfx.append({"atSec": s.atSec, "file": entry, "volume": s.volume})

        seg_whisper = (transcripts or {}).get(seg.source_file, [])
        rate = float(seg.playbackRate or 1.0)

        # Dual-track captions: ensure continuous Whisper streamer speech if Gemini emitted <3 speech captions
        captions = [
            _attach_karaoke_words(cap.model_dump(exclude_none=True), seg_whisper, seg.startSec, rate)
            for cap in seg.captions
        ]
        speech_cnt = sum(1 for c in captions if c.get("role") in ("streamer", "npc"))
        if speech_cnt < 3 and seg_whisper:
            auto_caps = build_whisper_captions(seg_whisper, seg.startSec, seg.endSec)
            if abs(rate - 1.0) > 0.01:
                for ac in auto_caps:
                    ac["startSec"] = round(ac["startSec"] / rate, 2)
                    ac["endSec"] = round(ac["endSec"] / rate, 2)
                    for wc in ac.get("words") or []:
                        wc["startSec"] = round(wc["startSec"] / rate, 2)
                        wc["endSec"] = round(wc["endSec"] / rate, 2)
            editorial_only = [c for c in captions if c.get("role") == "editorial"]
            captions = sorted(auto_caps + editorial_only, key=lambda x: x["startSec"])

        has_dialogue = any(c.get("role") in ("streamer", "npc") for c in captions)
        video_vol = 1.0
        if seg.isolate_vocals:
            video_vol = 0.55 if has_dialogue else 0.25

        seg_dict: dict[str, Any] = {
            "id": f"seg_{idx:02d}_{sanitize_filename(seg.author)}",
            "videoFile": seg.source_file,
            "platform": seg.platform,
            "author": seg.author,
            "startSec": seg.startSec,
            "endSec": seg.endSec,
            "cropZoom": seg.cropZoom,
            "streamerCaptionY": seg.streamerCaptionY,
            "isolateVocals": seg.isolate_vocals,
            "videoVolume": video_vol,
            "comedyBeatSummary": seg.comedy_beat_summary,
            "beatTags": [bt.model_dump() for bt in seg.beat_tags],
            "zooms": [z.model_dump() for z in seg.zooms],
            "shakes": [sh.model_dump() for sh in seg.shakes],
            "silences": [si.model_dump() for si in seg.silences],
            "freezes": [fr.model_dump() for fr in seg.freezes],
            "spotlights": [sp.model_dump() for sp in seg.spotlights],
            "sfx": resolved_sfx,
            "captions": captions,
        }
        if abs(rate - 1.0) > 0.01:
            seg_dict["playbackRate"] = round(rate, 3)
        if seg.transitionIn is not None:
            seg_dict["transitionIn"] = seg.transitionIn

        remotion_segments.append(seg_dict)
    return {
        "channelId": plan.channel_id,
        "theme": theme,
        "montageMode": plan.montage_mode,
        "fps": 30,
        "segments": remotion_segments,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 2 (V2): CHM × Red Arcade Multimodal Director")
    parser.add_argument("--selection", type=Path, required=True, help="Path to curated_selection_*.json")
    parser.add_argument("--project-dir", type=Path, required=True, help="Channel project directory")
    parser.add_argument("--model", default=None, help="Optional Gemini model override")
    args = parser.parse_args()

    load_dotenv(CORE_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY missing in clip_factory/.env")

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    channel_id = selection["channel_id"]
    run_date = selection["run_date"]
    clips = selection.get("selected_clips", [])
    if not clips:
        raise SystemExit("No selected_clips found.")

    project_dir = args.project_dir.resolve()
    inbox_dir = project_dir / "workspace" / "01_inbox_raw" / run_date
    inbox_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir = project_dir / "workspace" / "03_analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    download_missing_tiktoks(clips, inbox_dir)
    args.selection.write_text(json.dumps(selection, indent=2, ensure_ascii=False), encoding="utf-8")

    ready_clips = [c for c in clips if c.get("local_file") and (inbox_dir / c["local_file"]).exists()]
    if not ready_clips:
        raise SystemExit("No local .mp4 clips available.")

    transcripts_path = analysis_dir / f"transcripts_{channel_id}_{run_date}.json"
    if transcripts_path.exists():
        print(f"[Whisper] Using cached transcripts: {transcripts_path.name}")
        transcripts = json.loads(transcripts_path.read_text(encoding="utf-8"))
    else:
        transcripts = transcribe_all(ready_clips, inbox_dir)
        transcripts_path.write_text(
            json.dumps(transcripts, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    client = genai.Client(api_key=api_key)
    avail = get_available_models(client)
    model_name = args.model or next(
        (m for m in ("gemini-3.8-flash", "gemini-3.1-pro-preview", "gemini-3.5-flash-lite") if m in avail),
        "gemini-3.8-flash",
    )
    print(f"[Gemini] Using model: {model_name}")

    style_guide = (project_dir / "config" / "style_guide.md").read_text(encoding="utf-8")
    few_shot_path = project_dir / "config" / "few_shot_plans.json"
    few_shot_data = json.loads(few_shot_path.read_text(encoding="utf-8")) if few_shot_path.exists() else {}
    few_shot_examples = few_shot_data.get("examples", [])
    meme_map_data = json.loads((CORE_ROOT / "shared_assets" / "meme_map.json").read_text(encoding="utf-8"))
    sfx_map = dict(meme_map_data.get("sfx", {}))

    comedy_skill_md = ""
    skill_candidates = [project_dir / ".agents" / "skills" / f"{channel_id}-comedy-director" / "SKILL.md"]
    skills_root = project_dir / ".agents" / "skills"
    if skills_root.is_dir():
        skill_candidates.extend(sorted(skills_root.glob("*-comedy-director/SKILL.md")))
    for sp in skill_candidates:
        if sp.is_file():
            comedy_skill_md = sp.read_text(encoding="utf-8")
            break

    uploaded_files = []
    contents: list[Any] = []
    try:
        for idx, c in enumerate(ready_clips, start=1):
            local_path = inbox_dir / c["local_file"]
            dur = round(get_duration(local_path), 2)
            print(f"[Gemini] Uploading clip {idx}/{len(ready_clips)}: {c['local_file']} ({dur}s)...")
            gfile = client.files.upload(file=str(local_path))
            while gfile.state.name == "PROCESSING":
                time.sleep(2)
                gfile = client.files.get(name=gfile.name)
            if gfile.state.name != "ACTIVE":
                raise RuntimeError(f"Gemini upload failed for {c['local_file']}: {gfile.state.name}")
            uploaded_files.append(gfile)

            meta = {
                "clip_number": idx,
                "clip_id": c["clip_id"],
                "source_file": c["local_file"],
                "platform": c["platform"],
                "author": c["author"],
                "actual_duration_sec": dur,
                "title": c["title"],
                "user_directorial_note": c.get("directorial_note", ""),
                "user_markers": c.get("markers", []),
                "whisper_words": transcripts.get(c["local_file"], [])[:300],
            }
            contents.append(f"--- CLIP {idx} METADATA ---\n{json.dumps(meta, indent=2)}")
            contents.append(gfile)

        few_shot_block = (
            f"\nGOLDEN FEW-SHOT EXAMPLES (Match this exact timing, humor, and visual energy):\n{json.dumps(few_shot_examples, indent=2)}\n"
            if few_shot_examples
            else ""
        )
        comedy_skill_block = (
            f"\nCOMEDY DIRECTOR PLAYBOOK:\n{comedy_skill_md}\n"
            if comedy_skill_md
            else ""
        )

        prompt = f"""
You are the Lead 9:16 Vertical Gaming Comedy Editor for `{channel_id}` (v7 Hybrid Production Standard).

CHANNEL STYLE GUIDE:
{style_guide}
{comedy_skill_block}
{few_shot_block}
STRICT v7 PRODUCTION & COMEDY CONSTITUTION:
1. **62 to 85 Seconds Flexible Runtime:** Pick the strongest 4-5 clips whose trimmed segments sum to 62-75s (up to ~85s when setups/payoffs need breathing room). Drop the viewer into action at 0.0s, hold reaction beats 0.6s-2.0s AFTER the punchline registers — NEVER cut on a cliffhanger!
2. **MANDATORY MULTIMODAL VIDEO + AUDIO SPEAKER DIARIZATION (STRICT TOP vs. BOTTOM SPLIT):**
   - Watch the streamer's facecam mouth movement AND read any in-game subtitles alongside the audio timbre (close-mic streamer voice vs. spatial/in-game audio).
   - NEVER use audio-only guessing and NEVER cross a speaker boundary inside a single caption chunk.
   - `streamer` (**TOP zone** near streamer's mouth, white + yellow karaoke, `streamerCaptionY` default `27`): ONLY real-life streamer/commentator reactions spoken into their microphone.
   - `npc` (**BOTTOM zone**, electric cyan + mint subtitle pill with quotes): ALL in-game voices — NPCs, cops, bystanders, radio, and in-game player-character voice lines. Never tag an in-game character line as `streamer`!
   - `editorial`: Punchy deadpan callouts (`"INSTANT REGRET"`, `"DOWN GOES GRANDMA"`), max 1-2 per clip only when adding ironic contrast.
3. **VARIED CAMERA CHOREOGRAPHY (NEVER HOMOGENIZE ZOOMS):**
   - Match zoom `mode` and `scale` to each clip's comedic emotion: `aggressive_punch` (`1.75-2.05` + `ImpactShake`) for brutal hits/mauls; split segment with `playbackRate: 0.58-0.68` + `slow_creep` (`1.45-1.70`) for stunned slow-mo disbelief; `snap_hold` (`1.45-1.75`) for sudden punchlines; `smooth` (`1.20-1.40`) for subtle reveals.
4. **COMEDY BEAT HANDOFF FOR SOUND EDITOR:**
   - Set `montage_mode` (`funny` | `action` | `hybrid`) for the overall short (`hybrid` is ideal when a serious chase/flex turns into a sudden absurd fail).
   - Always fill `comedy_beat_summary` with 1 sharp sentence explaining what makes the clip funny and where the punchline hits, AND populate 1–3 structured `beat_tags` (`atSec`, `trigger`, `humor_type`, `energy`, `placement_hint`, `note`) describing the **situation** (never name a sound file in `note`).
   - Leave `sfx: []` empty/minimal — `sound_editor.py` designs the rule-checked meme & SFX mix using your `montage_mode`, `beat_tags`, `comedy_beat_summary`, and `captions`.
5. **ZERO ICON / SLOP SPAM:** Leave `spotlights: []` unless literally warranted; ZERO spoiler rankings ("Wait for the end") or deep-fried narration.
6. **CROP & COPYRIGHT DISCIPLINE:** Keep `cropZoom: 1.0` on native 9:16 clips (use `letterboxCrop` in props for 16:9/4:3 letterboxed clips). Set `isolate_vocals: true` whenever GTA car radio or copyrighted/unfitting background music is audible so NPC voices stay crisp.
"""
        contents.append(prompt)
        fallback_models = [model_name] + [
            m for m in ("gemini-3.1-pro-preview", "gemini-3.5-flash-lite", "gemini-3.8-flash")
            if m != model_name and m in avail
        ]
        resp = None
        last_err: Exception | None = None
        for m in fallback_models:
            try:
                print(f"[Gemini] Directing montage with CHM × Red Arcade rubric ({m})...")
                resp = client.models.generate_content(
                    model=m,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=MontagePlan,
                        temperature=0.35,
                    ),
                )
                log_token_usage("Director", m, resp)
                break
            except Exception as exc:
                last_err = exc
                print(f"  [Gemini] {m} unavailable ({exc}); trying fallback...")
        if resp is None:
            raise RuntimeError(f"All Gemini models failed: {last_err}")
        plan = MontagePlan.model_validate_json(resp.text)
        merge_user_meme_markers(plan, ready_clips)

        plan_path = analysis_dir / f"edit_plan_{channel_id}_{run_date}.json"
        plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

        props_path = analysis_dir / f"remotion_props_{channel_id}_{run_date}.json"
        props_path.write_text(
            json.dumps(
                plan_to_remotion_props(plan, sfx_map, channel_id=channel_id, transcripts=transcripts),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nDone! Directed {len(plan.segments)} segments ({plan.total_target_seconds:.1f}s)")
        print(f"  Edit plan:      {plan_path}")
        print(f"  Remotion props: {props_path}")
    finally:
        for gf in uploaded_files:
            try:
                client.files.delete(name=gf.name)
            except Exception:
                pass


if __name__ == "__main__":
    main()
