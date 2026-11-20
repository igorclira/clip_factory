---
name: style-extractor
description: >-
  Use this skill when the user provides reference TikToks, YouTube Shorts, or
  highlight videos to reverse-engineer their pacing, hooks, zoom timing, and
  meme cadence into config/<channel>/style_guide.md and few_shot_plans.json.
---

# Reference Style Extractor

Reverse-engineer 5–8 top-performing reference Shorts/TikToks into reusable editing DNA for `wow_forever` or `gta6`.

## Steps
1. For each reference video, run a multimodal video + audio audit capturing:
   - **Hook Structure (0:00–0:04):** Spoken words, visuals, and curiosity gap.
   - **Pacing & Cut Rhythm:** Average seconds between cuts, micro-zooms, or pattern interrupts.
   - **Zoom & Framing Mechanics:** Exact timestamps where the editor zooms into UI elements (HP bars, raid frames, NPC faces, ragdolls) and why.
   - **Meme & SFX Cadence:** Exact timestamps of meme cutaways, freeze-frames, or SFX relative to the gameplay beat.
   - **Voiceover vs. Raw Audio:** How the narrator adds context without merely describing the screen.
   - **Transition Formula:** How Clip 1 bridges into Clip 2 and Clip 3 to hold retention past 60s.
2. Synthesize recurring rules across all reference videos and update `config/<channel>/style_guide.md`.
3. Save 2–3 of the strongest timestamped breakdowns as structured JSON examples inside `config/<channel>/few_shot_plans.json`.
