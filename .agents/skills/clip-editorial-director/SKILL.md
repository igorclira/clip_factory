---
name: clip-editorial-director
description: >-
  Use this skill when planning, scripting hooks, reviewing curated clips, or
  generating structured JSON edit plans for the wow_forever_clips or gta6_clips
  short-form channels.
---

# Clip Editorial Director

Follow this procedure whenever building a montage edit plan or refining hooks/titles for `gta6_clips` or `wow_forever_clips`.

## Required Inputs
1. Read `<project>/config/channel.json`
2. Read `<project>/config/style_guide.md`
3. Read `<project>/config/few_shot_plans.json` and `<project>/config/learnings.md`
4. Read `clip_factory/shared_assets/sound_library.json` (and `meme_map.json`)
5. Read the user's curated clip list and directorial notes from `<project>/workspace/02_curated/`

## Editorial & v7 Production Rules
1. **Creator Rewards Target (62–85s Flexible):** Target 62–75s for TikTok Creator Rewards, and allow up to ~85s when a clip's comedic setup/payoff genuinely needs room to breathe. Never pad with dead air.
2. **Dual-Zone Color-Coded Karaoke Captions:**
   - Diarize speech explicitly into `streamer` vs. `npc` — never dump all Whisper output into `streamer`.
   - **`streamer`:** Top zone near mouth (`streamerCaptionY`, default `27%`), white base with bright yellow (`#FFE600`) word-by-word karaoke highlight (`words` array).
   - **`npc`:** Bottom zone (`bottom: 215px`), italic electric cyan (`#00F0FF`) in quotes.
   - **`editorial`:** Deadpan hot-pink mid-screen popups (`"INSTANT REGRET"`, `"DOWN GOES GRANDMA"`).
   - Clamp any abnormally stretched Whisper words (`>1.35s`) so captions never linger across silence.
3. **Varied Camera Choreography & Clean Framing:**
   - Vary zoom modes per situation (`aggressive_punch` up to `2.05x` + `ImpactShake` for brutal hits; `slow_creep` + FFmpeg `playbackRate` slow-mo for dramatic jaw-drop reveals; `snap_hold` for punchy beats; `smooth` for subtle focus).
   - Use `letterboxCrop: { yPct, hPct }` on letterboxed 16:9 / 4:3 clips with black bars or baked top text so gameplay sits cleanly over a blurred darkened `1080×1920` backdrop.
4. **Copyright & Vocal Clarity Check:**
   - For `gta6_clips`, check for car radio or unfitting clip music; set `isolateVocals: true` when swapping in `bgmFile` (`bgmVolume ~0.24`) so funny NPC complaints stay crystal clear.
   - For `wow_forever_clips`, set `isolateVocals: true` if streamer Spotify/copyrighted music is audible.
5. **Pre-Delivery Visual QA (Mandatory):**
   - After rendering, run `ffprobe` + loudness check (`-14 LUFS`), then extract 5–8 key frames across every segment and visually inspect them to verify zero black bars, zero cropped top text, and zero caption collisions with baked-in TikTok/Shorts banners (especially during zooms).

## Handling `rejected_feedback`
- Never treat `rejected_feedback` as a blind dump or automatic creator/topic ban.
- Read every clip's individual `feedback_note` carefully and distinguish between:
  - **Context/timing skips** (good clip, just doesn't fit today's montage theme — keep eligible for another theme)
  - **Format/quality preferences** (already over-edited CapCut clip, slow pacing, story spoiler — refine `config/style_guide.md` or `config/learnings.md`)
  - **Explicit source exclusions** (only block a creator, tag, or format in `config/scout_queries.json` when specifically requested or a clear multi-clip pattern emerges)
- Always summarize what you learned from `rejected_feedback` before applying changes to `scout_queries.json` or `style_guide.md`.

## Meme & Pop-Culture Voice Blip Restraint
- **Mainstream `<2.5s` voice blips over generic SFX:** Prioritize recognizable pop-culture voice blips/stingers (`<=2.5s`, cleanly faded) on real comedic payoffs instead of generic stock booms, pipes, or arcade bells.
- **Nuance over spam:** Iconic game/meme SFX (e.g., Half-Life SFX, Avengers `<2.4s` horn sting) work ONLY when peak-synced to exact physical/emotional beats. Overusing a meme or desyncing voice/SFX from on-screen action instantly turns it cringe.
- **Commercial Music Safety:** Never use `>2.5s` of clean record-label movie scores — use short `<=2.4s` stings/parodies or Epidemic Sound tracks instead.

## Reference Third-Party Skills
Consult `skills/screenwriting-skills`, `skills/visual-skills`, `skills/video-editing-skill`, and `skills/remotion-skills` when refining pacing, visual storytelling, or Remotion render components.
