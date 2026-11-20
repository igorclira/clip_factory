# Master Editing & Curation Blueprint: `wow_forever` & `gta6`

---

## 1. The Hybrid Formula (CHM Craft × Red Arcade Selection)

The hybrid formula merges **Red Arcade’s viral kinetic curation** (high-velocity physics anomalies, near-misses, sub-second punchlines) with **Classic Hardcore Moments' (CHM) transformative editorial craft** (micro-zooms on UI/cooldowns, dramatic silence-drops, satirical meme overlays, and vocal/syllabic kinetic sync).

```
┌────────────────────────────────────────────────────────────────────────┐
│                          THE HYBRID TIMELINE                           │
│                                                                        │
│   0s - 3s              3s - 8s              8s - 12s        12s - 14s  │
│ ┌───────────────┐    ┌─────────────────┐    ┌─────────────┐ ┌────────┐ │
│ │ IN MEDIAS RES │ ──>│ SURGICAL EDIT   │ ──>│ CLIMAX /    │>│RUTHLESS│ │
│ │ HOOK          │    │ FOCUS           │    │ SILENCE-SLAM│ │OUTPOINT│ │
│ └───────────────┘    └─────────────────┘    └─────────────┘ └────────┘ │
│  • Action underway    • UI / Threat zoom     • Bass vacuum   • +12-24f │
│  • Subtitle pop       • Cooldown / NPC gag   • Physics ragdoll max     │
│  • Creator badge in   • SFX accent layer     • Punchline hit • Hard cut│
└────────────────────────────────────────────────────────────────────────┘
```

### Core Architecture Rules

#### Pacing Arc & Structural Retention Velocity
* **Rule 1: In Medias Res Hook (0.0s–3.0s).** Zero travel or setup time. GTA clips begin mid-flight, mid-spin, or with an RPG in flight. WoW clips begin with combat engaged, mob health bars already depleting, or an immediate ironic voice line (*"There are no rogues"*). If an asset requires >4s before primary interaction occurs, trim the front head directly to the trigger frame.
* **Rule 2: Surgical Contextual Interventions (3.0s–8.0s).** Insert editorial transforms: crop into an overlooked cooldown icon, snap-zoom to an aggressive mob/NPC, or split-screen a deadpan facecam.
* **Rule 3: Climax Execution & Silence-Slam (8.0s–12.0s).** Apply the **CHM Silence-to-Bass Drop**: 0.3s–0.5s prior to collision/death, hard-duck all audio to absolute digital silence (`-∞ dB`). On the exact frame of impact/death, trigger an explosive sub-bass hit, a 3-frame screen shake, and punch-zoom.
* **Rule 4: The Ruthless Out-Point (Exit Cut).** Cut 12 to 24 frames (0.4s–0.8s) after the punchline registers (ragdoll hit, death screen, or streamer laugh crest). Never let an asset linger into post-climax cooldown.

#### Formatting Adaptation: 9:16 Shorts vs. 16:9 Long-Form

| Feature | 9:16 Vertical Shorts (62s–70s Reel / Micro-Compilation) | 16:9 Long-Form Compilations (8–12 mins) |
| :--- | :--- | :--- |
| **Clip Slicing** | **4 to 6 clips chained per Short** (10–14s avg duration per sub-clip). Fast narrative velocity. | **15 to 35s per clip**. Allows longer tension buildup, full combat logs, or multi-phase raid wipes. |
| **Canvas Stacking** | **Dynamic 3-Tier Canvas**: Top tier = Facecam (scaled 140%), Middle tier = Primary Action Crop (dynamic pan/scan), Bottom tier = UI/Minimap/Action-bar crop or editorial subtitles. | **Standard 1920×1080 canvas**. Full UI preserved with digital snap-crops (150%–300%) to focus on cooldowns or unitframes. |
| **Transitions** | Fast 4-frame directional whip-pan blur + high-frequency whoosh SFX or instant hard-cuts on downbeats. | Hard cuts on audio downbeats; TV-static / CRT analog glitch bars (6–10 frames) every 8–10 clips to reset viewer fatigue. |
| **BGM Treatment** | Continuous high-energy, royalty-free phonk, trap, or vaporwave groove at `-22dB`, hard-sidechained/ducked during dialogue and fail beats. | Organic clip audio prioritized. Music only introduced for comedic juxtaposition (e.g., classical opera over slow-mo physics). |

