# Clip Factory — Pipeline Modules (`src/`)

Planned deterministic scripts (all take `--channel wow_forever|gta6`):

1. `scout_clips.py` — Fetches candidate viral & small-channel outlier clips (V1: Twitch Helix + Reddit + Apify TikTok; V2: YouTube Data API + Apify X), deduplicates via SQLite, scores by Outlier Ratio + Velocity, downloads into `workspace/<channel>/01_inbox_raw/`, and generates `review_sheet.html`.
2. `analyze_gemini.py` — Runs `faster-whisper` word timestamps + audio volume-peak detection on curated clips (`02_curated/`), calls Gemini API with `config/<channel>/style_guide.md` and `few_shot_plans.json`, and writes structured JSON edit plans to `03_analysis/`.
3. `render_rough_cut.py` — Deterministic 1080x1920 vertical renderer (Remotion / FFmpeg) that applies zooms, karaoke captions, audio ducking (`-14dB`), vocal isolation if flagged, and mapped memes/SFX from `shared_assets/meme_map.json` into `04_rough_cuts/`.
4. `package_markers.py` — Exports timeline/cue markers and platform metadata (titles, hooks, posting slots) for final polish into `05_ready_to_post/`.
