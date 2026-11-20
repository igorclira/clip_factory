"""
Clip Factory — Stage 3: Remotion Production Renderer Launcher

Stages the channel's inbox clips + shared SFX into remotion_studio/public/,
runs `npx remotion render src/index.ts MontageVideo`, and outputs a clean
1080x1920 H.264 master directly into <project_dir>/workspace/04_rough_cuts/<date>/.

Usage:
    python src/render_remotion.py \
      --props C:/Users/PC/.gemini/antigravity/scratch/gta6_clips/workspace/03_analysis/remotion_props_gta6_2026-11-19.json \
      --project-dir C:/Users/PC/.gemini/antigravity/scratch/gta6_clips
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parent.parent
STUDIO_DIR = CORE_ROOT / "remotion_studio"


def build_atempo_filters(rate: float) -> list[str]:
    """Chain FFmpeg atempo filters (each supports 0.5..2.0) to match any playbackRate."""
    filters: list[str] = []
    r = rate
    while r < 0.5:
        filters.append("atempo=0.5")
        r /= 0.5
    while r > 2.0:
        filters.append("atempo=2.0")
        r /= 2.0
    if abs(r - 1.0) > 1e-3:
        filters.append(f"atempo={r:.5f}")
    return filters


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 3: Render Remotion MontageVideo")
    parser.add_argument("--props", type=Path, required=True, help="Path to remotion_props_*.json")
    parser.add_argument("--project-dir", type=Path, required=True, help="Channel project directory")
    parser.add_argument("--out", type=Path, default=None, help="Optional custom output .mp4 path")
    args = parser.parse_args()

    props = json.loads(args.props.read_text(encoding="utf-8"))
    channel_id = props["channelId"]
    parts = args.props.stem.split("_")
    run_date = next((p for p in parts if len(p) == 10 and p.count("-") == 2), "latest")

    project_dir = args.project_dir.resolve()
    inbox_dir = project_dir / "workspace" / "01_inbox_raw" / run_date
    out_dir = project_dir / "workspace" / "04_rough_cuts" / run_date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = args.out or (out_dir / f"montage_{channel_id}_{run_date}.mp4")

    # Stage ONLY the referenced clips + shared SFX into remotion_studio/public/
    pub_clips = STUDIO_DIR / "public" / "clips"
    pub_sfx = STUDIO_DIR / "public" / "sfx"
    pub_clips.mkdir(parents=True, exist_ok=True)
    pub_sfx.mkdir(parents=True, exist_ok=True)

    # Pre-trim each segment to exact CFR 30fps starting at 0.0s so Remotion OffthreadVideo
    # never hits VFR/deep-seek compositor errors and renders 2x faster!
    staged_segments = []
    for seg in props.get("segments", []):
        if seg.get("kind") == "cta":
            dur_s = max(0.5, round(float(seg["endSec"]) - float(seg["startSec"]), 3))
            new_seg = dict(seg)
            new_seg["startSec"] = 0.0
            new_seg["endSec"] = dur_s
            staged_segments.append(new_seg)
            print(f"[Prep] Staged CTA interstitial {seg['id']} ({dur_s}s)...")
            continue

        src = inbox_dir / seg["videoFile"]
        if not src.exists():
            raise FileNotFoundError(f"Clip not found in inbox: {src}")
        start_s = float(seg["startSec"])
        end_s = float(seg["endSec"])
        dur_s = max(0.5, round(end_s - start_s, 3))
        rate = float(seg.get("playbackRate") or 1.0)
        out_dur = max(0.5, round(dur_s / rate, 3))
        lbox = seg.get("letterboxCrop")
        trimmed_name = f"trim_{seg['id']}.mp4"
        dst = pub_clips / trimmed_name
        print(
            f"[Prep] Trimming {seg['id']}: {seg['videoFile']} ({start_s}s -> {end_s}s, "
            f"src={dur_s}s, rate={rate}x, out={out_dur}s, lbox={bool(lbox)})..."
        )

        # Build audio chain: optional vocal isolation -> slow/fast atempo -> -14 LUFS loudness leveling
        af_parts: list[str] = []
        if seg.get("isolateVocals"):
            has_bgm = bool(seg.get("bgmFile")) or bool((props.get("soundPlan") or {}).get("music", {}).get("file"))
            print(
                f"  [Warn] {seg['id']}: isolateVocals bandpass (260-3600Hz) is NOT Content-ID safe "
                f"(bgm_present={has_bgm}, videoVolume={seg.get('videoVolume', 1.0)})."
            )
            if not has_bgm or float(seg.get("videoVolume", 1.0)) > 0.3:
                af_parts.append("pan=mono|c0=0.5*c0+0.5*c1,highpass=f=260,lowpass=f=3600,acompressor=threshold=-20dB:ratio=3:attack=5:release=60")
        if abs(rate - 1.0) > 1e-3:
            af_parts.extend(build_atempo_filters(rate))
        af_parts.append("loudnorm=I=-14:TP=-1.5:LRA=11")
        af_chain = ",".join(af_parts)

        ffmpeg_cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{start_s:.3f}",
            "-t", f"{dur_s + 0.25:.3f}",
            "-i", str(src),
        ]

        if lbox:
            y_pct = float(lbox["yPct"])
            h_pct = float(lbox["hPct"])
            pts_part = f",setpts={1.0 / rate:.5f}*PTS" if abs(rate - 1.0) > 1e-3 else ""
            fc = (
                f"[0:v]crop=trunc(iw/2)*2:trunc(ih*{h_pct:.4f}/2)*2:0:trunc(ih*{y_pct:.4f}/2)*2,split=2[bgsrc][fgsrc];"
                f"[bgsrc]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=28,eq=brightness=-0.16[bg];"
                f"[fgsrc]scale=1080:-2[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2{pts_part}[vout];"
                f"[0:a]{af_chain}[aout]"
            )
            ffmpeg_cmd.extend(["-filter_complex", fc, "-map", "[vout]", "-map", "[aout]"])
        else:
            if abs(rate - 1.0) > 1e-3:
                ffmpeg_cmd.extend(["-vf", f"setpts={1.0 / rate:.5f}*PTS"])
            ffmpeg_cmd.extend(["-af", af_chain])

        ffmpeg_cmd.extend([
            "-t", f"{out_dur + 0.25:.3f}",
            "-r", "30", "-fps_mode", "cfr",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-g", "15", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            str(dst),
        ])
        subprocess.run(ffmpeg_cmd, check=True)

        new_seg = dict(seg)
        new_seg["videoFile"] = trimmed_name
        new_seg["startSec"] = 0.0
        new_seg["endSec"] = out_dur
        new_seg.pop("playbackRate", None)
        new_seg.pop("letterboxCrop", None)
        staged_segments.append(new_seg)

    staged_props = dict(props)
    staged_props["segments"] = staged_segments
    staged_props_path = out_dir / f"_staged_{args.props.name}"
    staged_props_path.write_text(json.dumps(staged_props, indent=2, ensure_ascii=False), encoding="utf-8")

    # Clean out unreferenced bulky raw clips from public/clips so bundle copy stays fast
    keep_names = {s["videoFile"] for s in staged_segments if s.get("videoFile")}
    for old in pub_clips.iterdir():
        if old.is_file() and old.name not in keep_names:
            old.unlink(missing_ok=True)

    # Stage ONLY the exact SFX & BGM files referenced in this video (searching both sfx/ and sfx_library/)
    needed_audio: set[str] = set()
    for seg in props.get("segments", []):
        if seg.get("bgmFile"):
            needed_audio.add(seg["bgmFile"])
        for s in seg.get("sfx", []):
            if s.get("file"):
                needed_audio.add(s["file"])

    sound_plan = props.get("soundPlan") or {}
    if isinstance(sound_plan, dict):
        sp_music = (sound_plan.get("music") or {}).get("file")
        if sp_music:
            needed_audio.add(sp_music)
        for ev in sound_plan.get("events") or []:
            if ev.get("file"):
                needed_audio.add(ev["file"])

    sfx_dirs = [CORE_ROOT / "shared_assets" / "sfx", CORE_ROOT / "shared_assets" / "sfx_library"]
    for fname in needed_audio:
        src_audio = next((d / fname for d in sfx_dirs if (d / fname).exists()), None)
        if not src_audio:
            raise FileNotFoundError(f"Referenced audio file not found in sfx/ or sfx_library/: {fname}")
        dst = pub_sfx / fname
        if not dst.exists() or dst.stat().st_size != src_audio.stat().st_size:
            shutil.copy2(src_audio, dst)

    # Clean out unreferenced audio from public/sfx so Remotion bundle stays tiny even with 1,000+ SFX!
    for old_a in pub_sfx.iterdir():
        if old_a.is_file() and old_a.name not in needed_audio:
            old_a.unlink(missing_ok=True)

    raw_mp4 = out_mp4.parent / f"_raw_{out_mp4.name}"
    npx_cmd = r"C:\Program Files\nodejs\npx.cmd" if os.name == "nt" else "npx"
    cmd = [
        npx_cmd,
        "remotion",
        "render",
        "src/index.ts",
        "MontageVideo",
        str(raw_mp4),
        f"--props={staged_props_path.resolve()}",
    ]
    print(f"[Remotion] Rendering {out_mp4.name} ...")
    subprocess.run(cmd, cwd=str(STUDIO_DIR), check=True)

    # Rule #10: Final integrated loudness master (-14 LUFS, -1.0 dBTP) with untouched video stream
    final_mix = sound_plan.get("final_mix") or {}
    target_lufs = float(final_mix.get("target_lufs", -14.0))
    true_peak = float(final_mix.get("true_peak_db", -1.0))
    print(f"[Master] Normalizing final mix to {target_lufs} LUFS / {true_peak} dBTP...")
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(raw_mp4),
            "-c:v", "copy",
            "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            str(out_mp4),
        ],
        check=True,
    )
    raw_mp4.unlink(missing_ok=True)
    print(f"\nDone! Rendered master: {out_mp4}")


if __name__ == "__main__":
    main()