---

## 2. Exact Visual Spec (Remotion React Components)

### Creator Credit Badge Components

#### A. GTA 6 Vaporwave Theme (`gta6_vaporwave`)
* **Remotion Container Geometry:** Pinned top-left corner (`top: 56px`, `left: 48px`). Two-tier horizontal flexbox.
* **Header Capsule:** Neon magenta (`#FF007F`) background, 4px rounded top edges. Typography: `Montserrat Black`, 14px, uppercase, tracking `0.15em`, pure white (`#FFFFFF`). Content: `EPISODE [X]` or `GTA 6 INTEL`.
* **Body Capsule:** Translucent smoked obsidian (`rgba(10, 10, 16, 0.85)`), 2px border matching neon cyan (`#00F0FF`). Height: 44px, border-radius: 0 8px 8px 8px, backdrop-filter: `blur(12px)`.
* **Icon:** Cyan game controller/crosshair SVG glyph (`20px x 20px`), margin-left: 12px.
* **Typography:** Streamer/Submitter handle in `Chalet London 1960` or `Bebas Neue`, 22px, solid white (`#FFFFFF`), drop-shadow: `0 0 8px rgba(0, 240, 255, 0.6)`.
* **Animation Lifecycle:**
  * **Frame 0–8:** Slide in from `translateX(-120%)` to `translateX(0)` using `spring({ damping: 14, mass: 0.8 })`.
  * **Frame 9–135 (4.5s at 30fps):** Static visibility.
  * **Frame 135–145:** Slide out to `translateX(-120%)` with opacity decay `1 -> 0`.

```tsx
// Remotion pseudo-implementation snippet: GTA6CreatorBadge.tsx
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

export const GTA6CreatorBadge = ({ username = "VICE_SNIPER" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const enter = spring({ frame, fps, config: { damping: 14, mass: 0.8 } });
  const exit = spring({ frame: Math.max(0, frame - 135), fps, config: { damping: 14 } });
  const translateX = (1 - enter) * -150 - exit * 150;

  return (
    <div style={{ position: "absolute", top: 56, left: 48, transform: `translateX(${translateX}px)`, zIndex: 100 }}>
      <div style={{ backgroundColor: "#FF007F", color: "#FFF", fontFamily: "Montserrat", fontWeight: 900, fontSize: 13, letterSpacing: "0.15em", padding: "3px 10px", width: "fit-content", borderRadius: "4px 4px 0 0" }}>
        GTA 6 FEED
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, backgroundColor: "rgba(10, 10, 16, 0.85)", border: "2px solid #00F0FF", padding: "6px 16px", borderRadius: "0 8px 8px 8px", backdropFilter: "blur(12px)" }}>
        <span style={{ color: "#00F0FF", fontSize: 18 }}>🎮</span>
        <span style={{ color: "#FFFFFF", fontFamily: "Impact, sans-serif", fontSize: 22, letterSpacing: "0.05em", textShadow: "0 0 8px rgba(0,240,255,0.6)" }}>
          {username.toUpperCase()}
        </span>
      </div>
    </div>
  );
};
```

