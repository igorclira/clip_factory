# sound_rules.md (v2)

## Rules
1. Hook: put an impact, bass hit or boom on frame 1 to 3. The first 2 seconds must sound loud and confident.
2. Sync & Placement: align `on_impact` SFX on the event frame (1–2 frames early for peaks, exact onset for voice blips). Use `after_impact` (+250ms) for reaction memes commenting on a hit, and `before_moment` for risers/anticipation. Use whooshes on transitions and cuts.
3. Mode-Aware Meme Density:
   - `funny`: max 3 memes per 30s (capped at 4 per video), >=5s apart.
   - `action`: max 1 meme per 30s (capped at 2 per video); risers/impacts/whooshes may be denser.
   - `hybrid`: play it straight with action SFX until the comedic turn/wipe, then drop 1–2 earned memes on the payoff.
   Never use memes as filler — silence is better than a forced meme.
4. Silence before payoff: cut or drop the music by 15 dB about 0.3 to 0.6 seconds before a punchline, hit the meme sound, then bring the music back.
5. Music: match energy to the clip (boss fights and PvP at energy 4-5, funny raid wipes or chill at 2-3). Prefer tracks without vocals under raid comms. Line cuts up with the track's beats when possible.
6. Ducking & Dialogue Protection: when game audio or raid comms are important, lower the music 8 to 12 dB under it. NEVER talk over the funniest raid-lead or streamer line — place spoken memes in speech gaps or right after the setup line.
7. No stacking or near-duplicates: never play 2 meme sounds or more than 2 SFX within 0.5 seconds of each other, and never use two memes from the same `dedupe_group` (e.g., two sad horns or two disbelief reactions) in one video.
8. Variety & Copyright Discipline: don't reuse the same meme sound twice in a video or in 3 videos in a row (`recent_sound_plans.json`). Prefer lower `copyright_risk` when two sounds tell the same joke, and cap `high`-risk sounds at 2 per short. Skip GTA-native stingers by default unless explicitly requested.
9. Ending: finish on a clean button (a final hit or a music stop) to help the video loop — never leave a meme ringing into black.
10. Mix: normalize the final audio to -14 LUFS integrated with a -1 dB true peak.

## Changelog
| Version | Date | Change | Reason | Target Metric |
| :--- | :--- | :--- | :--- | :--- |
| v2 | 2026-11-20 | Added v2 WoW Forever ruleset (`montage_mode`, `placement`, `dedupe_group`, `copyright_risk` cap) | Parity with GTA 6 semantic sound placement | Meme hit rate & completion rate |
