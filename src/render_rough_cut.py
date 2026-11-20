"""
Clip Factory — Stage 3: Deterministic 1080x1920 Vertical Rough-Cut Renderer (FFmpeg)

Reads an edit_plan_*.json + transcripts_*.json from workspace/03_analysis/,
renders each segment into a clean 1080x1920 30fps vertical clip with:
  - Blurred full-frame background + sharp centered foreground (no black bars)
  - Smooth 1.25x zoom punch at zoom_at_sec
  - Burned-in punchy 3-word captions from faster-whisper timestamps
  - Subtle top-right creator credit (@author)
  - Concatenated master rough cut into workspace/04_rough_cuts/

Usage:
    python src/render_rough_cut.py \
      --plan C:/Users/PC/.gemini/antigravity/scratch/gta6_clips/workspace/03_analysis/edit_plan_gta6_2026-11-19.json \
      --project-dir C:/Users/PC/.gemini/antigravity/scratch/gta6_clips
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def format_srt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        seconds += 1
        ms = 0
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_segment_srt(
    words: list[dict[str, Any]], seg_start: float, seg_end: float, out_srt: Path
) -> bool:
    rel_words = [
        {
            "word": w["word"],
            "start": max(0.0, float(w["start"]) - seg_start),
            "end": max(0.1, float(w["end"]) - seg_start),
        }
        for w in words
        if float(w["end"]) >= seg_start and float(w["start"]) <= seg_end and w.get("word")
    ]
    if not rel_words:
        return False

    lines = []
    idx = 1
    for i in range(0, len(rel_words), 3):
        chunk = rel_words[i : i + 3]
        t0 = chunk[0]["start"]
        t1 = max(chunk[-1]["end"], t0 + 0.35)
        text = " ".join(c["word"] for c in chunk)
        lines.append(f"{idx}\n{format_srt_time(t0)} --> {format_srt_time(t1)}\n{text}\n")
        idx += 1
    out_srt.write_text("\n".join(lines), encoding="utf-8")
    return True


def escape_ffmpeg_path(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def render_segment(
    seg: dict[str, Any],
    inbox_dir: Path,
    words: list[dict[str, Any]],
    out_mp4: Path,
    work_dir: Path,
) -> None:
    src_path = inbox_dir / seg["source_file"]
    if not src_path.exists():
        raise FileNotFoundError(f"Missing clip file: {src_path}")

    start_sec = float(seg["start_sec"])
    end_sec = float(seg["end_sec"])
    dur = max(1.0, end_sec - start_sec)

    srt_path = work_dir / f"{out_mp4.stem}.srt"
    has_srt = build_segment_srt(words, start_sec, end_sec, srt_path)

    zoom_at = seg.get("zoom_at_sec")
    credit = (seg.get("author") or "creator").replace(":", "").replace("'", "")

    # Composite centered foreground over blurred 1080x1920 background at 30fps,
    # then apply smooth frame-accurate zoompan punch around zoom_at_sec.
    vf_parts = [
        "[0:v]fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5,setsar=1[bg]",
        "[0:v]fps=30,scale=1080:1920:force_original_aspect_ratio=decrease,setsar=1[fg]",
        "[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1[base]",
    ]
    post = "[base]"
    if zoom_at is not None:
        f0 = max(0, int(round((float(zoom_at) - 0.5) * 30)))
        f1 = f0 + 36  # 1.2s at 30fps
        vf_parts.append(
            f"{post}zoompan=z='if(between(on\\,{f0}\\,{f1})\\,1+0.22*sin(PI*(on-{f0})/36)\\,1)':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30[zout]"
        )
        post = "[zout]"

    fontfile = "C\\:/Windows/Fonts/arialbd.ttf"
    overlay_chain = (
        f"{post}drawtext=fontfile='{fontfile}':text='@{credit}':"
        "x=w-tw-36:y=56:fontsize=28:fontcolor=white@0.85:box=1:boxcolor=black@0.45:boxborderw=8"
    )
    if has_srt:
        srt_esc = escape_ffmpeg_path(srt_path)
        overlay_chain += (
            f",subtitles='{srt_esc}':force_style="
            "'FontName=Arial,FontSize=20,Bold=1,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Alignment=2,MarginV=240'"
        )
    overlay_chain += "[vout]"
    vf_parts.append(overlay_chain)
    vf = ";".join(vf_parts)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start_sec:.2f}",
        "-t", f"{dur:.2f}",
        "-i", str(src_path),
        "-filter_complex", vf,
        "-map", "[vout]",
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        str(out_mp4),
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0:
        err = res.stderr.decode("utf-8", errors="ignore").splitlines()[-15:]
        raise RuntimeError("FFmpeg failed:\n" + "\n".join(err))


def concat_segments(seg_files: list[Path], final_out: Path) -> None:
    list_file = final_out.parent / "concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in seg_files),
        encoding="utf-8",
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(final_out),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 3: Deterministic 1080x1920 Rough-Cut Renderer")
    parser.add_argument("--plan", type=Path, required=True, help="Path to edit_plan_*.json")
    parser.add_argument("--project-dir", type=Path, required=True, help="Channel project directory")
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    channel_id = plan["channel_id"]
    # Extract YYYY-MM-DD from plan filename
    parts = args.plan.stem.split("_")
    run_date = parts[-1] if len(parts[-1]) == 10 else "latest"

    project_dir = args.project_dir.resolve()
    inbox_dir = project_dir / "workspace" / "01_inbox_raw" / run_date
    analysis_dir = project_dir / "workspace" / "03_analysis"
    rough_dir = project_dir / "workspace" / "04_rough_cuts" / run_date
    rough_dir.mkdir(parents=True, exist_ok=True)

    transcripts_path = analysis_dir / f"transcripts_{channel_id}_{run_date}.json"
    transcripts = json.loads(transcripts_path.read_text(encoding="utf-8")) if transcripts_path.exists() else {}

    rendered: list[Path] = []
    for idx, seg in enumerate(plan.get("segments", []), start=1):
        out_seg = rough_dir / f"seg_{idx:02d}.mp4"
        print(f"[Render] Segment {idx}/{len(plan['segments'])}: {seg['source_file']} ({seg['start_sec']}s -> {seg['end_sec']}s)...")
        render_segment(seg, inbox_dir, transcripts.get(seg["source_file"], []), out_seg, rough_dir)
        rendered.append(out_seg)

    if not rendered:
        raise SystemExit("No segments rendered.")

    final_out = rough_dir / f"rough_cut_{channel_id}_{run_date}.mp4"
    concat_segments(rendered, final_out)
    print(f"\nDone! Rough cut ready: {final_out}")


if __name__ == "__main__":
    main()