#### B. WoW Classic Hardcore Theme (`wow_classic`)
* **Remotion Container Geometry:** Pinned top-center (`top: 36px`, `left: 50%`, `transform: translateX(-50%)`). Single integrated pill container.
* **Container Plate:** Charcoal-slate plate (`rgba(13, 14, 18, 0.90)`), 1.5px solid border-color `#C69B6D` (WoW Classic UI Gold), border-radius: 20px, padding: `6px 18px`, box-shadow: `0 4px 14px rgba(0,0,0,0.8)`.
* **Icon:** Twitch Purple squircle (`#9146FF`) with white glyph or Kick Green (`#53FC18`) squircle, size: 20px.
* **Typography:** `Inter Bold`, 18px, color: pure white (`#FFFFFF`), text-shadow: `1px 1px 2px #000000`. Left margin: 8px from platform icon.
* **Animation Lifecycle:**
  * **Frame 0–5:** Scale pop `scale(0.8) -> scale(1.05) -> scale(1.0)` with opacity fade `0 -> 1`.
  * **Duration:** Persists for the **entire duration** of the clip until the hard cut to eliminate visual flicker.

---

### Subtitle Specification

```
STREAMER SPOKEN           FUNNY NPC / DIALOGUE         EDITORIAL CALLOUT
┌────────────────────┐    ┌────────────────────┐    ┌────────────────────┐
│      "NO WAY"      │    │  "YOU FORGOT THIS" │    │  *petri cancelled* │
│    Solid White     │    │   Canary Yellow    │    │    Toxic Violet    │
│    6px Contour     │    │    6px Contour     │    │  Direct Placement  │
└────────────────────┘    └────────────────────┘    └────────────────────┘
```

* **Font Family & Weight:** `Montserrat Black`, `Futura ExtraBold`, or `The Bold Font` (condensed grotesque styling).
* **Stroke & Outline Execution:** Heavy solid outer outline (stroke-width: 6px–8px solid `#000000`), `paint-order: stroke fill`, `stroke-linejoin: round`. Zero soft blur on the stroke contour.
* **Shadow:** `box-shadow: none`. Text drop shadow: `3px 4px 0px #000000` (hard-edged arcade drop).
* **Color Hierarchy Engine:**
  * **Streamer Primary Speech:** Solid pure white (`#FFFFFF`).
  * **Funny NPC / Voice-Chat Panics / Stressed Syllables:** High-saturation canary yellow (`#FFEB3B`) or emergency crimson (`#FF2A2A`).
  * **Editorial Callouts / Meta-Irony:** Toxic violet (`#A855F7`) or mint green (`#22C55E`) in italics/lowercase (e.g., `*he had 5 health pots*`, `*instantly dazed*`).
* **Placement & Safe-Zones:**
  * Standard: Lower-third centered (`bottom: 18%` in 9:16 layout; `bottom: 12%` in 16:9 layout), clearance above default HUD elements.
  * Contextual tracking: Anchored over the moving target during aerial drops or physical fail points using Remotion dynamic coordinates.
* **Chunking & Velocity Rules:**
  * Maximum words per pop: **1 to 3 words**.
  * Syllabic pop spring: `scale(0.85) -> scale(1.15) -> scale(1.0)` over 3 frames.
  * **Anti-Lingering Cutoff Rule:** When the voice audio dips below `-35dB` on the waveform for more than 4 consecutive frames, the subtitle unmounts immediately. Zero persistent text on screen.

---

### Visual Shenanigans Toolkit (Remotion Catalog)

#### 1. Hard Snap-Zoom to Bounding Box (`SnapZoomBox`)
* **Parameters:** `targetX`, `targetY`, `targetScale` (default: 220% to 350%), `durationFrames` (1 frame snap or 3 frame spring).
* **Behavior:** Instant 1-frame camera punch-in to isolated coordinate (e.g., a Rogue stealth indicator, mob casting bar, or vehicle impact point).
* **Remotion Mechanism:** Apply CSS `transformOrigin: `${targetX}% ${targetY}%`` and `transform: scale(${scale})` instantly on trigger frame.

#### 2. Freeze-Frame + Monochrome + Vignette (`DespairFreeze`)
* **Parameters:** `triggerFrame`, `holdFrames` (typically 45–75 frames / 1.5s–2.5s).
* **Behavior:** Clip freezes on fatal frame. Saturation shifts to `grayscale(100%)`, contrast pushes to 130%, and a radial gradient vignette animates in (`radial-gradient(circle, transparent 40%, rgba(0,0,0,0.85) 100%)`).
* **Audio Coupling:** In-game audio ducks to `-∞ dB`; acoustic melancholy string or high-pitch tinnitus tone triggers.

