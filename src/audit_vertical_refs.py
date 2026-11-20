"""
Clip Factory — 9:16 Vertical Contrastive Style Auditor (GOOD vs. BAD AI SLOP vs. MIXED)

Audits vertical YouTube Shorts with explicit user verdicts so Gemini learns BOTH:
  - What makes great 9:16 gaming editing feel human, readable, and funny
  - What makes bad AI-slop / over-edited Shorts feel awful so our pipeline NEVER does it

Outputs:
  - workspace/style_references/vertical_9x16/<id>.md (per-Short forensic audit)
  - workspace/style_references/vertical_9x16/vertical_9x16_constitution.md (master 9:16 rules)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

CORE_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = CORE_ROOT / "workspace" / "style_references" / "vertical_9x16"

CONTRASTIVE_PROMPT = """
You are a senior 9:16 vertical gaming Short / TikTok editor conducting a frame-accurate
forensic audit (watching BOTH visuals and audio at 2 fps).

Short Label: {label}
User's Explicit Verdict: {verdict}
User's Exact Notes: {notes}

Analyze this 9:16 vertical Short specifically to teach our Remotion + Gemini pipeline HOW TO
FRAME AND EDIT 9:16 VERTICAL GAMING VIDEOS PROPERLY (and what to NEVER do):

1. **9:16 Vertical Framing & Layout (CRITICAL):**
   - How is 16:9 gameplay adapted to 9:16? (Split-screen facecam top + gameplay bottom? Centered crop with zoom? Blurred background? Black bars?)
   - How much of the gameplay is kept visible so the viewer ALWAYS understands what is happening?
2. **Zoom Restraint & Scale:**
   - Exact zoom scales used (e.g., subtle 1.15x-1.35x push-in vs hard cut vs NO zoom at all).
   - How often do zooms happen? Are they sparse/earned or spammed?
   - Does any zoom cut off the streamer or hide the main action?
3. **SFX & Audio Restraint:**
   - List EVERY SFX heard with exact timestamp and purpose.
   - How much silence / raw game audio is left untouched vs edited?
   - If the user flagged SFX overuse (like bass drops) or awful narration, pinpoint EXACTLY why it feels bad here.
4. **Why This Matches the User's Verdict ({verdict}):**
   - Pinpoint the 3-5 concrete visual/audio choices that make this Short feel genuinely good (or clearly AI slop / bad).
   - Extract concrete DO / DO NOT rules for our 9:16 Remotion renderer and Gemini director.
"""


def run_with_fallback(client: genai.Client, models: list[str], contents: Any) -> str:
    last_err = None
    for m in models:
        try:
            resp = client.models.generate_content(
                model=m,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.3),
            )
            return resp.text or ""
        except Exception as exc:
            last_err = exc
            print(f"    [Fallback] {m} failed ({str(exc)[:110]})...")
            time.sleep(2)
    raise RuntimeError(f"All models failed: {last_err}")


def audit_refs(refs: list[dict]) -> None:
    load_dotenv(CORE_ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY missing")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)
    avail = {m.name.replace("models/", "") for m in client.models.list()}
    models = [m for m in ("gemini-3.8-flash", "gemini-3.5-flash-lite") if m in avail]
    print(f"[VerticalAuditor] Model chain: {models}")

    audits: dict[str, str] = {}
    for idx, ref in enumerate(refs, start=1):
        out_md = OUT_DIR / f"{ref['id']}.md"
        if out_md.exists() and out_md.stat().st_size > 400:
            print(f"[{idx}/{len(refs)}] Cached: {out_md.name}")
            audits[ref["id"]] = out_md.read_text(encoding="utf-8")
            continue

        print(f"[{idx}/{len(refs)}] Auditing {ref['label']} ({ref['verdict']}) -> {ref['url']} ...")
        parts = [
            types.Part(
                file_data=types.FileData(file_uri=ref["url"]),
                video_metadata=types.VideoMetadata(fps=2.0),
            ),
            types.Part.from_text(
                text=CONTRASTIVE_PROMPT.format(
                    label=ref["label"],
                    verdict=ref["verdict"],
                    notes=ref["notes"],
                )
            ),
        ]
        try:
            text = run_with_fallback(client, models, types.Content(role="user", parts=parts))
            out_md.write_text(text, encoding="utf-8")
            audits[ref["id"]] = text
            print(f"  Saved {out_md.name} ({len(text)} chars)")
        except Exception as exc:
            print(f"  FAILED {ref['id']}: {exc}")

    if not audits:
        raise SystemExit("No vertical audits succeeded.")

    combined = "\n\n".join(f"=== {k} ===\n{v}" for k, v in audits.items())
    synth_prompt = f"""
You are writing the **9:16 Vertical Gaming Editing Constitution** for our Remotion + Gemini pipeline
(`gta6_clips` and `wow_forever_clips`), based on CONTRASTIVE audits of GOOD Shorts, BAD AI-SLOP Shorts,
and MIXED Shorts annotated by the channel owner.

Produce a razor-sharp, practical Constitution with:
1. **9:16 Framing Blueprint (How to Show Gameplay + Creator Clearly With Zero Black Bars):**
   - Exact layout patterns observed in DarkViperAU, Classic Hardcore Moments Shorts, and Gtaquix GOOD (`NZduDPLlCRE`).
   - How to handle 16:9 source clips vs native 9:16 source clips WITHOUT cutting off the streamer or making action unreadable.
2. **Zoom & Effect Restraint Rules (Why 16:9 Rules Broke 9:16):**
   - Exact max zoom scale on 9:16, max zooms per clip, and strict rules on when an effect/icon (like `!`) is EARNED vs SPAM.
3. **SFX & Audio Restraint Rules:**
   - What worked in DarkViperAU / CHM Shorts / `HJkkkrdVyQQ` vs what felt overused (bass-drop spam, awful narration in `BgtgsXbAKJY`).
4. **The "AI Slop" Blacklist (Learned Directly from `rSDerB5TBWM`, `HJkkkrdVyQQ`, and `BgtgsXbAKJY`):**
   - Concrete checklist of dead giveaways that scream "AI engine pumping out slop" (rankings, oversaturation, black bars, robotic narration, constant bass booms, meaningless zooms/icons) so our director NEVER produces them.
5. **Exact Updated Directives for `analyze_gemini.py` & Remotion:**
   - Concrete numeric limits and layout modes we should enforce in code right now.

AUDITS:
{combined}
"""
    print("\n[VerticalAuditor] Synthesizing 9:16 Vertical Editing Constitution...")
    constitution = run_with_fallback(client, models, synth_prompt)
    out_path = OUT_DIR / "vertical_9x16_constitution.md"
    out_path.write_text(constitution, encoding="utf-8")
    print(f"Done! Saved -> {out_path} ({len(constitution)} chars)")


if __name__ == "__main__":
    import json
    refs_file = Path(sys.argv[1])
    audit_refs(json.loads(refs_file.read_text(encoding="utf-8")))
