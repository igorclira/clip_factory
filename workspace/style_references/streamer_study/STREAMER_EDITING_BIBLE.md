# The Streamer Montage Editing & Comedic Timing Bible
*Defines automated rendering standards for `clip_factory`, `gta6_clips`, and `wow_forever_clips` via Remotion + Gemini + Epidemic Sound.*

---

## 1. Executive Summary: What Separates Viral 9/10 Edits from Slop

Based on our multimodal study of top-tier YouTube Shorts and TikTok streamer edits (e.g., *ibohclips*, *SpeedKaiClip*, *TheRussianBadger*), viral success on vertical feeds requires **relentless narrative pacing, spatial legibility, and subverted expectations**. 

### YouTube Shorts vs. TikTok Craft Divergence
* **YouTube Shorts (High Production Value & Narrative Arch):** Top Shorts lean into high-production multi-clip montages, narrative progression (e.g., escalating ranks or multi-year continuity like *yt_5Vh5SU2XL8c*), and sophisticated split-screen layouts. They reward rewatchability via visual callbacks and precise needle-drops.
* **TikTok (Immediate Hook & Raw Relatability):** TikTok winners rely on instant facecam engagement, tight framing, and deadpan meta-commentary. They use immediate audio/visual text hooks in the first 0.8 seconds and cut dead air aggressively.

### The 4 Pillars of a Viral Remotion Render
1. **Zero Dead Air:** If a streamer isn't speaking, reacting, or driving physical action, cut the frames or inject a motion tag (`*PANICKS*`, `*SEARCHES*`, `*EARTHQUAKE*`).
2. **Kinetic Typography as a Character:** Captions are never static blocks; they are dynamic, color-coded, word-level UI elements that react to vocal velocity.
3. **Hybrid Framing Choreography:** Never leave a 16:9 Twitch clip un-reframed with black bars. Use either a **50/50 Facecam/Gameplay Split Stack** or a **Contextual Focus Crop** with micro-zooms.
4. **Punctuated Sound Design:** Raw streamer audio is boosted to 85%+, underpinned by clean audio ducking, tactical whooshes, and precise comedy/impact stingers.

---

## 2. The Streamer Subtitle System (Exact Spec)

Top-tier captions use a **dual-track system**: continuous 1-3 word kinetic speech chunks combined with bracketed editorial popups.

### Exact JSON & Component Spec
Every caption item emitted by Gemini (`analyze_gemini.py`) and rendered by Remotion must follow this schema:

```json
{
  "start": 1.24,
  "end": 1.85,
  "text": "BRO REALLY",
  "speaker": "speaker_a",
  "is_editorial": false,
  "emphasis": true
}
```

### Typography & Color Coding Rules
* **Speaker A (Main Streamer / Protagonist):** Bold sans-serif (e.g., Montserrat / Impact hybrid), **Pure White** fill (`#FFFFFF`), heavy black stroke (`#000000`, width: 6-8px), drop shadow (`rgba(0,0,0,0.8)`).
* **Speaker B (Guest / Co-op Partner):** High-contrast **Bright Yellow** (`#FFE600`) to visually separate conversational ping-pong without needing split-screen labels.
* **Funny NPC / Game Dialogue:** **Cyan / Electric Blue** (`#00F0FF`).
* **Deadpan Editorial Popups / Meta-Cues:** Italicized in brackets with a semi-transparent dark pill background (e.g., *`*PAINFUL REGRET*`*, *`*EARTHQUAKE*`*, *`*CRAFTS*`*). Colored in **Hot Pink/Magenta** (`#FF0055`) or **Warning Orange** (`#FF6B00`).

### Kinetic Animation Rules
* **Chunking:** Max 1 to 3 words per frame sequence. Never display a full sentence.
* **Scale-Pop:** On emphasized syllables or screaming peaks (detected via audio amplitude spikes), scale the text container from `0.85` to `1.15` using a spring physics damping curve (`spring({ damping: 12, mass: 0.5 })`).
* **Zero Lingering:** Subtitles must cut out *the exact millisecond* audio finishes. Lingering text destroys comedic timing.

---

## 3. 9:16 Framing, Facecam Choreography & Smart Crop Rules

Never render raw unedited horizontal video. Handle sources dynamically:

### Layout Archetypes
1. **The 50/50 Split Stack (Best for Facecam + Heavy Gameplay/Crafting like *yt_f7bSQFq5PNo*):**
   * **Top Half (40-45% height):** Streamer facecam cropped tight to head/shoulders, placed over a blurred, scaled-up backdrop of the source video for aesthetic letterboxing.
   * **Bottom Half (55-60% height):** Gameplay HUD, inventory, or action feed locked to absolute 9:16 vertical center.
2. **Native 9:16 Broadcast / IRL Crop:**
   * Center-weighted tracking that pans dynamically to follow physical subjects (wrestlers, acrobats, running streamers) with smooth interpolation.
3. **Badly Letterboxed 16:9 Clips:**
   * Crop away black letterboxes entirely. Force-scale width to 1080px and apply a slow 1.0x to 1.1x pan across active focal points.

### Contextual Zoom Rules
* **Trigger:** Zoom in on facecam during sudden realizations, screams, or micro-expressions. Zoom in on gameplay action (e.g., a crafting grid or a missed jump) during periods of deadpan silence.
* **Scale Range:** Restrict automated zooms between **1.1x and 1.4x max**. 
* **Anti-Pattern Warning:** *Over-zooming beyond 1.5x on low-bitrate clips destroys pixel resolution and induces motion sickness.* Keep zooms stable; never shake the camera unless paired with an explicit physical impact (e.g., CaseOh desk slam = seismic screen shake).

---

