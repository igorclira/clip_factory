### 1. 9:16 Vertical Framing & Layout (Forensic Analysis)

* **Framing Structure:** Direct vertical center-crop of the 16:9 game viewport. No blurred background bars, no letterboxing, and no split-screen facecam.
* **UI Retention & Readability:**
  * **Action Bars:** Bottom HUD bar remains anchored cleanly along the bottom edge, maintaining the authentic WoW Classic interface aesthetic.
  * **Cast Bar Placement:** The crucial cast bars (`Opening`, `Interrupted`) sit directly below the character model in the vertical center-lower third, unobstructed by captions.
  * **Smart UI Overlay (00:44.5):** When the chest opens, the editor highlights the loot window (`Items: Arena Master`, `Greater Mana Potion`, etc.) and the chat log in an enlarged overlay layout on the left/top flank, immediately proving the rogue secured the prized Arena Master trinket before resetting to wide chase framing.
* **Player Visibility:** Third-person camera tracking naturally keeps the player avatar ("Dubshoot") centered. Viewers maintain complete awareness of spatial orientation, arena boundaries, and the positioning of the threatening priest.

---

### 2. Zoom Restraint & Scale

* **00:00 – 00:28.0 (1.0x Baseline):** Full 1.0x vertical crop. Zero jitter, camera shake, or artificial panning while setting up the encounter and running from the attacker.
* **00:28.5 – 00:30.0 (Comedic Punch-In ~1.6x – 1.8x):** Hard cut to an isolated crop of the rogue’s deadpan chat bubble: `"k"`. The zoom lasts 1.5 seconds purely to land the comedic beat of feigned submission.
* **00:37.0 – 00:44.5 (Suspense Push-In ~1.15x – 1.25x):** As the rogue begins channeling the chest, the camera executes a continuous, slow linear push-in centered on the rogue and the `Opening` progress bar. This builds micro-tension as the cast bar fills.
* **00:46.5 – 00:53.0 (Snap to 1.0x Baseline):** Immediately snaps back to 1.0x wide framing for the sprint escape up the ramp, providing full visibility of potential pursuers.
* **Cadence Assessment:** Zooms are strictly **earned narrative punctuation** (the agreement punchline, the cast-bar tension, the loot reveal). Zero spammed micro-zooms.

---

### 3. SFX & Audio Restraint

* **Audio Events Timeline:**
  * `00:00.0 – 00:02.0`: Raw player voice comms (*"Alright, let's just go for it, fk it"*).
  * `00:07.5 – 00:08.5`: Raw combat hit & interrupt sound effect with natural game audio.
  * `00:18.0 – 00:19.0`: Dubbed comedic voice line (*"Spare me!"*) timed to the in-game emote text.
  * `00:28.0 – 00:30.0`: Complete silence/ambient arena wind when Dubshoot types `"k"` — deadpan comedic pause.
  * `00:37.5 – 00:45.5`: Iconic meme voice clip (*"In the end, I still managed to stay two steps ahead... of everyone"*) over a low, swelling cinematic synth drone. Perfectly synchronized so the final phrase lands exactly as the chest opens.
  * `00:47.5 – 00:49.0`: Panic voice clip (*"Oh, shit"*) as Dubshoot grabs the loot and runs for his life.
* **Restraint Factor:** No Vine booms, no screeching whooshes, and no robotic TikTok TTS narration. The raw footstep and cast audio carry the middle portion, giving the meme audio maximum comedic impact.

---

### 4. Concrete Rules for Remotion & Gemini Pipeline

#### **DO:**
1. **Preserve Cast/Progress Bars:** When gameplay involves channeled casts, interactions, or defuses, never allow captions or UI overlays to obscure the center-lower cast progress bar.
2. **Use Audio Deadpan Pauses:** Cut background music/SFX to near-silence during deadpan text punchlines (e.g., typing `"k"` to an enemy threat).
3. **Execute Slow Suspense Push-Ins on Timed Actions:** Use a subtle `1.15x` to `1.25x` gradual scale-in exclusively during tense, high-stakes progress bars to amplify viewer engagement.
4. **Reposition Key Evidence Pop-Ups:** When high-value loot or kill notifications appear at the edge of the 16:9 source, crop and overlay that specific UI box into the 9:16 frame for 1–2 seconds so mobile viewers see the payoff.

#### **DO NOT:**
1. **DO NOT Spam Transition Whooshes:** Avoid whoosh/impact SFX on routine cuts or camera angle adjustments.
2. **DO NOT Obscure Movement During Escapes:** Never zoom in closely while a character is fleeing or kiting; wide field-of-view (1.0x baseline) is mandatory for chase clarity.
3. **DO NOT Over-Subtitle Gameplay Chat:** Chat bubbles already rendered by the game engine in the center of the screen do not need oversized animated karaoke captions stacked directly on top of them.