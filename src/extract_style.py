"""
Clip Factory — Multimodal Style & Editing DNA Extractor

Forensically analyzes reference YouTube videos using Gemini's native YouTube video+audio
ingestion (with exact start_offset/end_offset & high FPS sampling so fast zoom punches,
SFX hits, and subtitle styles aren't missed), then synthesizes a concrete Editing &
Curation Blueprint combining multiple reference channels.

Usage:
    python src/extract_style.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

CORE_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = CORE_ROOT / "workspace" / "style_references"

REFERENCES = [
    {
        "id": "chm_wow_forever_2",
        "channel": "Classic Hardcore Moments",
        "role": "editing_craft_master",
        "url": "https://www.youtube.com/watch?v=h7lnlrKoDz0",
        "title": "WoW Forever Moments #2",
        "windows": [("0s", "180s"), ("420s", "540s")],
    },
    {
        "id": "chm_wow_forever_1",
        "channel": "Classic Hardcore Moments",
        "role": "editing_craft_master",
        "url": "https://www.youtube.com/watch?v=oz-UThz-C1Q",
        "title": "WoW Forever Moments #1",
        "windows": [("0s", "180s")],
    },
    {
        "id": "chm_top_250_climax",
        "channel": "Classic Hardcore Moments",
        "role": "editing_craft_master",
        "url": "https://www.youtube.com/watch?v=jSGPew1vqDE",
        "title": "Top 250 Classic Hardcore Moments (Top Climax Window)",
        "windows": [("10500s", "10680s")],
    },
    {
        "id": "red_arcade_1in1m",
        "channel": "Red Arcade",
        "role": "gta_clip_selection_and_pacing_master",
        "url": "https://www.youtube.com/watch?v=MmKByWYnaws",
        "title": "1 in 1,000,000 GTA 5 Moments!",
        "windows": [("0s", "180s")],
    },
    {
        "id": "red_arcade_top1000",
        "channel": "Red Arcade",
        "role": "gta_clip_selection_and_pacing_master",
        "url": "https://www.youtube.com/watch?v=_F0GvHSlBiw",
        "title": "Top 1000 BEST GTA V Clips of all time",
        "windows": [("0s", "150s"), ("10800s", "10950s")],
    },
    {
        "id": "red_arcade_13years",
        "channel": "Red Arcade",
        "role": "gta_clip_selection_and_pacing_master",
        "url": "https://www.youtube.com/watch?v=GXbtw3x37tk",
        "title": "13 Years Of GTA 5 | Best Clips Of All Time",
        "windows": [("0s", "180s")],
    },
]

FORENSIC_PROMPT = """
You are a senior gaming video editor and viral content strategist conducting a frame-accurate
forensic audit of this reference video (watching BOTH visuals and audio carefully).

Channel: {channel}
Video: {title}
Role in our research: {role}
Time window(s) analyzed: {windows}

Provide a DENSE, concrete, timestamped technical breakdown covering EVERY category below.
Be hyper-specific — no generic advice! Quote exact timestamps, exact SFX names/descriptions,
exact zoom targets, exact visual gags, and exact subtitle styling:

1. **Creator Credit Badge & Framing:**
   - Exact screen position, icon style, font weight/size, color, background (or transparent), animation in/out, and how long it stays visible.
2. **Subtitle & Typography Design (CRITICAL):**
   - Exact visual look (font style, weight, outline/stroke vs drop shadow, color-coding per speaker, position on screen).
   - What gets subtitled vs what is intentionally NOT subtitled (e.g., streamer reaction vs random game/NPC chatter).
   - Word-grouping count, pop/bounce animation, and timing precision.
3. **Contextual Zooms, Pans, Freeze-Frames & Visual Shenanigans (TIMESTAMPED EXAMPLES):**
   - List 6-10 specific timestamped moments showing HOW the editor uses zooms, crops, freeze-frames, slow-mo, screen shakes, B&W desaturation, red/meme overlays, or visual callouts.
   - Crucial: WHAT is the zoom aimed at (facecam? health bar? NPC? projectile? chat?), how fast is the zoom (hard punch cut vs smooth ramp), and what comedic or tension beat does it serve?
4. **SFX & Music Architecture (TIMESTAMPED EXAMPLES):**
   - List the exact recurring SFX categories used (not generic "whoosh" — specify e.g. subtle bass thud, record scratch, cartoon slip, metal pipe, heartbeat, cinematic riser, abrupt music cut to silence, meme stingers).
   - How does the editor combo a zoom + SFX + audio silence/music drop to elevate an ordinary clip into a hilarious moment?
   - How is background music used (or intentionally absent) between clips?
5. **Clip Transitions & Pacing Rhythm:**
   - Average clip length, how quickly each clip gets to the hook/setup, and how the editor cuts OUT right after the punchline (exact comedic beat timing).
   - Exact transition style between clips (hard cut? quick swipe? SFX bridge? black flash? TV static?).
6. **What Makes a Clip Worth Picking (Curation Criteria — Especially for GTA / WoW):**
   - Break down the specific archetypes of clips featured in this video (e.g., instant karma, 1-in-a-million physics chain reactions, absurd NPC timing, confident-statement-followed-by-instant-disaster, clutch escapes, hilarious streamer voice-cracks).
   - What makes a clip IMMEDIATELY rejectable compared to these winners?
