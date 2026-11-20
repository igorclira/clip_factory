### 1. 9:16 Vertical Framing & Layout (Forensic Analysis)

* **Adaptation Method (Top Facecam + Centered Game Focus):**
  * **Facecam Docking:** A floating 16:9 rectangular facecam box with a clean, subtle light border is anchored at upper-center ($y \approx 10\% - 27\%$). This sits safely below platform UI overlays (profile badges/title bars) without intruding into the central action.
  * **Gameplay Canvas:** The game is cropped vertically to prioritize the primary point of interest (the in-game TV screen and the player character). At wide framing, the full TV console and player are centered. In transition cuts (e.g., 00:07.5–00:09.5), blurred edge wings (subtle horizontal blur of the source footage) pad the side borders naturally without distracting black voids.
  * **Subtitle Placement ($y \approx 20\% - 25\%$):** Dynamic subtitles appear directly below the facecam and directly above the in-game TV. This creates an effortless **single vertical eye-line**:
    $$\text{Facecam (top)} \longrightarrow \text{Captions (upper-mid)} \longrightarrow \text{In-game TV (center)}$$
    The viewer never has to scan horizontally or dart across corners.
* **Game Visibility:** $\sim 70\%$ of the vertical real estate is reserved for gameplay. The TV set and player avatar are 100% visible throughout the entire premise setup.

---

### 2. Zoom Restraint & Scale

| Timestamp | Camera/Zoom State | Scale Factor | Focus Target | Purpose & Execution |
| :--- | :--- | :--- | :--- | :--- |
| **00:00.0 – 00:05.0** | Static Wide | 1.0x (base crop) | Living room + TV | Establishes the scene, character stance, and streamer reaction. |
| **00:05.5 – 00:06.8** | Hard Punch Zoom | $\approx 1.65\text{x}$ | In-Game TV Screen | **The Punchline:** Instant cut punch-in directly onto the cartoon face when the joke lands ("They are p\*\*ises"). Holds for 1.3 seconds. |
| **00:07.0 – 00:09.5** | Snap Return | 1.0x (base crop) | Player walking away | Snaps back cleanly as the streamer reacts ("Oh. Okay, I'm gonna go now") and walks the character out of the room. |

* **Restraint Score:** **10/10.** In a 9-second Short, there is exactly **one zoom**. It is strictly earned by the comedic reveal.
* **Streamer Integrity:** The streamer facecam remains rigidly anchored at the top throughout the TV punch zoom, ensuring zero visual disorientation.

---

### 3. SFX & Audio Restraint

* **SFX Audit:** **Zero added artificial SFX.**
  * *00:00.0 – 00:09.5:* No whooshes, no vine booms, no impact hits, no sub-bass drops, no risers, and no meme soundboard clips.
* **Audio Layering:**
  1. **Primary Track:** Streamer microphone (crisp, dry, completely natural reaction).
  2. **Secondary Track:** In-game TV cartoon audio and ambient room audio.
* **Why This Works:**
  Manufactured hype (e.g., bass drops on every caption word) ruins situational comedy. Leaving the raw dialogue and ambient audio untouched allows the organic timing of the game's absurdity and the streamer's deadpan reaction to carry the humor.

---

### 4. Why This Matches `BEST_GTA_9X16_EXAMPLE` & Production Rules

#### Why It Succeeds:
1. **Vertical Flow Architecture:** Stacking `[Facecam] -> [Text] -> [Subject]` creates zero viewer fatigue.
2. **Earned Narrative Punch-In:** Zooming is treated as a narrative punctuation mark, not an ADHD visual fidget toy.
3. **Audio Dignity:** Clean game audio + clean creator commentary without AI narration or generic library SFX.

#### Strict Rules for Remotion / Gemini Pipeline:

* **DO:**
  * Anchor facecam at upper-center ($y \approx 10\% - 28\%$) with a subtle outline border.
  * Place kinetic captions in the dead zone between facecam and the gameplay focal point ($y \approx 28\% - 36\%$).
  * Reserve punch zooms ($\approx 1.5\text{x} - 1.8\text{x}$) exclusively for high-salience moments (punchlines, headshots, jump scares), holding for $1.0\text{s} - 1.5\text{s}$ before returning to base framing.
  * Keep the streamer cam anchored/static during gameplay punch zooms to prevent viewer motion sickness.

* **DO NOT:**
  * **DO NOT** insert whoosh sound effects on text pop-ups or camera reframes.
  * **DO NOT** use AI TTS voiceovers to explain what the creator is already seeing or saying.
  * **DO NOT** oscillate or continuously slow-push the camera without a distinct narrative reason.
  * **DO NOT** place facecam at the bottom or corners where platform UI (like/share buttons, sound discs, captions) obscures the streamer.