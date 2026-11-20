# Clip Factory — Pipeline Modules (`src/`)

## Happy Path (5 Stages)
Each channel runs out of its own `--project-dir` workspace containing `config/` and `workspace/` siblings (for example `gta6_clips/` or `wow_forever_clips/`), separate from the shared engine git root:

1. **`scout_clips.py`** — Fetches candidate clips (Twitch Helix, YouTube Data API v3, Apify TikTok), deduplicates via SQLite, downloads into `workspace/01_inbox_raw/<date>/`, and generates an interactive `review_sheet.html` with structured `START` / `END` / `ZOOM` / `MEME` (`trigger`, `humor_type`, `energy`) markers.
2. **`review_sheet.html` (Human Curation)** — Open locally in a browser to shortlist clips, add directorial notes/markers, and export `workspace/02_curated/curated_selection_<channel>_<date>.json`.
3. **`analyze_gemini.py`** — Runs local `faster-whisper` word-level timestamps, uploads curated clips to the Gemini Files API for multimodal video + audio direction (strict Top Streamer vs. Bottom NPC diarization, 4-mode camera choreography, `montage_mode`, and `beat_tags`), merges user `MEME` markers into `beatTags`, and writes `edit_plan_*.json` + `remotion_props_*.json` into `workspace/03_analysis/`.
4. **`sound_editor.py`** — Designs the rule-checked JSON `soundPlan` (`montage_mode`, semantic meme/SFX picks, `max_duration_s` playback caps, `game_duck_windows`, `-15 dB` music `cut_points`, `dedupe_group` + `copyright_risk` + `feedback/placements.csv` guardrails) and injects it into `remotion_props_*.json`.
5. **`render_remotion.py`** — Pre-trims segments to CFR 30fps (baking `playbackRate` slow-mo and `letterboxCrop`), stages ONLY referenced clips and audio into `remotion_studio/public/`, renders `1080×1920` via Remotion (`MontageVideo`), and normalizes the final master to `-14 LUFS / -1.0 dBTP` in `workspace/04_rough_cuts/<date>/`.

## Sound Asset Management
- **`shared_assets/sound_semantics.json`** is the curated semantic roster (`id`, `meaning`, `trigger_moments`, `humor_type`, `montage_mode`, `energy`, `placement`, `copyright_risk`, `freshness`, `dedupe_group`).
- **`build_sound_libraries.py`** measures `length_s`, `peak_sec`, `onset_sec`, `align_mode`, and `loudness_lufs` across `shared_assets/sfx/` and `shared_assets/sfx_library/`, merging semantic fields into `shared_assets/sound_library.json`. **Only rows with `curated_semantic: true` are sent to Gemini**; scraped `sfx_library/` files remain unpromoted until a semantics row is added.
- **`fetch_meme_sfx.py`** downloads curated meme SFX into `shared_assets/sfx/`.
- **`index_sfx.py`** updates `meme_map.json` peaks-only by default (pass `--listen` to call Gemini audio profiling).
- Licensed music beds dropped into `shared_assets/sfx/` are registered via `MUSIC_META_OVERRIDES` in `build_sound_libraries.py`.

## Legacy / Utility Scripts (Not on the Happy Path)
- `render_rough_cut.py` — Legacy FFmpeg-only rough-cut renderer superseded by `render_remotion.py`.
- `scrape_popular_sfx.py`, `extract_style.py`, `audit_vertical_refs.py`, `study_streamer_montages.py` — Offline research and asset-discovery utilities.