## 4. Comedic Timing, Setup-to-Payoff Arcs & Never Cutting on a Cliffhanger

Comedy lives and dies in the milliseconds after a punchline.

### The 3-Beat Comedic Rhythm
1. **The Setup (0% - 40% duration):** Establish context quickly (e.g., item crafting, riddle reading, walking into a trap). Trim all dead air preceding the dialogue.
2. **The Climax / Impact (40% - 75%):** The sudden shift, jump scare, explosion, or insult. 
   * *Hard-Cut Rule:* For physical slaps, WWE takedowns, or sudden screams, cut *instantly* on the frame of impact ("perfectly cut screams").
3. **The Reaction & Consequence Hold (75% - 100%):** **Never cut immediately on the punchline.** Hold the frame on the streamer's blank stare, heavy breathing, or awkward silence for **1.5 to 3.0 seconds** so the joke actually registers with the viewer. This pause is what triggers viral loops and replay value.

---

## 5. Music Swaps & Studio SFX Playbook (Epidemic Sound Strategy)

### Audio Swap Scenarios
* **Awkward / Dead Room Audio:** If a raw clip features muddy microphone hum or dead air during a mundane task, mute original speech background and inject an ironic, upbeat track (e.g., quirky jazz, frantic phonk, or classic sitcom elevator music).
* **Needle-Drop Entrances:** Sync high-energy entrances (like *yt_8ipYkWfJBTE*) to recognizable beat drops or hip-hop intros exactly on the frame the door opens or the character enters.

### Expanded SFX Arsenal (`shared_assets/sfx/`)
Add these specific stingers to our automated asset library:
1. `sfx_cartoon_spring.mp3` (Bouncy stretch/recoil for comedic realizations)
2. `sfx_vinyl_scratch.mp3` (Immediate screech halt for sudden interruptions)
3. `sfx_superhero_landing.mp3` (Cinematic sub-bass boom for heavy impacts or dramatic character entries)
4. `sfx_bone_crunch.mp3` (Crisp cartoon/foley snap for physical fails)
5. `sfx_one_eternity_later.mp3` (SpongeBob transition chime for long thinking pauses)
6. `sfx_gta_mission_passed.mp3` (Nostalgic fanfare for successful stunt/quest completions)
7. `sfx_discord_join.mp3` or `sfx_notification.mp3` (Subtle meta-interruption)
8. `sfx_cartoon_slip.mp3` (Whistle-down slide for unexpected falls)

### Audio Balance & Restraint Rules
* **The 85%+ Raw Audio Rule:** Raw streamer dialogue, screams, and game sounds must sit at **85% to 100% volume**. Background music must be ducked aggressively to **-18dB to -24dB** whenever anyone speaks.
* **Bass-Drop Fatigue Prevention:** Limit heavy cinematic bass drops to true climax moments (e.g., desk slams, explosions). Do not trigger heavy bass on every transition, or it loses all comedic impact.

---

## 6. Concrete Code Upgrades for `analyze_gemini.py` and `remotion_studio/`

Implement these exact upgrades in code to ensure every automated render hits masterpiece tier.

### A. Upgrades to `analyze_gemini.py` (JSON Output Schema)
Update the Gemini prompt and JSON parser to output structured cinematic markers alongside transcripts:

```json
{
  "clip_metadata": {
    "archetype": "Fast Multi-Clip Montage",
    "primary_subject": "CaseOh Minecraft Crafting Fail",
    "target_pacing": "rapid_escalation"
  },
  "segments": [
    {
      "start": 0.0,
      "end": 3.4,
      "layout": "split_screen_50_50",
      "zoom_target": "crafting_grid",
      "zoom_scale": 1.25,
      "speaker": "CaseOh",
      "dialogue": [
        {"start": 0.0, "end": 0.8, "text": "WHERE", "emphasis": true},
        {"start": 0.8, "end": 1.5, "text": "IS THE", "emphasis": false},
        {"start": 1.5, "end": 3.4, "text": "NETHERITE?!", "emphasis": true}
      ],
      "editorial_popup": "*PANICKS*",
      "sfx_trigger": "sfx_vinyl_scratch.mp3",
      "hold_post_action_seconds": 2.1
    }
  ]
}
```

### B. Whisper Auto-Builder Logic (`whisper_to_remotion.py`)
Ensure our transcription processing pipeline auto-segments long sentences into kinetic chunks:
* Max word count per chunk: **3 words**.
* Force a chunk break on any audio pause > **0.25 seconds**.
* Automatically inject editorial action tags (`*PANICKS*`, `*SEARCHES*`, `*LOSES IT*`) if Gemini detects a silent gameplay sequence lasting longer than 2.0 seconds.

### C. Remotion Component Upgrades (`remotion_studio/`)
Build or update the core composition renderer (`StreamerClip.tsx`) with these features:

1. **Kinetic Text Component (`AnimatedCaption.tsx`):**
   * Uses Remotion's `spring()` to animate text scale from `0.8` to `1.0` on mount.
   * Applies conditional text coloring based on `speaker` property (`#FFFFFF` for primary, `#FFE600` for secondary, `#FF0055` for editorial brackets).

2. **Dynamic Split-Screen Layout Component (`SplitScreenStack.tsx`):**
   * Automatically calculates vertical split coordinates: Top 42% for facecam with background blur effect (`backdropFilter: blur(10px)`), Bottom 55% for cropped gameplay.

3. **Inertial Zoom & Shake Engine (`CameraEngine.tsx`):**
   * Applies CSS `transform: scale()` interpolations driven by segment metadata.
   * If `screen_shake: true` is flagged, injects procedural sinusoidal translation offsets (`Math.sin(frame * 2) * intensity`) synchronized exactly to audio impact timestamps.