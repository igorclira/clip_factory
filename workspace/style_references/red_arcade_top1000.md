### 1. Creator Credit Badge & Framing

* **Screen Placement:** Top-left corner ($x \approx 60\text{px}, y \approx 60\text{px}$ from 1080p safe zone).
* **Two-Tier Badge Architecture:**
  * **Top Tier (Episode Indicator):** A solid high-contrast crimson red rectangle (`#D31D24`) housing bold condensed white text: `📋 EPISODE [XXX]` (e.g., `EPISODE 108` at `00:00.000`, `EPISODE 42` at `00:31.500`, `EPISODE 160` at `00:59.000`).
  * **Bottom Tier (Submitter Handle):** A semi-transparent dark charcoal grey/black tab (`rgba(15, 15, 15, 0.85)`) placed flush directly beneath the red banner. Contains an orange/yellow game controller / user avatar icon on the left, followed by the submitter’s gamer tag in white, heavy all-caps font (e.g., `EPHEUS`, `MESHARY-RADY`, `FERNANDO_CNETO`, `THOMASOBISJS`).
* **Animation & Screen Time:** 
  * Slides in rapidly from the left edge via an ease-out curve (~8 frames / 0.25s).
  * Stays pinned on-screen for exactly **3.5 to 5.0 seconds** before smoothly sliding off-screen or fading out. If the entire clip is under 4 seconds, it remains pinned until the transition cut.
* **Branding Watermark:** Unobtrusive white semi-transparent `RED ARCADE` wordmark placed in the bottom-right corner during gameplay clips, toggling to fully branded title cards during segment breaks.

---

### 2. Subtitle & Typography Design

* **Font Style & Weight:** Heavy geometric grotesque sans-serif / display font (Impact / Futura Extra Bold / Montserrat Black), rendered strictly in **ALL-CAPS**.
* **Stroke & Shadow Specifications:**
  * **Fill:** High-saturation Canary Yellow (`#FFEB3B`) for comedic exclamations, punchlines, and voice chat; Pure White (`#FFFFFF`) for formal warnings, NPC dialogue, or narrative setup; Bold Red (`#FF1E1E`) for screams, crashes, and aggressive callouts.
  * **Outline (Stroke):** Heavy pure-black stroke (10–14px solid contour, zero bevel), guaranteeing readability against sun flares, tarmac, explosions, and night scenes.
  * **Drop Shadow:** Hard black drop shadow with 100% opacity, offset 4px downward at 90°, minimal blur radius.
* **Screen Placement & Motion:**
  * Centered in the middle or lower-third ($y \approx 70\%–80\%$). If the focal action occurs at the bottom, text moves directly above or adjacent to the character/vehicle.
  * **Animation:** Instant **scale pop** (105% $\rightarrow$ 98% $\rightarrow$ 100% across 3 frames) with zero motion blur.
* **Word Grouping & Selective Subtitling:**
  * **Chunking:** Strict 1–3 words per pop (e.g., `WHAT DOES` $\rightarrow$ `THIS` $\rightarrow$ `BUTTON` $\rightarrow$ `DO?` at `00:33.500–00:34.500`; `SHUT` $\rightarrow$ `UP` at `180:04.000–180:04.500`).
  * **Editorial Selection:** Ambient radio, casual in-game traffic chatter, and low-priority gameplay audio are **completely un-subtitled**. Only peak comedic beats, panic voice cracks, situational irony, or sudden NPC dialogue (e.g., `GET THAT VEHICLE OUTTA MY SHOP!` at `182:21.000`) receive text graphics.

---

### 3. Contextual Zooms, Pans, Freeze-Frames & Visual Shenanigans

| Timestamp | Visual Technique | Exact Focal Target | Speed / Curve | Comedic / Tension Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **00:02.500–00:03.500** | Camera whip-follow & tight crop | RPG rocket whizzing past player’s helmet | Hard snap, dynamic tracking | Highlights near-miss hitboxes; sudden shift from cocky stance to pure shock. |
| **00:15.500–00:17.500** | Speed ramp down to 20% slow-mo | Mid-air jet collision with cargo plane | Smooth linear deceleration | Accentuates GTA V's high-velocity shrapnel and explosion physics. |
| **00:36.500–00:38.500** | Low-angle dynamic track | Flying wheelchair falling off roof towards jeep | 40% slow-mo ramp | Stretches suspense before the inevitable face-plant impact on the car hood. |
| **01:03.500–01:06.500** | Instant B&W desaturation + Slow-mo replay | Pedestrian ragdoll knocked into second pedestrian | Instant punch-cut replay | Isolates a chaotic secondary chain reaction that would be missed in real-time. |
| **01:46.000–01:47.500** | Wide-angle symmetrical cut | Two rooftop snipers firing around identical air vents | Static locked-off frame | Visual irony: reveals both combatants are blindly firing away from each other. |
| **01:50.000–01:58.500** | Dynamic tracking zoom | Semi-truck performing an aerial backflip | Float slow-motion follow | Elevates an absurd physics glitch into a majestic, cinematic stunt. |
| **180:10.000–180:15.000** | Medium tracking pan | Two players brawling on motorcycle in highway lane | Real-time follow | Sets up incoming traffic wipeout; builds situational awareness for the viewer. |
| **181:03.500–181:06.000** | Snap zoom-in (140%) | Two armored thugs riding a tiny pastel Faggio scooter | Instant 1-frame punch | Visual comedy: huge armored avatars crammed onto a ridiculous moped. |
| **181:21.000–181:23.500** | Rotational center-lock zoom | Military buggy executing a clean 360° rail grind/flip | Follows vehicle rotation | Emphasizes accidental trick-shot perfection before landing. |
| **182:02.000–182:09.500** | Extreme telephoto digital zoom | Parachutist sniped out of the sky cartwheeling into dirt | Stepped digital punch-in | Keeps a tiny, distant ragdoll clearly legible against the desert horizon. |