"""


def analyze_video(client: genai.Client, model: str, ref: dict) -> str:
    parts: list[types.Part] = []
    for start_off, end_off in ref["windows"]:
        parts.append(
            types.Part(
                file_data=types.FileData(file_uri=ref["url"]),
                video_metadata=types.VideoMetadata(
                    start_offset=start_off,
                    end_offset=end_off,
                    fps=2.0,
                ),
            )
        )

    prompt = FORENSIC_PROMPT.format(
        channel=ref["channel"],
        title=ref["title"],
        role=ref["role"],
        windows=", ".join(f"{a}-{b}" for a, b in ref["windows"]),
    )
    parts.append(types.Part.from_text(text=prompt))

    resp = client.models.generate_content(
        model=model,
        contents=types.Content(role="user", parts=parts),
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return resp.text or ""


def synthesize_blueprint(client: genai.Client, model: str, audits: dict[str, str]) -> str:
    combined = "\n\n".join(
        f"================ {k} ================\n{v}" for k, v in audits.items()
    )
    synth_prompt = f"""
You are designing the production bible for TWO gaming clip channels (`wow_forever` and `gta6`)
and an automated Remotion + Gemini + Epidemic Sound editing pipeline.

Below are forensic multimodal audits of 6 reference videos from:
- **Classic Hardcore Moments** (master of editing craft: contextual zooms, SFX combos, visual gags, creator badge, comedic timing)
- **Red Arcade** (master of GTA 5 clip curation, viral clip archetypes, pacing, transitions)

Synthesize these audits into ONE ultra-actionable **Master Editing & Curation Blueprint** with these exact sections:

1. **The Hybrid Formula (Classic Hardcore Moments Craft × Red Arcade GTA Selection):**
   - Exact concrete rules for blending CHM's transformative editing shenanigans with Red Arcade's viral clip archetypes (adapted for 62-70s 9:16 vertical Shorts/TikToks AND future long-form compilations).
2. **Exact Visual Spec (for Remotion React Components):**
   - Creator Credit Badge spec (for both `gta6_vaporwave` and `wow_classic` themes).
   - Subtitle spec (font family/weight, exact stroke/shadow, color-coding for Streamer vs Funny NPC vs Editorial callout, placement, max words per line, strict anti-lingering rule).
   - Visual Shenanigans Toolkit (exact catalog of reusable Remotion effects we should build: e.g., hard snap-zoom to bounding box, freeze-frame + monochrome + vignette, quick screen shake, music cut-to-silence before punchline, arrow/circle callout, slow-mo replay).
3. **Exact SFX Shopping List (for Epidemic Sound MCP `SearchSoundEffects`):**
   - 15-20 SPECIFIC, real-world search queries to run on Epidemic Sound MCP to build a killer non-generic SFX library mapped to exact comedic/tension situations (e.g., what SFX to trigger on a freeze-frame, on a sudden fail, on a subtle zoom-in, on a ragdoll impact, on an ironic boast).
4. **GTA 6 & WoW Forever Clip Selection Rubric (for Fine-Tuning Our Scout & Curating Agent):**
   - Concrete **Pick Criteria** (archetypes that consistently go viral on Red Arcade / CHM) with examples.
   - Concrete **Auto-Reject Criteria** (what wastes time and kills retention).
   - Specific keywords/tags/signals to upgrade `scout_queries.json` and Gemini's scoring prompt.

FORENSIC AUDITS:
{combined}
"""
    resp = client.models.generate_content(
        model=model,
        contents=synth_prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return resp.text or ""


def main() -> None:
    load_dotenv(CORE_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY missing in clip_factory/.env")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)

    preferred = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
    avail = {m.name.replace("models/", "") for m in client.models.list()}
    model = next((m for m in preferred if m in avail), "gemini-2.5-flash")
    print(f"[StyleExtractor] Using model: {model}")

    audits: dict[str, str] = {}
    for idx, ref in enumerate(REFERENCES, start=1):
        out_md = OUT_DIR / f"{ref['id']}.md"
        if out_md.exists() and out_md.stat().st_size > 500:
            print(f"[{idx}/{len(REFERENCES)}] Using cached audit: {out_md.name}")
            audits[ref["id"]] = out_md.read_text(encoding="utf-8")
            continue

        print(f"[{idx}/{len(REFERENCES)}] Watching & auditing {ref['channel']} — {ref['title']} ({ref['windows']})...")
        t0 = time.time()
        try:
            text = analyze_video(client, model, ref)
            out_md.write_text(text, encoding="utf-8")
            audits[ref["id"]] = text
            print(f"  Done in {time.time() - t0:.1f}s -> {out_md.name} ({len(text)} chars)")
        except Exception as exc:
            print(f"  FAILED {ref['id']}: {exc}")

    if not audits:
        raise SystemExit("No audits succeeded.")

    print("\n[StyleExtractor] Synthesizing Master Editing & Curation Blueprint...")
    blueprint = synthesize_blueprint(client, model, audits)
    bp_path = OUT_DIR / "editing_dna_synthesis.md"
    bp_path.write_text(blueprint, encoding="utf-8")
    print(f"Done! Saved Master Blueprint -> {bp_path} ({len(blueprint)} chars)")


if __name__ == "__main__":
    main()
