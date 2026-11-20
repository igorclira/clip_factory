"""
Clip Factory — Unified Sound & Music Library Builder

Scans shared_assets/meme_map.json and shared_assets/sfx_catalog.json, resolves files in
shared_assets/sfx/ and shared_assets/sfx_library/, measures loudness_lufs via FFmpeg + numpy,
and emits:
  - shared_assets/sound_library.json: list of {file, category, mood, length_s, peak_sec, loudness_lufs, use_when}
  - shared_assets/music_library.json: list of {file, bpm, energy, mood, has_vocals, length_s, loudness_lufs}

Usage:
    python src/build_sound_libraries.py
"""

from __future__ import annotations

import json
import math
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np

CORE_ROOT = Path(__file__).resolve().parent.parent
SHARED_DIR = CORE_ROOT / "shared_assets"
SFX_DIRS = [SHARED_DIR / "sfx", SHARED_DIR / "sfx_library"]
MEME_MAP_PATH = SHARED_DIR / "meme_map.json"
SFX_CATALOG_PATH = SHARED_DIR / "sfx_catalog.json"
SEMANTICS_PATH = SHARED_DIR / "sound_semantics.json"
SOUND_LIB_PATH = SHARED_DIR / "sound_library.json"
MUSIC_LIB_PATH = SHARED_DIR / "music_library.json"

MUSIC_META_OVERRIDES: dict[str, dict[str, Any]] = {
    "upbeat_grandma_chase.wav": {
        "bpm": 124,
        "energy": 4,
        "mood": "upbeat_funny_chase",
        "has_vocals": False,
    },
    "vice_city_synth_bed.wav": {
        "bpm": 112,
        "energy": 3,
        "mood": "vice_city_vaporwave_chill",
        "has_vocals": False,
    },
}

TRANSITION_KEYWORDS = ("whoosh", "swoosh", "riser", "swell", "rewind", "glitch", "tape_stop", "scratch", "transition")
IMPACT_KEYWORDS = ("boom", "bass", "slam", "hit", "impact", "thud", "crash", "gun", "pistol", "shot", "explosion", "bang", "punch", "slap", "bonk", "pipe")
MEME_HINT_WORDS = (
    "meme", "bruh", "vine", "fah", "faaah", "uwu", "rizz", "among", "gta", "wasted", "spongebob",
    "taco", "windows", "violin", "trombone", "buzzer", "quack", "huh", "wow", "avengers", "hl_",
    "scientist", "roblox", "minecraft", "mgs", "cat", "scream", "laugh", "oh_no", "fart", "cj",
    "moment", "wait_a_minute", "hell_no", "fbi", "mission", "milk", "nani", "please_no", "surprise",
    "directed", "tuco", "nelson", "gordon", "family_guy", "knuckles", "lil_jon", "running",
)

PERCUSSIVE_MEME_TOKENS = (
    "bonk", "slip", "vine_boom", "pipe", "bong", "hit", "alert", "dundun",
    "click", "oof", "fart", "quack", "buzzer", "error", "ding", "pop", "avengers_sting",
)