#### 3. Quick Screen Shake (`ImpactShake`)
* **Parameters:** `intensity` (px deviation, default: 12px), `decayFrames` (6–9 frames).
* **Behavior:** Micro-rumble triggered frame-accurately on collision, sniper shot, or death hit.
* **Math:** Sine-wave dampening:
  ```ts
  const offset = Math.sin(frame * 2.5) * intensity * (1 - progress);
  ```

#### 4. Music Cut-to-Silence (`AudioVacuum`)
* **Parameters:** `leadInFrames` (default: 9–15 frames prior to climax).
* **Behavior:** Mutes the background music and ambient tracks to absolute zero. Isolates isolated audio stems (e.g., footstep, mob aggro cry, or streamer saying *"Watch this"*).

#### 5. Animated Callout Arrow & Circle (`TargetSpotlight`)
* **Parameters:** `x`, `y`, `radius`, `color` (default: `#FF1E1E`).
* **Behavior:** Vector circle draws itself around an unused inventory item, cooldown bar, or distant airborne projectile using Remotion `interpolate` on SVG `strokeDashoffset`, accompanied by a mechanical arrow bobbing 10px up/down.

#### 6. Slow-Mo Replay Ramp (`ImpactSlowMo`)
* **Parameters:** `entrySpeed` (1.0), `slowSpeed` (0.2 to 0.35), `durationFrames` (30–60 frames).
* **Behavior:** Post-impact replay showing physics flukes, multi-kills, or ragdoll trajectories with an automatic 20% saturation boost and micro-sub-bass rumble.

---

## 3. Exact SFX Shopping List (Epidemic Sound MCP)