---

### 4. SFX & Music Architecture

* **Key Recurring SFX Categories:**
  * **Whoosh / Whip-Pan Accents:** Low-friction air whooshes paired frame-accurately with every subtitle pop and camera punch.
  * **Meme / Vocal Stingers:** Spliced pop-culture quotes and movie samples (`"Oh my god"`, `"Do a flip"`, `"A perfect ten"`, `"No God please no"` at `181:44.000`).
  * **Acoustic Slapstick:** Cartoony hollow wood knocks, spring bounces, and subtle squeaks deployed when characters crash or ragdoll.
  * **Explosion & Impact Reinforcement:** Deep 30Hz sub-bass drops and metallic pipe clangs layered on top of in-game collisions.
* **The "Zoom + Silence + Punchline" Formula:**
  * When approaching a fail or absurd physics glitch, background music or ambient noise is **abruptly hard-cut to dead silence** (or muffled through an aggressive 200Hz low-pass filter).
  * A 1-frame snap zoom lands simultaneously with a dry voice line or visual gag (e.g., the deadpan scooter engine purr at `181:06.000`), followed immediately by an explosive impact SFX.
* **Musical Usage & Juxtaposition:**
  * **Ironic Orchestral / Choral Music:** Traditional classical or operatic choir tracks (e.g., *Ave Maria* style) play exclusively during majestic, slow-motion physics glitches (such as the truck flip at `01:53.000–01:58.000`), creating sharp comedic contrast against violent gameplay.
  * **Clean Cuts Between Clips:** Music rarely bleeds across clip boundaries unless it’s a thematic mini-montage. Each clip carries its own independent audio envelope.

---

### 5. Transition Techniques & Pacing Rhythm

* **Clip Duration:** Averages **6 to 14 seconds** per clip.
* **Pacing Arc (Hook to Exit):**
  * **0.0s–2.0s (Setup):** Immediate in-medias-res establishment—the vehicle is already mid-air, the gunfight is already underway, or the stunt run has just begun. No dead travel time.
  * **2.0s–8.0s (Development/Climax):** The unexpected event occurs (physics failure, third-party collision, catastrophic mistake).
  * **Exit Cut:** The cut occurs **within 10–20 frames (0.3s–0.7s)** after the punchline lands (e.g., cutting immediately as the "WASTED" screen flashes at `181:46.000` or right as the body hits the dirt at `182:10.500`). Holding any longer deflates the comedic energy.
* **Transition Styles:**
  * **Primary (Clip-to-Clip):** Hard, clean cuts with instantaneous audio swaps.
  * **Secondary (Scene/Segment Reset):** TV static / SMPTE color bar glitch overlays lasting 6–10 frames with an authentic CRT analog crackle (e.g., `181:00.000` and `181:39.500`).
  * **Branded Breakpoints:** 3D motion graphic title bumpers (`RED ARCADE PRESENTS` / `TOP 1000 GTA 5 FAILS` at `00:05.500` and `00:18.500`) used every 10–15 clips to reset viewer attention.

---

### 6. Curation & Clip Selection Criteria (GTA / Open World)

#### Winning Clip Archetypes:
1. **Instant Irony / Confident Hubris:** A player boasting, aiming down sights, or setting up a clean play only to be immediately obliterated by an off-screen factor (e.g., the gas station wipeout at `181:40.000`).
2. **One-in-a-Million Ragdoll & Vehicle Physics:** Impossible, accidental geometric interactions—trucks flipping 360° and landing upright, or motorcycles wedging between barriers.
3. **Absurd NPC/AI Interference:** GTA NPCs pulling erratic lane changes, delivering deadpan insults, or reacting with uncanny timing to player disasters.
4. **Symmetrical Stupidity:** Two opponents failing simultaneously or mirroring identical terrible decisions in PvP encounters (e.g., rooftop vent standoff at `01:46.000`).
5. **Anti-Climax Fails:** An elaborate, high-skill setup that fails at the final millisecond by the smallest possible margin (e.g., golf putt stopping on the rim at `01:32.000`).

#### Automatic Rejection Criteria (Why Submissions Get Cut):
* **Long Lead-Up Times:** Clips requiring more than 4 seconds of uneventful driving/running before the core action occurs.
* **Staged / Scripted Fails:** Clips that feel rehearsed or lack organic ragdoll unpredictability.
* **Unclear Visual Hierarchy:** Cluttered screens where the punchline occurs off-camera, far in the background, or obscured by heavy UI/mod menus without a readable focal point.
* **Low-Energy Audio:** Clips without distinct game audio, lacking authentic panic/laughter, or muffled by blown-out, un-leveled microphones.