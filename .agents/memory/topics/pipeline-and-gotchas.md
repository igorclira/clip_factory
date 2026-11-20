# Pipeline & Gotchas

> Consolidated learnings for the shared `clip_factory` engine. Updated by `memory-dreaming`.

## Architecture (5-Stage Pipeline)
- Shared core at `C:/Users/PC/.gemini/antigravity/scratch/clip_factory/` powering separate channel workspaces (`gta6_clips`, `wow_forever_clips`).
- Pipeline flow: `src/scout_clips.py` → local `review_sheet.html` curation → `src/analyze_gemini.py` → `src/sound_editor.py` → `src/render_remotion.py` (Remotion Studio in `remotion_studio/`).
- Shared audio assets live in `shared_assets/sfx/` (curated Epidemic Sound WAVs + `<2.5s` trimmed mainstream voice blips) and `shared_assets/sfx_library/` (400 scraped viral MP3s), unified by `src/build_sound_libraries.py` into `sound_library.json` (484 sounds) and `music_library.json` (2 tracks).

## Remotion & FFmpeg Gotchas (Verified Fixes)
- **TikTok VFR/deep-seek crashes:** `OffthreadVideo` fails on raw VFR TikTok `.mp4`s (`No frame found`). `render_remotion.py` pre-trims every segment to `0.0s` CFR 30fps (`-fps_mode cfr -g 15`) and stages ONLY referenced clips and SFX into `remotion_studio/public/`.
- **Real slow-motion (`playbackRate`):** Pre-baked in FFmpeg via `setpts=(1/rate)*PTS` + chained `atempo` filters, then `playbackRate` is stripped from `_staged_*.json` so Remotion does not double-scale duration. All cue timestamps inside a slow-mo segment must be in post-slowmo output seconds.
- **Letterboxed 16:9 / 4:3 clips (`letterboxCrop`):** Use `letterboxCrop: { yPct, hPct }` in `render_remotion.py` to crop out black bars or baked top text and composite full-width gameplay over a blurred darkened `1080×1920` backdrop (`gblur=sigma=28,eq=brightness=-0.16`). Far cleaner than high `cropZoom` which destroys FOV or leaks top text.
- **Vocal isolation (`isolateVocals: true`):** Mono sum + `260Hz–3600Hz` bandpass + `acompressor` keeps streamer/NPC voices legible over replacement BGM (`bgmVolume ~0.24`).
- **Remotion `<TransitionSeries.Transition>` TS error:** Do not mix `wipe(...) | slide(...)` in one ternary prop — render separate conditional JSX branches.
- **Final master loudness:** Always run FFmpeg `-c:v copy -af loudnorm=I=-14:TP=-1.0:LRA=11` after Remotion render.

## Whisper, Diarization & Dual-Zone Karaoke Captions
- **`faster-whisper` + `av 19.0.2` crash:** Never pass video paths directly to `WhisperModel.transcribe()`; decode to 16kHz float32 PCM via `ffmpeg` (`decode_audio_ffmpeg()`) and pass numpy array. Local cached model is `"base"` (`local_files_only=True` offline).
- **Stretched Whisper words:** Whisper can stretch a single word across multi-second silence (e.g., 8.3s). `build_whisper_captions()` clamps words `>1.35s` to `+0.85s` and emits `words: [{text, startSec, endSec}]`.
- **Dual-zone captions (`SmartCaptions.tsx`):**
  - `streamer`: Top zone near streamer's mouth (`streamerCaptionY`, default `27%`), white base + `#FFE600` yellow active spoken word (`1.10x` pop). Always check baked TikTok banners during zooms (`originY` shifts banners vertically — adjust `streamerCaptionY` per clip and inspect rendered frames).
  - `npc`: Bottom zone (`bottom: 215px`), italic `#00F0FF` electric cyan with quotes (white active word).
  - `editorial`: Contextual hot-pink (`#FF5CD6` / `#A855F7`) mid-screen deadpan popups.
- **Mandatory Multimodal Video + Audio Diarization (`analyze_gemini.py`):**
  - NEVER run audio-only speaker diarization (in v7 it mixed NPC lines into top streamer captions and sent streamer reactions to the bottom). ALWAYS inspect video + audio together (checking streamer facecam lip movement + in-game GTA subtitles), and never let a caption chunk cross a speaker turn.
- **`analyze_gemini.py` v7 Schema Parity & Bugfix:**
  - Fixed dead-code bug in `plan_to_remotion_props()` (now emits processed `captions` + `_attach_karaoke_words()` fallback instead of ignoring Whisper fallback), upgraded Pydantic schemas (`ZoomCue` 4 modes, `WordCue`, `SegmentPlan.streamerCaptionY`, `playbackRate`, `transitionIn`, `comedy_beat_summary` -> `comedyBeatSummary`), auto-injects `<channel>-comedy-director/SKILL.md`, and removed noisy 450-line uncurated SFX dumps.

## Camera Choreography (`MontageVideo.tsx`)
- Never homogenize every clip to mild `smooth` zoom. Vary across 4 modes: `aggressive_punch` (up to `2.05x` + `ImpactShake` on brutal hits), `slow_creep` (up to `1.70x` ease-out over slow-mo reveals), `snap_hold` (up to `1.75x`), and `smooth` (up to `1.42x`).

## Sound Editor & Library Gotchas
- **Category classification (`build_sound_libraries.py`):** `meme_*` / `hl_*` / `ah_shit_here_we_go_again_cj.mp3` classify as `meme` (uses `_has_token()` regex boundaries so `"hit"` never matches inside `"shit"`).
- **Spoken Voice-Blip `onset_sec` & `align_mode`:** `build_sound_libraries.py` measures both `peak_sec` and `onset_sec` and assigns `align_mode: "onset"` for spoken voice blips vs. `"peak"` for impacts/transitions/percussive stingers. `sound_editor.py` aligns `"onset"` blips by `t - onset_sec` (fixing early firing like `meme_oh_hell_no_2s.mp3` where `peak_sec=2.21s`) and `"peak"` SFX by `t - peak_sec - 0.033`.
- **Full-Segment Context Handoff (`sound_editor.py`):** `extract_segment_summaries(props)` hands Gemini grouped streamer/NPC dialogue, zoom modes, editorial popups, and `comedyBeatSummary` across ALL segments (fixing the old `speech_windows[:20]` truncation) so voice blips drop in speech gaps without talking over punchlines.
- **Prompt signal-to-noise:** Send only the curated high-signal `<2.5s` mainstream English voice-blip roster + clean transitions/impacts (with rich `VOICE_BLIP_CURATED_META` `use_when` tags) so Gemini stops defaulting to generic booms/bells.
- **Trimming voice blips:** Trim mainstream voice blips/stingers to `<=2.4s` with `silenceremove` + `0.15s` trailing `afade` to prevent clicks and keep fair-use-sized punch.
- **`sound_editor.py` flags:** Account for `playbackRate` in `extract_clip_events()` and `extract_segment_summaries()`, fall back immediately on `429` (`gemini-3.5-flash-lite`), and use `--ignore-recent` (or same-date exclusion) when iterating versions (`v6 → v7`) of the same video.

## Sourcing APIs
- **Apify TikTok (`clockworks~tiktok-scraper`, `shouldDownloadVideos: true`):** Pass `Authorization: Bearer <APIFY_TOKEN>` header on BOTH actor requests AND `api.apify.com` media downloads (never `?token=` in URL).
- **Reddit:** Unauthenticated `.json` returns `403`; V1 scout relies on Twitch Helix + YouTube Data API v3 + Apify TikTok.
