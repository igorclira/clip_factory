export type PlatformType = 'tiktok' | 'youtube' | 'twitch' | 'reddit';
export type ThemeType = 'gta6_vaporwave' | 'wow_classic';
export type SpeakerRole = 'streamer' | 'npc' | 'editorial';

export interface ZoomCue {
  atSec: number;             // relative second inside this trimmed segment
  durationSec?: number;      // default 1.0s
  scale?: number;            // e.g. 1.95 for aggressive_punch, 1.55 for slow_creep/snap_hold
  originX: number;           // 0..100 (% horizontal subject coordinate)
  originY: number;           // 0..100 (% vertical subject coordinate)
  mode?: 'aggressive_punch' | 'slow_creep' | 'snap_hold' | 'snap' | 'smooth';
  target?: 'full' | 'game' | 'facecam'; // isolate zoom to gameplay or facecam when splitY is set
}

export interface ShakeCue {
  atSec: number;             // relative second inside trimmed segment
  intensity?: number;        // px deviation, default 14
  durationFrames?: number;   // default 8 frames
}

export interface SilenceCue {
  startSec: number;          // CHM AudioVacuum start (e.g. 0.35s before impact)
  endSec: number;            // AudioVacuum end (exact impact frame)
}

export interface FreezeCue {
  atSec: number;             // relative second to trigger monochrome despair freeze
  durationSec?: number;      // default 1.5s
  monochrome?: boolean;      // default true
}

export interface SpotlightCue {
  atSec: number;
  durationSec?: number;      // default 1.1s
  x: number;                 // 0..100%
  y: number;                 // 0..100%
  radius?: number;           // px for circle, default 75
  kind: 'circle' | 'alert';  // 'circle' = animated SVG ring; 'alert' = Metal Gear '!' icon
  color?: string;            // default '#FF1E1E' for circle, '#FFE600' for alert
}

export interface SfxCue {
  atSec: number;             // relative second inside this trimmed segment
  file: string;              // relative filename inside public/sfx/
  volume?: number;           // 0..1.5, default 0.9
}

export interface CaptionWord {
  text: string;
  startSec: number;
  endSec: number;
}

export interface CaptionCue {
  startSec: number;          // relative second inside this trimmed segment
  endSec: number;            // tight anti-lingering end second
  text: string;              // 1-3 punchy words preferred
  role: SpeakerRole;
  words?: CaptionWord[];     // word-level timestamps for karaoke highlighting
  x?: number;                // optional contextual X% (Red Arcade style)
  y?: number;                // optional contextual Y%
  rotateDeg?: number;        // optional slight tilt (-10..10 deg)
}

export interface LetterboxCrop {
  yPct: number;              // vertical start fraction (0..1) of gameplay region
  hPct: number;              // vertical height fraction (0..1) of gameplay region
}

export interface CtaConfig {
  variant: 'mid' | 'outro' | 'sponsor';
  headline: string;
  subline: string;
  badges?: string[];
  sponsorText?: string;
}

export interface SegmentProps {
  id: string;
  kind?: 'clip' | 'cta';
  cta?: CtaConfig;
  splitY?: number;           // horizontal seam % (0..100) separating top streamer facecam from bottom gameplay
  videoFile?: string;        // relative filename inside public/clips/
  platform?: PlatformType;
  author?: string;
  startSec: number;
  endSec: number;
  playbackRate?: number;     // e.g. 0.62 for dramatic slow-motion (pre-baked in render_remotion.py)
  letterboxCrop?: LetterboxCrop; // crop out top/bottom bars & bake over blurred 9:16 backdrop
  streamerCaptionY?: number; // top % override for streamer captions near mouth (default 27)
  cropZoom?: number;         // extra base scale (>1.0) to eliminate baked-in black bars
  cropOffsetY?: number;      // % vertical shift if needed
  videoVolume?: number;      // 0..1
  isolateVocals?: boolean;   // if true, render_remotion.py isolates speech band so voice stays audible over bgmFile
  transitionIn?: 'slide' | 'wipe' | 'fade' | 'none'; // clip-to-clip transition style (default 'slide' for new creators)
  bgmFile?: string;          // optional per-clip BGM swap inside public/sfx/ (e.g. upbeat track over muted weird audio)
  bgmVolume?: number;        // default 0.35 (or 0.65 if videoVolume is 0)
  zooms?: ZoomCue[];
  shakes?: ShakeCue[];
  silences?: SilenceCue[];
  freezes?: FreezeCue[];
  spotlights?: SpotlightCue[];
  sfx?: SfxCue[];
  captions?: CaptionCue[];
}

export interface SoundCutPoint {
  start_s: number;
  end_s: number;
}

export interface SoundPlanMusic {
  file: string;
  start_s?: number;
  gain_db: number;
  duck_under_game_audio_db: number;
  cut_points?: SoundCutPoint[];
}

export interface SoundPlanEvent {
  t: number;
  play_at_s?: number;
  trim_start_s?: number;
  max_duration_s?: number;
  file: string;
  sound_id?: string;
  category: string;
  placement?: string;
  trigger?: string;
  copyright_risk?: string;
  gain_db: number;
  reason?: string;
}

export interface GameDuckWindow {
  start_s: number;
  end_s: number;
  db?: number;
}

export interface SoundPlanFinalMix {
  target_lufs: number;
  true_peak_db: number;
}

export interface SoundPlanProps {
  montage_mode?: 'funny' | 'action' | 'hybrid';
  music: SoundPlanMusic;
  events: SoundPlanEvent[];
  game_duck_windows?: GameDuckWindow[];
  final_mix?: SoundPlanFinalMix;
}

export type MontageProps = {
  channelId: string;
  theme: ThemeType;
  montageMode?: 'funny' | 'action' | 'hybrid';
  fps: number;
  segments: SegmentProps[];
  soundPlan?: SoundPlanProps;
};
