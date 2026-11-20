"""
Clip Factory — Audio-Listening SFX Auto-Indexer (src/index_sfx.py)

Scans shared_assets/sfx/ for audio files (.wav, .mp3, .ogg, .m4a), measures exact
duration_sec and acoustic peak_sec (via FFmpeg + numpy so Remotion aligns the actual
impact peak to the target video frame), uploads each new sound to Gemini so Gemini
listens to it natively, and writes a rich semantic catalog into shared_assets/meme_map.json:
  - file, duration_sec, peak_sec, category, sounds_like, use_when, avoid_when, pair_with

Usage:
    python src/index_sfx.py
    python src/index_sfx.py --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Literal

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from gemini_utils import get_available_models, log_token_usage

CORE_ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = CORE_ROOT / "shared_assets" / "sfx"
MEME_MAP_PATH = CORE_ROOT / "shared_assets" / "meme_map.json"
AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".m4a", ".flac"}


class SfxSemanticProfile(BaseModel):
    category: Literal["impact", "transition", "comedy", "tension", "alert", "gaming", "meme"]
    sounds_like: str = Field(description="Concise, vivid description of what this audio clip actually sounds like")
    use_when: str = Field(description="Exact gaming/editing moments where this SFX lands best (CHM × Red Arcade style)")
    avoid_when: str = Field(description="Situations where this SFX would feel out of place or spammy")
    pair_with: list[Literal["SnapZoomBox", "AudioVacuum", "ImpactShake", "DespairFreeze", "TargetSpotlight"]] = Field(
        description="Visual shenanigans that combo best with this SFX"
    )


def measure_audio_peak(audio_path: Path, sr: int = 22050) -> tuple[float, float]:
    """Return (duration_sec, peak_sec) using FFmpeg PCM decode + short-window RMS energy."""
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(audio_path),
        "-f", "f32le", "-acodec", "pcm_f32le", "-ac", "1", "-ar", str(sr), "-",
    ]
    raw = subprocess.check_output(cmd)
    samples = np.frombuffer(raw, dtype=np.float32)
    if samples.size == 0:
        return 0.0, 0.0
    duration_sec = round(samples.size / sr, 3)

    # 20ms sliding window RMS to find the true perceived impact peak (ignores single-sample clicks)
    win = max(1, int(sr * 0.02))
    if samples.size <= win:
        peak_sec = 0.0
    else:
        sq = samples.astype(np.float64) ** 2
        csum = np.cumsum(np.insert(sq, 0, 0.0))
        rms = np.sqrt((csum[win:] - csum[:-win]) / win)
        peak_idx = int(np.argmax(rms))
        peak_sec = round(peak_idx / sr, 3)
    return duration_sec, peak_sec


def slugify_tag(stem: str) -> str:
    tag = re.sub(r"[^a-zA-Z0-9]+", "_", stem.lower()).strip("_")
    return tag or "sfx_item"


def listen_and_profile(client: genai.Client, model_name: str, audio_path: Path, duration_sec: float, peak_sec: float) -> SfxSemanticProfile:
    gfile = client.files.upload(file=str(audio_path))
    try:
        while gfile.state.name == "PROCESSING":
            time.sleep(1)
            gfile = client.files.get(name=gfile.name)
        if gfile.state.name != "ACTIVE":
            raise RuntimeError(f"Gemini audio upload failed for {audio_path.name}: {gfile.state.name}")

        prompt = f"""
Listen closely to this sound effect file (`{audio_path.name}`, duration {duration_sec}s, acoustic energy peak at {peak_sec}s).
You are cataloging SFX for two viral gaming clip channels (`wow_forever` and `gta6`) using the
Classic Hardcore Moments × Red Arcade editing style.

Describe accurately what this sound actually sounds like, the exact comedic/tension/impact beats
where a pro gaming editor should use it, when to avoid using it, and which Remotion visual effects
it pairs best with. Be concrete and specific.
"""
        resp = client.models.generate_content(
            model=model_name,
            contents=[gfile, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SfxSemanticProfile,
                temperature=0.25,
            ),
        )
        log_token_usage("SfxIndexer", model_name, resp)
        return SfxSemanticProfile.model_validate_json(resp.text)
    finally:
        try:
            client.files.delete(name=gfile.name)
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Index shared_assets/sfx/ (peaks-only by default; pass --listen for Gemini audio profiling)")
    parser.add_argument("--listen", action="store_true", help="Upload unprofiled SFX to Gemini to generate sounds_like/use_when metadata")
    parser.add_argument("--force", action="store_true", help="Re-index all SFX with Gemini even if already profiled (implies --listen)")
    parser.add_argument("--peaks-only", action="store_true", help="Explicit peaks-only mode (default when --listen/--force are omitted)")
    args = parser.parse_args()

    use_gemini = (args.listen or args.force) and not args.peaks_only

    load_dotenv(CORE_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if use_gemini and not api_key:
        raise SystemExit("GEMINI_API_KEY missing in clip_factory/.env")

    SFX_DIR.mkdir(parents=True, exist_ok=True)
    audio_files = sorted(p for p in SFX_DIR.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS)
    if not audio_files:
        print(f"No audio files found in {SFX_DIR}")
        return

    existing = json.loads(MEME_MAP_PATH.read_text(encoding="utf-8")) if MEME_MAP_PATH.exists() else {}
    existing_sfx = existing.get("sfx", {})

    client = None
    model_name = "gemini-2.5-flash"
    if use_gemini:
        client = genai.Client(api_key=api_key)
        avail = get_available_models(client)
        model_name = next(
            (m for m in ("gemini-3.8-flash", "gemini-2.5-flash") if m in avail),
            "gemini-2.5-flash",
        )
    print(f"[SFX Indexer] Scanning {len(audio_files)} audio file(s) (gemini={use_gemini})...")

    updated_sfx: dict[str, dict] = {}
    for p in audio_files:
        tag = slugify_tag(p.stem)
        prev = existing_sfx.get(tag)
        dur, peak = measure_audio_peak(p)

        if isinstance(prev, dict) and (prev.get("filename") == p.name or prev.get("file") == p.name) and prev.get("sounds_like") and not args.force:
            merged = dict(prev)
            merged["filename"] = p.name
            merged["duration_sec"] = dur
            merged["peak_sec"] = peak
            updated_sfx[tag] = merged
            print(f"  [Peak-Synced] {tag}: dur={dur}s, peak={peak}s")
            continue

        if not use_gemini or client is None:
            merged = dict(prev) if isinstance(prev, dict) else {}
            merged.update({"filename": p.name, "duration_sec": dur, "peak_sec": peak})
            updated_sfx[tag] = merged
            continue

        print(f"  [Listening] {p.name} (dur={dur}s, peak={peak}s)...")
        profile = listen_and_profile(client, model_name, p, dur, peak)
        updated_sfx[tag] = {
            "filename": p.name,
            "duration_sec": dur,
            "peak_sec": peak,
            **profile.model_dump(),
        }
        print(f"    -> [{profile.category}] {profile.sounds_like[:90]}")

    out_data = {
        "_comment": "Rich Semantic SFX & Meme Catalog. Auto-indexed by src/index_sfx.py (Gemini listens to each new audio file + FFmpeg measures exact peak_sec for frame-accurate Remotion alignment).",
        "sfx": updated_sfx,
        "memes": existing.get("memes", {}),
    }
    MEME_MAP_PATH.write_text(json.dumps(out_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone! Synced {len(updated_sfx)} SFX into {MEME_MAP_PATH}")


if __name__ == "__main__":
    main()