VOICE_BLIP_CURATED_META: dict[str, str] = {
    "bruh.mp3": "[MAINSTREAM VOICE BLIP] Classic deadpan 'Bruh' reaction for dumb decisions, obvious fails, or awkward pauses.",
    "meme_bruh_og.mp3": "[MAINSTREAM VOICE BLIP] Original deadpan 'Bruh' reaction for foolish plays or instant anti-climax.",
    "tuco_get_out.mp3": "[MAINSTREAM VOICE BLIP] Aggressive Tuco 'GET OUT!' yell when kicking someone out, ejecting from a car, or banning chaos.",
    "my_leg_spongebob_fish_clear.mp3": "[MAINSTREAM VOICE BLIP] SpongeBob 'MY LEG!' scream on brutal ragdoll impacts, crashes, falls, or mauls.",
    "tom_scream.mp3": "[MAINSTREAM VOICE BLIP] Classic Tom & Jerry agonizing scream for sudden launches, explosions, or comedic pain.",
    "the_simpsons_nelson_s_ha_ha.mp3": "[MAINSTREAM VOICE BLIP] Nelson 'HA-HA!' point-and-laugh for instant karma, missed shots, or petty schadenfreude.",
    "knuckles_oh_no.mp3": "[MAINSTREAM VOICE BLIP] Punchy Knuckles 'Oh no' beat right as a bad plan goes sideways or disaster starts.",
    "lil_jon_whaaat.mp3": "[MAINSTREAM VOICE BLIP] Lil Jon 'WHAAAT?!' reaction for ridiculous NPC lines, glitches, or absurd plot twists.",
    "oh_my_god_meme.mp3": "[MAINSTREAM VOICE BLIP] Classic stunned 'OH MY GOD!' reaction for jaw-dropping chaos or insane luck.",
    "another_one_dj_khaled.mp3": "[MAINSTREAM VOICE BLIP] DJ Khaled 'Another one' for back-to-back fails, repeated crashes, or stacked chaos.",
    "michael_jackson_hee_hee.mp3": "[MAINSTREAM VOICE BLIP] Playful MJ 'Hee-hee!' accent for slick escapes, goofy animations, or cheeky moments.",
    "wilhelm_scream.mp3": "[MAINSTREAM VOICE BLIP] Iconic Wilhelm Scream when a pedestrian or NPC gets sent flying off screen.",
    "sonic_you_re_too_slow.mp3": "[MAINSTREAM VOICE BLIP] Sonic 'You're too slow!' taunt for narrow escapes, failed chases, or outrunning danger.",
    "a_few_moments_later_sponge_bob_sfx_fun.mp3": "[MAINSTREAM VOICE BLIP] SpongeBob narrator 'A few moments later...' for jump-cuts from setup straight to disaster.",
    "talking_ben_no.mp3": "[MAINSTREAM VOICE BLIP] Deadpan Talking Ben 'No.' refusal right after a bad idea or doomed request.",
    "home_improvement_huh.mp3": "[MAINSTREAM VOICE BLIP] Tim Allen confused 'Huh?!' grunt for bizarre glitches, weird NPCs, or double-takes.",
    "gah_dayum.mp3": "[MAINSTREAM VOICE BLIP] Explosive 'GAH DAYUM!' exclamation for massive hits, brutal ragdolls, or savage comebacks.",
    "family_guy_shut_the_f_ck_up.mp3": "[MAINSTREAM VOICE BLIP] Aggressive 'Shut the f*** up!' cutoff when an annoying NPC or loudmouth gets silenced.",
    "meme_law_and_order_dundun.mp3": "[MAINSTREAM STINGER] Iconic Law & Order 'DUN-DUN' sting for sudden crimes, arrests, or guilty reveals.",
    "meme_taco_bell_bong.mp3": "[MAINSTREAM STINGER] Heavy Taco Bell gong on sudden knockouts, headshots, or brutal comedic hits.",
    "meme_huh_cat.mp3": "[MAINSTREAM VOICE BLIP] Rapid 'Huh?' cat beat for pure confusion, unexpected turns, or nonsensical AI behavior.",
    "meme_cartoon_bonk.mp3": "[MAINSTREAM STINGER] Crisp cartoon 'BONK' on melee slaps, head knocks, or goofy collisions.",
    "meme_cartoon_slip.mp3": "[MAINSTREAM STINGER] Classic cartoon slip whistle when characters wipe out, trip, or lose traction.",
    "meme_mgs_alert.mp3": "[MAINSTREAM STINGER] Metal Gear Solid '!' alert sting when spotted by cops, guards, or an ambush.",
    "meme_roblox_oof.mp3": "[MAINSTREAM VOICE BLIP] Quick 'Oof' death sound for sudden anticlimactic wipeouts or instant KOs.",
}