Use these queries with Epidemic Sound MCP tool `SearchSoundEffects`. Each query maps to a specific editorial trigger:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      SFX TRIGGER ARCHITECTURE                          │
│                                                                        │
│   TRIGGER                   QUERY                     TIMING           │
│  ───────────────────────────────────────────────────────────────────   │
│   Target Locking       ──>  "camera autofocus beep"   (-10 frames)    │
│   Build / Launch       ──>  "cinematic sub riser"     (-15 to 0 frames)│
│   The Cut-to-Silence   ──>  [ALL MUTE / VACUUM]       (-8 to 0 frames) │
│   IMPACT / CLIMAX      ──>  "cinematic sub drop bass" (Frame 0)        │
│   Ragdoll / Hitmarker  ──>  "hitmarker metallic tick" (+1 frame)       │
│   Editorial Stupidity  ──>  "record scratch pause"    (+5 frames)      │
└────────────────────────────────────────────────────────────────────────┘
```

| # | Exact MCP Search Query | Target Filename / Asset Type | Contextual Trigger & Editorial Purpose |
| :--- | :--- | :--- | :--- |
| **1** | `cinematic sub drop bass heavy 808` | Sub Drop / Low Boom | Applied on fatal damage ticks, boss wipes, and vehicle collisions on Frame 0. |
| **2** | `short high speed whoosh transition` | Whip Swoosh | Tied frame-accurately to camera snap-zooms (150%–300%) and 4-frame scene cuts. |
| **3** | `record scratch pause stop` | Vinyl Scratch Stop | Deployed when hubris is interrupted (e.g., player boasts -> instantly stunned/ragdolled). |
| **4** | `hitmarker metallic click blip` | FPS Hit Accent | Synchronized with RPG snipes, one-shot crits, or mid-air vehicle projectile contacts. |
| **5** | `cartoon slide whistle down fall` | Descending Slide | Placed on characters falling off cliffs, failed parachutes, or airborne vehicle drops. |
| **6** | `metal pipe clatter echo impact` | Hollow Metal Impact | Comedic audio reinforcement when motorcycles hit obstacles or players ragdoll off hoods. |
| **7** | `cinematic tension heartbeat pulse riser` | Heartbeat Sub Pulse | Low-pass filtered background cue during stalking sequences, low-HP kiting, or escort runs. |
| **8** | `comedy spring boing jump` | Cartoon Mechanical Boing | Spliced over physics anomalies, players bouncing off terrain hitboxes, or trampoline car glitches. |
| **9** | `stealth whoosh blade reveal dark` | Dark Dagger Swoosh | Used when Rogue opens from stealth or enemy jet sneaks in from outside camera view. |
| **10** | `camera autofocus electronic beep short` | HUD Lock Target Beep | Paired with target spotlight circles, arrows, or HUD zoom-ins on enemy units. |
| **11** | `vintage bell boxing bell ring single` | Arcade Bell Ding | Emphasizes instant karma knockouts or punchline deliveries. |
| **12** | `retro 8-bit game death fall fail` | 8-Bit Game Over | Accent cue over the instant a hardcore character turns into a ghost. |
| **13** | `deep cinematic impact slam brass` | Inception-style Brass Hit | Drops on catastrophic raid mechanics (e.g., Naxxramas dance fail, instant 40-man wipe). |
| **14** | `tape stop rewind speed down` | Analog Motor Slowdown | Cut-to-silence transition right as a massive mechanical mistake is initiated. |
| **15** | `glitch digital data burst static short` | CRT Static Glitch Pop | Layered on TV static transition wipes between contrasting video styles. |
| **16** | `wooden door slam heavy latch click` | Heavy Dungeon Gate Latch | Triggered when players trap themselves inside geometry or cage mechanics. |
| **17** | `cinematic reverse cymbal swell fast` | 1-Second Reverse Swell | Pre-impact tension builder immediately before vehicular or projectile collision. |
| **18** | `funny squeak rubber toy compress` | Rubber Toy Squeak | Micro-accent deployed on minor head-bumps, failed jumps, or petty slapstick damage. |

---

## 4. GTA 6 & WoW Forever Clip Selection Rubric

### A. Concrete Pick Criteria (Winning Archetypes)

#### GTA 6 Winning Archetypes
* **The Stratospheric Parabolic Snipe:** Firing an unguided projectile or boosting a vehicle (Rocket/Scramjet mechanic) blindly into the sky and obliterating a high-velocity aircraft or micro-target on the horizon.
* **Millimeter Ragdoll Escapes:** Survival sequences where the player model clears lethal terrain, vehicle chassis, or helicopter blades by fractions of a meter without registering damage hitboxes.
* **Rogue Sandbox AI Interference:** Unscripted NPC mechanics interrupting cinematic mission paths (e.g., pedestrian delivery truck running over an antagonist mid-monologue; police cruiser pinballing into an active shootout).
* **The Accidental 500 IQ Trickshot:** Unintended geometric interactions—vehicles doing 720-degree flips off highway dividers and landing perfectly in tight alleys or mission triggers.

#### WoW Forever Winning Archetypes
* **Instant Ironic Hubris:** Explicit verbal confidence immediately refuted by game state (e.g., streamer stating *"This pull is completely safe"* 0.5s before pulling a wandering elite pack; mocking someone falling before slipping off the identical ledge).
* **Mechanical Self-Sabotage:** Players defeating themselves via game knowledge blunders (clicking an escort door shut, activating Cheetah in melee combat, canceling Feign Death instantly, or rolling Need on high-value BoEs accidentally).
* **The 1-Second Combat Roll Deletion:** High-level or fully raid-geared characters getting erased in <1.0s due to wild RNG combat spikes (Windfury procs, triple-crit thrash mechanics, boss parry-haste resets).
* **Frantic Comm Collapse (Raid Wipe Disasters):** High-stakes Hardcore voice-comms deteriorating into pure panic as health bars cascade down simultaneously (*"Petri out!"*).

---

### B. Concrete Auto-Reject Criteria (Instant Bin)

* **Setup Sloth (>4.0s Rule):** Any clip requiring more than 4 seconds of walking, running, driving, or buffing before the central conflict, stunt, or ironic dialogue begins.
* **Flatline Reaction / Low Audio Dynamism:** Clips where the player dies or completes an insane stunt without a verbal reaction, laughter, desk slam, or audible spike. Muffled, clipped, or low-bitrate USB microphones are rejected automatically.
* **Standard Gameplay Attrition:** Routine 1v1 PvP kills, typical dungeon boss takedowns, or standard vehicle drive-bys with no unexpected physics, RNG rolls, or comedic misplays.
* **Visual Pollution / Obstructed Canvas:** Clips with intrusive third-party channel watermarks, massive donation alert gifs covering the center screen, or lower-third webcam frames that obstruct the player's primary health frame or casting bar.
* **Anticlimactic Dissipation:** Stunts or pulls that build anticipation but resolve in a gradual reset, mob de-aggro, or slow health drain over 20+ seconds without a definite punchline cut.

---

### C. Automated Ingestion & Scout Rules

#### Upgraded `scout_queries.json` Payloads

```json
{
  "wow_forever_queries": [
    "WoW Classic Hardcore death clips twitch highlights",
    "WoW Hardcore instant karma deaths level 60",
    "Classic WoW griefing misplay clips 2024",
    "WoW Hardcore high level ninja loot reaction",
    "WoW Classic rare world drop reaction Kungen Sonii",
    "Naxxramas raid wipe Petri panic comms Hardcore"
  ],
  "gta6_queries": [
    "GTA 5 viral physics fails and wins Red Arcade style",
    "GTA Online 1 in a million stunts Scramjet",
    "GTA Online funny NPC karma moments clips",
    "GTA 5 impossible vehicle tricks and near misses",
    "GTA 6 leaked mechanics sandbox physics stunts",
    "GTA Online accidental jet snipes and stunt kills"
  ]
}
```

#### Gemini Multi-Modal Scoring Prompt Additions
Inject these technical scoring criteria into the multimodal ingestion pipeline:

```markdown
Evaluate the candidate video on a 1-100 scale using this strict editorial matrix:

