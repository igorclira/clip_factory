### 1. 9:16 Vertical Framing & Layout (CRITICAL)

* **Layout Structure:**
  * **Top ~30–35%:** Streamer facecam in a crisp rectangular overlay, framed just below a clean, static header tag (`GTA 5 CHAOS MOD`). Flanked by subtly blurred, mirrored game background to prevent ugly black pillarboxing without visual clutter.
  * **Middle Dynamic Zone:** Active modifier indicator (`Vehicles Explode On Impact` / `Spawn Adder`) sitting directly underneath the facecam, ensuring viewers immediately grasp the gameplay stakes.
  * **Bottom ~65–70%:** Gameplay viewport cropped to 9:16 with the player’s car anchored in the lower-middle vertical center.
* **Visibility & Spatial Awareness:**
  * Crucial road geometry, incoming traffic, and obstacles remain 100% visible throughout turns and maneuvers. The crop never cuts off the player vehicle or the immediate driving trajectory.

---

### 2. Zoom Restraint & Scale

* **Measured Zoom Events:**
  1. **`00:05.500` – `00:07.500` (Narrative Punch-In ~2.0x):** 
     * **Target:** Hard punch-in directly onto the streamer’s facecam and the purple Chaos Mod timer bar.
     * **Visual Cue:** A solid red arrow draws viewer attention to the timer bar reaching 100%. 
     * **Narrative Purpose:** Punctuates the irony of the streamer saying *"I had all the time in the world"* right as the timer expires.
  2. **`00:08.000` (Instant Reset to 1.0x):**
     * Snaps instantly back to default framing on streamer dialogue (*"I don't really chat, this is a speedrun"*), establishing the baseline before the punchline.
  3. **`00:09.500` – `00:12.000` (Climactic Impact Punch ~1.25x + Slight Camera Shake):**
     * Punches in slightly onto the explosion when `Spawn Adder` detonates the vehicle. Accentuates the instant death without losing the wreckage or the streamer's reaction.
* **Pacing & Restraint:**
  * Exactly **two zooms** across a 12-second clip. Every zoom is strictly tied to a comedic narrative beat (setup $\rightarrow$ ironic indicator $\rightarrow$ catastrophe). No arbitrary breathing zooms, no spammed punch-ins.

---

### 3. SFX & Audio Restraint

* **SFX Breakdown:**
  * `00:00.000 – 00:05.500`: **Zero artificial sound effects.** Pure raw in-game engine audio layered cleanly under the streamer's live voice.
  * `00:06.000`: Minimal record-scratch / subtle comedic stop cue coinciding with the timer arrow punch-in.
  * `00:09.500`: Raw in-game vehicle explosion SFX, immediately followed by the streamer’s organic, uncompressed scream and laugh (*"AHAHAHA! You son of a—"*).
* **Audio Balance:**
  * **95%+ natural sound.** No AI narration, no stock meme soundboards (e.g., vine thuds, bruh SFX, cartoon whooshes), and no muddy bass drops. The entertainment value relies entirely on the streamer's comedic timing and the natural game mechanics.

---

### 4. Why This Matches `BEST_GTA_9X16_EXAMPLE`

#### Key Visual & Audio Choices That Make It Excel:
1. **Context-First Visual Hierarchy:** The viewer understands within 1 second what game is being played, who is playing it, and what rule is active (`Vehicles Explode On Impact`).
2. **Irony-Driven Visual Gag:** The red arrow + zoom onto the timer bar at `00:06.000` turns game UI into comedic foreshadowing, paying off 3 seconds later when the timer hits zero and spawns the deadly vehicle.
3. **Dialogue & Action Synchronization:** The edit lets the creator's cocky line (*"this is a speedrun"*) deliver completely unhindered before the sudden detonation cuts him off.

#### Concrete DO / DO NOT Rules for Remotion & Gemini

* **DO:**
  * **Anchor player vehicles in the lower 40–50% of the canvas** during driving clips to maintain peripheral road context.
  * **Reserve punch-in zooms strictly for narrative setups or punchlines** (e.g., UI countdown expiration, sudden impact).
  * **Let natural creator speech and in-game SFX carry the audio track.** Mute or omit generic stock meme soundboards unless an explicit meta gag requires it.
  * **Use clean, two-word-burst animated subtitles** centered near the car/face boundary without obscuring primary action.

* **DO NOT:**
  * **DO NOT apply continuous random scale-bumping / drift zooms** during normal driving; it induces motion sickness and destroys spatial awareness.
  * **DO NOT slap heavy bass drops or whooshes over real game explosions.** The in-game audio and creator reaction already peak naturally.
  * **DO NOT crop out game UI elements that explain the clip’s premise** (e.g., Chaos mod notifications, timers, mission titles). Move them into the vertical stack if needed.