def _has_token(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", text) for w in words)


def resolve_audio_path(filename: str) -> Path | None:
    for d in SFX_DIRS:
        p = d / filename
        if p.is_file():
            return p
    return None


def measure_lufs_and_timing(
    audio_path: Path, existing_dur: float | None, existing_peak: float | None, sr: int = 16000
) -> tuple[float, float, float, float]:
    """Return (length_s, peak_sec, onset_sec, loudness_lufs) via FFmpeg PCM decode."""
    try:
        raw = subprocess.check_output(
            [
                "ffmpeg", "-v", "error", "-i", str(audio_path),
                "-f", "f32le", "-acodec", "pcm_f32le", "-ac", "1", "-ar", str(sr), "-",
            ],
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        samples = np.frombuffer(raw, dtype=np.float32)
        if samples.size == 0:
            return round(existing_dur or 0.0, 3), round(existing_peak or 0.0, 3), 0.0, -24.0

        dur = round(existing_dur if existing_dur and existing_dur > 0 else samples.size / sr, 3)

        # Active loudness (ignore leading/trailing silence < -50dB so short stingers measure accurately)
        abs_s = np.abs(samples)
        active = samples[abs_s > 0.003]
        if active.size < 100:
            active = samples
        rms = float(np.sqrt(np.mean(active.astype(np.float64) ** 2)))
        lufs = round(max(-35.0, min(-3.0, 20.0 * math.log10(rms + 1e-9) - 0.691)), 1)

        win = max(1, int(sr * 0.02))
        if samples.size <= win:
            peak = round(float(existing_peak), 3) if existing_peak is not None and existing_peak >= 0 else 0.0
            onset = 0.0
        else:
            sq = samples.astype(np.float64) ** 2
            csum = np.cumsum(np.insert(sq, 0, 0.0))
            rms_w = np.sqrt((csum[win:] - csum[:-win]) / win)
            if existing_peak is not None and existing_peak >= 0:
                peak = round(float(existing_peak), 3)
            else:
                peak = round(int(np.argmax(rms_w)) / sr, 3)
            max_rms = float(np.max(rms_w)) if rms_w.size > 0 else 0.0
            thresh = max(0.015, 0.12 * max_rms)
            above = np.where(rms_w >= thresh)[0]
            raw_onset = round(int(above[0]) / sr, 3) if above.size > 0 else 0.0
            onset = round(min(max(0.0, raw_onset), peak), 3)

        return dur, peak, onset, lufs
    except Exception:
        return round(existing_dur or 0.0, 3), round(existing_peak or 0.0, 3), 0.0, -18.0


def classify_sound(tag: str, filename: str, raw_cat: str, title: str, sounds_like: str, use_when: str) -> tuple[str, str]:
    text = f"{tag} {filename} {title} {sounds_like} {use_when}".lower()

    if tag.startswith(("meme_", "hl_")) or filename.lower().startswith(("meme_", "hl_")) or filename.lower() == "ah_shit_here_we_go_again_cj.mp3":
        category = "meme"
    elif any(k in text for k in TRANSITION_KEYWORDS):
        category = "transition"
    elif _has_token(text, IMPACT_KEYWORDS) and not any(m in text for m in ("metal_pipe_og", "vine_boom", "bonk_meme", "anime", "fart")):
        category = "impact"
    elif raw_cat in ("sound_effects",) and not any(m in text for m in MEME_HINT_WORDS):
        category = "sfx"
    elif raw_cat in ("memes", "viral", "reactions", "movies", "anime", "trending", "games") or any(m in text for m in MEME_HINT_WORDS):
        category = "meme"
    else:
        category = "sfx"

    # Compact mood inference
    if category == "transition":
        mood = "energetic" if "riser" in text or "whip" in text or "swell" in text else "tense"
    elif category == "impact":
        mood = "dramatic" if "sub" in text or "brass" in text or "dramatic" in text or "boom" in text else "punchy"
    elif any(w in text for w in ("sad", "violin", "trombone", "death", "flatline", "fail", "error", "shutdown")):
        mood = "fail_comedy"
    elif any(w in text for w in ("scream", "panic", "stahp", "wtf", "shock", "gasp", "huh", "alert")):
        mood = "chaotic_shock"
    elif any(w in text for w in ("fanfare", "epic", "avengers", "jackpot", "tada", "cheer", "yay")):
        mood = "heroic_hype"
    else:
        mood = "comedic"

    return category, mood


def main() -> None:
    meme_map = json.loads(MEME_MAP_PATH.read_text(encoding="utf-8")).get("sfx", {}) if MEME_MAP_PATH.exists() else {}
    sfx_catalog = json.loads(SFX_CATALOG_PATH.read_text(encoding="utf-8")) if SFX_CATALOG_PATH.exists() else {}
    sound_semantics: dict[str, dict[str, Any]] = (
        json.loads(SEMANTICS_PATH.read_text(encoding="utf-8")) if SEMANTICS_PATH.exists() else {}
    )

    # Collect unique audio entries by resolved filename (prefer meme_map rich descriptions)
    entries: dict[str, dict[str, Any]] = {}

    for tag, meta in meme_map.items():
        if not isinstance(meta, dict):
            continue
        fname = meta.get("filename") or meta.get("file")
        if not fname or fname in entries:
            continue
        path = resolve_audio_path(fname)
        if not path:
            continue
        entries[fname] = {
            "tag": tag,
            "file": fname,
            "path": path,
            "raw_cat": "curated",
            "title": tag.replace("_", " "),
            "sounds_like": meta.get("sounds_like", ""),
            "use_when": meta.get("use_when", ""),
            "duration_sec": meta.get("duration_sec"),
            "peak_sec": meta.get("peak_sec"),
        }

    for tag, meta in sfx_catalog.items():
        if not isinstance(meta, dict):
            continue
        fname = meta.get("filename") or meta.get("file")
        if not fname or fname in entries:
            continue
        path = resolve_audio_path(fname)
        if not path:
            continue
        entries[fname] = {
            "tag": tag,
            "file": fname,
            "path": path,
            "raw_cat": meta.get("category", "trending"),
            "title": meta.get("title", tag.replace("_", " ")),
            "sounds_like": "",
            "use_when": "",
            "duration_sec": meta.get("duration_sec"),
            "peak_sec": meta.get("peak_sec"),
        }

    # Discover any remaining curated files placed directly inside shared_assets/sfx/
    curated_sfx_dir = SHARED_DIR / "sfx"
    if curated_sfx_dir.is_dir():
        for p in sorted(curated_sfx_dir.iterdir()):
            if not p.is_file() or p.suffix.lower() not in (".wav", ".mp3"):
                continue
            fname = p.name
            if fname in entries:
                continue
            tag = p.stem
            entries[fname] = {
                "tag": tag,
                "file": fname,
                "path": p,
                "raw_cat": "curated",
                "title": tag.replace("_", " "),
                "sounds_like": "",
                "use_when": f"[CURATED] {tag.replace('_', ' ')}",
                "duration_sec": None,
                "peak_sec": None,
            }

    # Discover any files explicitly listed in sound_semantics.json that weren't in meme_map/sfx_catalog
    for fname, sem in sound_semantics.items():
        if fname in entries:
            continue
        path = resolve_audio_path(fname)
        if not path:
            print(f"  [Semantics] Missing audio file on disk: {fname}")
            continue
        entries[fname] = {
            "tag": sem.get("id", path.stem),
            "file": fname,
            "path": path,
            "raw_cat": "curated",
            "title": sem.get("id", path.stem).replace("_", " "),
            "sounds_like": "",
            "use_when": sem.get("meaning", ""),
            "duration_sec": None,
            "peak_sec": None,
        }

    print(f"[BuildSoundLibs] Measuring LUFS & classifying {len(entries)} unique audio files...")
    sound_library: list[dict[str, Any]] = []
    music_library: list[dict[str, Any]] = []

    def process_item(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        dur, peak, onset, lufs = measure_lufs_and_timing(
            item["path"], item["duration_sec"], item["peak_sec"]
        )
        fname = item["file"]
        if dur >= 15.0 or fname in MUSIC_META_OVERRIDES:
            ov = MUSIC_META_OVERRIDES.get(fname, {})
            return "music", {
                "file": fname,
                "bpm": ov.get("bpm", 120),
                "energy": ov.get("energy", 3),
                "mood": ov.get("mood", item["title"].lower().replace(" ", "_")),
                "has_vocals": ov.get("has_vocals", False),
                "length_s": dur,
                "loudness_lufs": lufs,
            }

        cat, mood = classify_sound(
            item["tag"], fname, item["raw_cat"], item["title"], item["sounds_like"], item["use_when"]
        )
        use_when = item["use_when"] or item["sounds_like"] or f"{item['title']} ({item['raw_cat']})"
        if fname in VOICE_BLIP_CURATED_META and "[MAINSTREAM VOICE BLIP]" not in use_when:
            use_when = VOICE_BLIP_CURATED_META[fname]

        fname_low = fname.lower()
        is_percussive_meme = _has_token(fname_low, PERCUSSIVE_MEME_TOKENS)
        align_mode = "onset" if (cat == "meme" and not is_percussive_meme) else "peak"

        record: dict[str, Any] = {
            "file": fname,
            "category": cat,
            "mood": mood,
            "length_s": dur,
            "peak_sec": peak,
            "onset_sec": onset,
            "align_mode": align_mode,
            "loudness_lufs": lufs,
            "use_when": use_when,
        }
        sem = sound_semantics.get(fname)
        if sem:
            record.update({
                "id": sem.get("id", Path(fname).stem),
                "meaning": sem.get("meaning", use_when),
                "trigger_moments": sem.get("trigger_moments", []),
                "humor_type": sem.get("humor_type", "none"),
                "montage_mode": sem.get("montage_mode", "both"),
                "energy": int(sem.get("energy", 3)),
                "placement": sem.get("placement", "on_impact"),
                "copyright_risk": sem.get("copyright_risk", "medium"),
                "freshness": sem.get("freshness", "evergreen"),
                "dedupe_group": sem.get("dedupe_group", ""),
                "curated_semantic": True,
            })
            if sem.get("gta_native"):
                record["gta_native"] = True
        return "sound", record

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(process_item, item) for item in entries.values()]
        for fut in as_completed(futures):
            kind, record = fut.result()
            if kind == "music":
                music_library.append(record)
            else:
                sound_library.append(record)

    sound_library.sort(key=lambda x: (x["category"], x["file"]))
    music_library.sort(key=lambda x: x["file"])

    SOUND_LIB_PATH.write_text(json.dumps(sound_library, indent=2, ensure_ascii=False), encoding="utf-8")
    MUSIC_LIB_PATH.write_text(json.dumps(music_library, indent=2, ensure_ascii=False), encoding="utf-8")

    cat_counts: dict[str, int] = {}
    for s in sound_library:
        cat_counts[s["category"]] = cat_counts.get(s["category"], 0) + 1

    print(f"Done! Built libraries:")
    print(f"  sound_library.json -> {len(sound_library)} files {cat_counts}")
    print(f"  music_library.json -> {len(music_library)} tracks ({[m['file'] for m in music_library]})")


if __name__ == "__main__":
    main()