1. HOOK VELOCITY (Weight: 25%):
   - Score 90-100: Primary action/ironic claim begins in 0.0s - 2.5s.
   - Score < 40: Requires > 5.0s of driving/walking to locate the subject. (AUTO-REJECT)

2. EDITORIAL LEVERAGE & MEME DENSITY (Weight: 30%):
   - Does the clip contain a clear focal point suitable for a 300% snap-zoom (e.g., an unclicked health potion, an overlooked mob, a flying rocket)?
   - Is there an ironic voice claim that directly contradicts the visual outcome?

3. AUDIO DYNAMICS (Weight: 25%):
   - Look for an abrupt audio dynamic shift (high vocal scream, sharp silence beat, or explosive spike).
   - If audio levels are flat, low-energy, or speech is absent during a fail, cap this score at 30.

4. PUNCHLINE DECISIVENESS (Weight: 20%):
   - Does the event end with an absolute resolution (ragdoll impact, death frame, loot popup)?
   - If the clip ends in a slow drag-out or prolonged disengagement, score 0.

OUTPUT FORMAT:
Return JSON with:
{
  "curation_score": number, // 0-100
  "verdict": "ACCEPT" | "REJECT", // ACCEPT if score >= 82
  "archetype": "IronicHubris" | "PhysicsAnomalies" | "SelfSabotage" | "ParabolicSnipe" | "RaidPanic",
  "in_point_timestamp": "00:00.000", // exact start frame of the hook
  "climax_timestamp": "00:00.000",   // exact frame for impact / silence drop
  "out_point_timestamp": "00:00.000",// cut-point 12-24 frames after punchline
  "zoom_target_coordinates": { "x": number, "y": number }, // normalized 0-100%
  "suggested_sfx_query": string // from blueprint library
}
```