import React from 'react';
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { slide } from '@remotion/transitions/slide';
import { wipe } from '@remotion/transitions/wipe';
import { CreatorCredit } from './components/CreatorCredit';
import { SmartCaptions } from './components/SmartCaptions';
import { DespairOverlay, TargetSpotlights } from './components/VisualShenanigans';
import { MontageProps, SegmentProps, ThemeType } from './types';

export const TRANSITION_FRAMES = 8;

const dbToLinear = (db: number): number => Math.min(1.5, Math.max(0, Math.pow(10, db / 20)));

// Hard-enforced 9:16 Vertical Editing Constitution + 34-Video Streamer Bible limits
const PIPELINE_LIMITS = {
  MAX_ZOOM_SCALE: 2.05,
  MAX_SMOOTH_ZOOM_SCALE: 1.42,
  MAX_CREEP_ZOOM_SCALE: 1.70,
  MAX_SNAP_ZOOM_SCALE: 1.75,
  MAX_CROP_ZOOM: 1.78,
  MAX_ZOOMS_PER_CLIP: 2,
  MAX_SFX_PER_CLIP: 2,
};

const SegmentView: React.FC<{ seg: SegmentProps; theme: ThemeType; isFirst: boolean }> = ({
  seg,
  theme,
  isFirst,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const nowSec = frame / fps;

  // 1. Situation-specific 9:16 Camera Choreography (aggressive_punch / slow_creep / snap_hold / smooth)
  const baseCrop = Math.min(Math.max(1.0, seg.cropZoom ?? 1.0), PIPELINE_LIMITS.MAX_CROP_ZOOM);
  let zoomScale = baseCrop;
  let originX = 50;
  let originY = 50;

  for (const z of (seg.zooms || []).slice(0, PIPELINE_LIMITS.MAX_ZOOMS_PER_CLIP)) {
    const dur = Math.max(0.2, z.durationSec ?? 1.0);
    const zStart = z.atSec;
    const zEnd = zStart + dur;
    const mode = z.mode ?? 'smooth';
    if (nowSec >= zStart && nowSec <= zEnd) {
      if (mode === 'aggressive_punch') {
        const targetScale = Math.min(z.scale ?? 1.9, PIPELINE_LIMITS.MAX_ZOOM_SCALE);
        const localF = Math.round((nowSec - zStart) * fps);
        const totalF = Math.max(8, Math.round(dur * fps));
        const inPop = spring({ frame: localF, fps, config: { damping: 14, stiffness: 520, mass: 0.35 } });
        const outRamp = interpolate(localF, [Math.max(0, totalF - 5), totalF], [1, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        zoomScale *= 1.0 + (targetScale - 1.0) * Math.min(inPop, outRamp);
      } else if (mode === 'slow_creep') {
        const targetScale = Math.min(z.scale ?? 1.55, PIPELINE_LIMITS.MAX_CREEP_ZOOM_SCALE);
        const progress = Math.min(1, Math.max(0, (nowSec - zStart) / dur));
        const easeOut = 1 - Math.pow(1 - progress, 2.2);
        zoomScale *= 1.0 + (targetScale - 1.0) * easeOut;
      } else if (mode === 'smooth') {
        const targetScale = Math.min(z.scale ?? 1.25, PIPELINE_LIMITS.MAX_SMOOTH_ZOOM_SCALE);
        const progress = (nowSec - zStart) / dur;
        zoomScale *= 1.0 + (targetScale - 1.0) * Math.sin(Math.PI * progress);
      } else {
        // 'snap_hold' or legacy 'snap'
        const targetScale = Math.min(z.scale ?? 1.55, PIPELINE_LIMITS.MAX_SNAP_ZOOM_SCALE);
        const localF = Math.round((nowSec - zStart) * fps);
        const totalF = Math.max(6, Math.round(dur * fps));
        const inPop = spring({ frame: localF, fps, config: { damping: 16, stiffness: 420, mass: 0.4 } });
        const outRamp = interpolate(localF, [Math.max(0, totalF - 6), totalF], [1, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        zoomScale *= 1.0 + (targetScale - 1.0) * Math.min(inPop, outRamp);
      }
      originX = z.originX ?? 50;
      originY = z.originY ?? 50;
    }
  }

  // 2. ImpactShake (dampened micro-rumble on hits/crashes/wipes)
  let shakeX = 0;
  let shakeY = 0;
  for (const sh of seg.shakes || []) {
    const startF = Math.round(sh.atSec * fps);
    const durF = sh.durationFrames ?? 8;
    if (frame >= startF && frame <= startF + durF) {
      const progress = (frame - startF) / durF;
      const intensity = sh.intensity ?? 14;
      shakeX += Math.sin(frame * 2.7) * intensity * (1 - progress);
      shakeY += Math.cos(frame * 3.1) * intensity * 0.7 * (1 - progress);
    }
  }

  // 3. DespairFreeze monochrome filter check
  const freezes = seg.freezes || [];
  const activeFreeze = freezes.find(
    (f) => nowSec >= f.atSec && nowSec <= f.atSec + (f.durationSec ?? 1.5)
  );
  const videoFilter =
    activeFreeze && activeFreeze.monochrome !== false
      ? 'grayscale(100%) contrast(130%)'
      : 'none';

  // 4. Fast 4-frame whip-pan blur intro transition (skip on very first frame of montage)
  const whipBlur = !isFirst && frame < 4 ? interpolate(frame, [0, 4], [12, 0]) : 0;
  const combinedFilter =
    whipBlur > 0.1
      ? `${videoFilter === 'none' ? '' : videoFilter + ' '}blur(${whipBlur.toFixed(1)}px)`
      : videoFilter;

  // 5. CHM AudioVacuum (mute video audio to 0 during silence windows or DespairFreeze)
  const silences = seg.silences || [];
  const inSilence =
    silences.some((s) => nowSec >= s.startSec && nowSec <= s.endSec) || Boolean(activeFreeze);
  const baseVol = seg.videoVolume ?? 1.0;

  const startFrame = Math.round(seg.startSec * fps);
  const endFrame = Math.round(seg.endSec * fps);
  const offsetY = seg.cropOffsetY ?? 0;

  return (
    <AbsoluteFill style={{ backgroundColor: '#000', overflow: 'hidden' }}>
      {/* Full-bleed video canvas (ZERO black bars) */}
      <AbsoluteFill
        style={{
          transform: `translate(${shakeX}px, ${shakeY}px) scale(${zoomScale}) translateY(${offsetY}%)`,
          transformOrigin: `${originX}% ${originY}%`,
          filter: combinedFilter,
        }}
      >
        <OffthreadVideo
          src={staticFile(`clips/${seg.videoFile}`)}
          startFrom={startFrame}
          endAt={endFrame}
          volume={() => (inSilence ? 0 : baseVol)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
      </AbsoluteFill>

      {/* DespairFreeze radial vignette */}
      <DespairOverlay freezes={freezes} />

      {/* TargetSpotlights (animated SVG circles + Metal Gear '!' alerts) */}
      <TargetSpotlights spotlights={seg.spotlights || []} />

      {/* Subtle bottom vignette for crisp caption legibility */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 440,
          background:
            'linear-gradient(to top, rgba(0,0,0,0.68) 0%, rgba(0,0,0,0.18) 55%, rgba(0,0,0,0) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* CHM / GTA 6 Vaporwave Creator Credit Badge */}
      <CreatorCredit platform={seg.platform} author={seg.author} theme={theme} />

      {/* Dual-Zone Karaoke Streamer (top) / NPC (bottom) / Editorial Smart Captions */}
      <SmartCaptions
        captions={seg.captions || []}
        theme={theme}
        streamerCaptionY={seg.streamerCaptionY}
      />

      {/* Optional per-segment BGM swap (e.g., upbeat track replacing awkward/unfitting clip audio) */}
      {seg.bgmFile ? (
        <Audio src={staticFile(`sfx/${seg.bgmFile}`)} volume={seg.bgmVolume ?? 0.5} loop />
      ) : null}

      {/* Multi-track Studio SFX (clamped by 85%+ Raw Audio Rule) */}
      {(seg.sfx || []).slice(0, PIPELINE_LIMITS.MAX_SFX_PER_CLIP).map((s, i) => {
        const sfxStartFrame = Math.max(0, Math.round(s.atSec * fps));
        return (
          <Sequence key={`${seg.id}-sfx-${i}`} from={sfxStartFrame}>
            <Audio src={staticFile(`sfx/${s.file}`)} volume={Math.min(s.volume ?? 0.75, 0.85)} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

export const MontageVideo: React.FC<MontageProps> = ({ theme, fps, segments, soundPlan }) => {
  // Precompute global timing windows matching TransitionSeries so global music
  // cleanly mutes under per-clip BGM swaps and ducks under game audio/speech.
  let cursorF = 0;
  const segWindows = segments.map((seg, idx) => {
    const effDur = Math.max(0.5, (seg.endSec - seg.startSec) / (seg.playbackRate ?? 1.0));
    const durF = Math.max(1, Math.round(effDur * fps));
    const prev = idx > 0 ? segments[idx - 1] : null;
    const isJump = Boolean(prev && prev.author === seg.author);
    const transKind = seg.transitionIn ?? (isJump ? 'none' : 'slide');
    if (idx > 0 && transKind !== 'none') {
      cursorF = Math.max(0, cursorF - TRANSITION_FRAMES);
    }
    const startF = cursorF;
    const endF = startF + durF;
    cursorF = endF;
    return {
      startSec: startF / fps,
      endSec: endF / fps,
      hasBgmOverride: Boolean(seg.bgmFile),
      hasGameAudio: (seg.videoVolume ?? 1.0) > 0,
    };
  });

  const music = soundPlan?.music;
  const musicStartFrame = music?.start_s ? Math.max(0, Math.round(music.start_s * fps)) : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      <TransitionSeries>
        {segments.map((seg, idx) => {
          const effDur = Math.max(0.5, (seg.endSec - seg.startSec) / (seg.playbackRate ?? 1.0));
          const frames = Math.max(1, Math.round(effDur * fps));
          const prev = idx > 0 ? segments[idx - 1] : null;
          const isSameCreatorJumpCut = prev && prev.author === seg.author;
          const transKind = seg.transitionIn ?? (isSameCreatorJumpCut ? 'none' : 'slide');

          return (
            <React.Fragment key={seg.id}>
              {idx > 0 && transKind === 'wipe' ? (
                <TransitionSeries.Transition
                  presentation={wipe({ direction: 'from-left' })}
                  timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
                />
              ) : idx > 0 && transKind === 'slide' ? (
                <TransitionSeries.Transition
                  presentation={slide({ direction: idx % 2 === 1 ? 'from-right' : 'from-left' })}
                  timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
                />
              ) : null}
              <TransitionSeries.Sequence durationInFrames={frames}>
                <SegmentView seg={seg} theme={theme} isFirst={idx === 0} />
              </TransitionSeries.Sequence>
            </React.Fragment>
          );
        })}
      </TransitionSeries>

      {/* Dedicated Sound Editor Global BGM with dynamic ducking & silence-before-payoff cuts */}
      {music?.file ? (
        <Audio
          src={staticFile(`sfx/${music.file}`)}
          startFrom={musicStartFrame}
          loop
          volume={(f) => {
            const t = f / fps;
            const activeWin = segWindows.find((w) => t >= w.startSec && t <= w.endSec);
            if (activeWin?.hasBgmOverride) return 0;
            const inCut = (music.cut_points || []).some((c) => t >= c.start_s && t <= c.end_s);
            if (inCut) return dbToLinear(music.gain_db - 15);
            const duck = activeWin?.hasGameAudio ? music.duck_under_game_audio_db : 0;
            return dbToLinear(music.gain_db + duck);
          }}
        />
      ) : null}

      {/* Dedicated Sound Editor Rule-Checked & Peak-Synced SFX / Meme Events */}
      {(soundPlan?.events || []).map((ev, i) => {
        const startFrame = Math.max(0, Math.round((ev.play_at_s ?? ev.t) * fps));
        const trimFrames = ev.trim_start_s ? Math.max(0, Math.round(ev.trim_start_s * fps)) : 0;
        const endAtFrame = ev.max_duration_s
          ? trimFrames + Math.max(1, Math.round(ev.max_duration_s * fps))
          : undefined;
        return (
          <Sequence key={`sp-ev-${i}-${ev.file}`} from={startFrame}>
            <Audio
              src={staticFile(`sfx/${ev.file}`)}
              startFrom={trimFrames}
              endAt={endAtFrame}
              volume={dbToLinear(ev.gain_db ?? 0)}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
