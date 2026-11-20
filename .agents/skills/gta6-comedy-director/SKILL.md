---
name: gta6-comedy-director
description: Concise GTA 6 multimodal director contract for analyze_gemini.py.
---

# GTA 6 Comedy Director Rules

1. Always set `montage_mode` (`funny` | `action` | `hybrid`) for the short. Use `hybrid` when a serious chase/flex turns into a sudden absurd fail.
2. Populate 1–3 structured `beat_tags` per segment (`atSec`, `trigger`, `humor_type`, `energy`, `placement_hint`, `note`). Describe the **situation** in `note` — never name a sound file.
3. Leave `sfx: []` empty — `sound_editor.py` handles all rule-checked meme/SFX placement.
4. **Strict Speaker Separation (Top vs. Bottom):**
   - `role: "streamer"` → **TOP zone** (white + yellow karaoke). ONLY real-life streamer/commentator reactions spoken into their mic (verify visually via facecam lip movement + audio timbre).
   - `role: "npc"` → **BOTTOM zone** (cyan + mint subtitle pill with quotes). ALL in-game voices: NPCs, cops, bystanders, radio, and in-game player-character voice lines. Never mix in-game lines into top streamer captions.
5. **Visual Subtitle Verification (Mandatory):** Never guess `streamer` vs `npc` from transcript text alone — inspect video frames for on-screen in-game subtitles AND check whether the streamer's mouth moves on facecam.
6. **Split-Screen Game-Only Zooms (`splitY` + `target`):** On split-screen streamer clips, set `splitY` (`0..100` seam separating top facecam from bottom gameplay) and put `target: "game"` on gameplay zooms so the streamer's facecam NEVER gets cropped out of frame. Whenever a clip wants to highlight streamer shock, add a separate `target: "facecam"` zoom on the facecam window.
7. **Streamer-First Audio:** Never overlap a meme or loud SFX over a streamer's vocal reaction — the streamer IS the focus of these compilations. Place memes strictly in speech gaps or after the reaction line finishes.
8. **Sleek CTA Inserts (Sponsor-Ready):** Include a quick `~1.8s` mid-roll CTA interstitial (`kind: "cta"`, `variant: "mid"`) asking for Like/Follow/Subscribe, and a `~3.0s` outro CTA (`variant: "outro"`) with a clean bottom `sponsorText` slot for future brand reads.
