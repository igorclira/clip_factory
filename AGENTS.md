# Clip Factory — Project Rules

This workspace operates a dual-channel short-form gaming clip factory for:
- **`wow_forever`** (World of Warcraft Forever — English / Global)
- **`gta6`** (Grand Theft Auto VI — English / Global)

## Non-Negotiable Rules

1. **Strict Channel Isolation:** Never mix assets, configs, transcripts, style guides, or outputs between `wow_forever` and `gta6`. Every script must accept `--channel wow_forever|gta6`.
2. **60+ Second Rule (TikTok Creator Rewards):** Every montage must target **62–70 seconds** total runtime (3–4 clips for WoW Forever, 4–5 clips for GTA 6). Never pad dead air just to reach 60s.
3. **Transformative Originality (YouTube & TikTok):** Never merely describe what is visible on screen. Every hook/narration must add mechanic context, stakes, or comedic framing.
4. **Audio Copyright Safety:**
   - **GTA 6:** NEVER allow in-game car radio music in the final render. Flag clips with car radio as `isolate_vocals: true` so the pipeline strips music and lays licensed/royalty-free audio underneath. No unedited story cutscenes or spoilers.
   - **WoW Forever:** Flag clips where streamers play copyrighted Spotify/background music for vocal isolation.
   - Always apply audio ducking (`-14dB` on game/streamer audio) whenever the narrator hook speaks.
5. **Clean Masters Only:** Never cross-post watermarked files between TikTok and YouTube Shorts. Always render clean 1080x1920 watermark-free masters into `workspace/<channel>/05_ready_to_post/`.
6. **Deterministic Rendering:** Use Gemini API for multimodal video+audio analysis and structured JSON edit plans; use deterministic code (Remotion / FFmpeg + `faster-whisper`) for rendering and timing alignment.
7. **Human-in-the-Loop Curation:** Every clip passes through `01_inbox_raw` → `review_sheet.html` → `02_curated` with human approval and optional directorial notes before Gemini analysis.

## Reference Skills
- Workspace skills live in `.agents/skills/` (auto-discovered by Antigravity).
- Third-party reference skill repositories are cloned under `skills/`.

## Memory & Dreaming
- Read `.agents/memory/MEMORY.md` before substantive work; open topic files on demand.
- Capture quick mid-session learnings/gotchas in `.agents/memory/inbox.md` (do not bloat this file).
- Out-of-band consolidation & pruning are handled by the global `memory-dreaming` skill.
