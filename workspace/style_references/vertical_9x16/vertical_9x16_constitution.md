# 9:16 Vertical Gaming Editing Constitution
**Remotion + Gemini Pipeline (`gta6_clips` & `wow_forever_clips`)**  
*Strict enforcement rules derived from contrastive audits of GOOD, BAD, and MIXED Shorts.*

---

## 1. 9:16 Framing Blueprint (Zero Black Bars & Stacked Layout)

Mobile viewers hold their phones vertically. **Floating 16:9 boxes inside black letterbox bars (`MIXED_EXAMPLE` slop) are strictly banned.** Every output must fully occupy the 9:16 canvas using intentional, spatial-aware layout modes.

### A. Layout Mode Matrix
* **Mode 1: Stacked Facecam + Gameplay (Default for Streamers / RP / Chaos Mods)**
  * **Top 30% – 35% ($y: 0\% \to 30\%)$:** Streamer facecam (cropped to 16:9 or square) with a subtle, clean border ($2\text{px}$ white/light gray outline) and static channel/mod header.
  * **Upper-Mid Dead Zone ($y: 30\% \to 36\%)$:** Reserved exclusively for dynamic, high-contrast kinetic subtitles.
  * **Bottom 64% – 70% ($y: 36\% \to 100\%)$:** Gameplay canvas cropped to 9:16. The player character, vehicle, or primary focus must be anchored in the lower-middle half ($y: 50\% \to 70\%$) to maintain peripheral road/action context.
* **Mode 2: Full-Screen Centered Gameplay Crop (Pure Gameplay / Guides / Machinima)**
  * Full 9:16 vertical crop. If the source is 16:9 and requires padding, use **subtle horizontal blurred edge wings** (mirrored, blurred padding of the source footage) rather than solid black bars.
  * Anchor the crop directly to the player character or primary point of interest's horizontal/vertical centerline.

### B. UI & Context Preservation
* **Never crop out critical game notifications:** In RPGs (like *WoW Hardcore*), death logs, chat windows, loot popups, and cast bars must remain visible. If important loot or chat appears at the edge of a 16:9 source, crop and overlay that specific UI box into the 9:16 frame for 1–2 seconds.
* **Single Vertical Eye-Line:** Maintain the visual flow:
  $$\text{Facecam (top)} \longrightarrow \text{Captions (upper-mid)} \longrightarrow \text{Gameplay Focus (lower)}$$

---

## 2. Zoom & Effect Restraint Rules (Killing the 16:9 Brainrot)

Uncontrolled digital zooming and micro-fidget cuts induce motion sickness and destroy spatial tracking. 

* **Max Zoom Scale:** **1.65x hard cap** on 9:16 sources; standard baseline is **1.0x**.
* **Zoom Frequency Limit:** **Maximum 1 to 2 zooms per 15–30 second clip.** Zooms are narrative punctuation marks, not fidget toys.
* **Earned vs. Spammed Zooms:**
  * **EARNED:** Slow, suspenseful linear push-in ($1.15\text{x} \to 1.25\text{x}$) during a channeled cast bar or countdown timer; or a hard punch-in ($\approx 1.6\text{x}$) held for $1.0\text{s} - 1.5\text{s}$ to land a punchline or joke reveal.
  * **SPAM (BANNED):** Continuous slow drift zooms, random scale-bumping during normal driving/movement, or seizure-inducing 0.5-second jump cuts.
* **Icon & Graphic Restraint:** 
  * The Metal Gear Solid `!` alert, red indicator arrows, and custom PNG cutouts must be tied strictly to major comedic ironies or catastrophic failures (e.g., a timer hitting zero right before an explosion). **Never repeat the same icon or gag twice in one video.**

---

## 3. SFX & Audio Restraint Rules

Content mills rely on wall-to-wall audio clutter; premium edits rely on pacing, silence, and organic reaction.

* **The 85%+ Raw Audio Rule:** At least 85% of the video's timeline must consist of pristine game engine audio and uncompressed creator microphone tracks.
* **Meme Soundboard Budget:** **Maximum 1 external meme sound bite or voice clip per 15-second clip** (e.g., *"It was at this moment that he knew..."*). 
* **Banned Audio Clutter:**
  * **No Bass-Drop Spam:** Sub-bass impact booms and ear-rape drops are banned unless tied to a major structural catastrophe, and must be normalized to `-6 dBFS` to prevent digital clipping.
  * **No Whoosh Overload:** Zero transition whooshes on routine cuts or caption pops.
  * **No Robotic AI TTS Narration:** Never use flat, emotionless AI voiceovers to explain what the creator is already saying or seeing. Let raw creator speech and natural in-game audio carry the narrative.
* **Audio Deadpan Pauses:** Cut background music and SFX to near-silence during deadpan text punchlines or unexpected pauses in creator speech.

---

## 4. The "AI Slop" Blacklist (Strictly Prohibited)

Any output exhibiting these traits fails QA instantly and must be rejected by the Gemini director:

1. **Floating Letterbox Slop:** Unprocessed 16:9 gameplay floating in the center of a 9:16 frame with solid black bars top and bottom.
2. **Deep-Fried Color Grading:** Aggressive contrast curves, crushed shadow blacks, and saturated skin tones that degrade video fidelity.
3. **Spoiler Ranking Overlays:** Clunky text titles like *"RANKING ISHOWSPEED FUNNIEST MOMENTS"* or *"Wait for the end 😂"* that spoil the punchline before it happens.
4. **Monotonous AI Voiceover:** Robotic, uninflected TTS reading bullet points or explaining simple gameplay hooks.
5. **Hyper-Saturated Listicle Formats:** Low-effort repetitive loops (e.g., *"What happens if you drop a grenade in front of cops in 5 different GTA games?"* with manic 0.5s cuts).
6. **Continuous Wall-to-Wall SFX:** Non-stop trap music loops competing with loud TTS and redundant explosion sounds with zero audio breathing room.

---

## 5. Exact Updated Directives for `analyze_gemini.py` & Remotion

Encode these concrete numerical limits directly into our pipeline logic:

### Gemini Video Prompt Directives (`analyze_gemini.py`):
* **Hook Rule:** Drop the viewer instantly into the action at frame zero ($00:00.000$). **Banned:** 8-second intro cards or static exposition hooks.
* **Punchline Protection:** Gemini must never suggest ranking overlays, spoiler captions, or predictive text prompts that ruin comedic timing.
* **Audio/Visual Intent:** When evaluating source clips, Gemini must score clips based on the presence of *organic creator reactions* and *natural narrative arcs*, penalizing clips padded with synthetic AI narration.

### Remotion Renderer Code Enforcement (`remotion/`):
```typescript
// Enforced Pipeline Constants
export const PIPELINE_LIMITS = {
  MAX_ZOOM_SCALE: 1.65,
  BASE_ZOOM_SCALE: 1.0,
  MAX_ZOOMS_PER_CLIP: 2,
  MAX_MEME_SOUNDS_PER_CLIP: 1,
  AUDIO_NORMALIZATION_DB: -6,
  LAYOUT_MODES: ['STACKED_FACECAM', 'FULL_VERTICAL_CROP'] as const,
};
```
* **Enforce Zero Black Bars:** Remotion templates must calculate layout dimensions dynamically. If `sourceWidth / sourceHeight !== 9/16`, apply the mirrored blurred edge padding background layer automatically.
* **Subtitle Safe-Zone:** Lock kinetic subtitle rendering layers strictly to the upper-middle dead zone ($y: 30\% \to 36\%$) so they never overlap facecams, progress cast bars, or bottom UI elements.