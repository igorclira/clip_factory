import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { FreezeCue, SpotlightCue } from '../types';

export const TargetSpotlights: React.FC<{ spotlights: SpotlightCue[] }> = ({ spotlights }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const nowSec = frame / fps;

  return (
    <>
      {spotlights.map((sp, idx) => {
        const dur = sp.durationSec ?? 1.1;
        if (nowSec < sp.atSec || nowSec > sp.atSec + dur) return null;

        const localFrame = Math.max(0, Math.round((nowSec - sp.atSec) * fps));
        const pop = spring({ frame: localFrame, fps, config: { damping: 10, stiffness: 280, mass: 0.5 } });

        if (sp.kind === 'alert') {
          // Classic Hardcore Moments / Metal Gear Solid '!' alert icon
          const color = sp.color ?? '#FFE600';
          const bounceY = Math.sin(localFrame * 0.45) * 6;
          return (
            <div
              key={`sp-${idx}`}
              style={{
                position: 'absolute',
                left: `${sp.x}%`,
                top: `${sp.y}%`,
                transform: `translate(-50%, -100%) translateY(${bounceY}px) scale(${pop})`,
                zIndex: 95,
                pointerEvents: 'none',
              }}
            >
              <svg width="84" height="120" viewBox="0 0 84 120">
                <rect x="30" y="10" width="24" height="68" rx="8" fill={color} stroke="#000" strokeWidth="6" />
                <circle cx="42" cy="98" r="13" fill={color} stroke="#000" strokeWidth="6" />
              </svg>
            </div>
          );
        }

        // Animated self-drawing red callout circle + bobbing arrow
        const r = sp.radius ?? 78;
        const color = sp.color ?? '#FF1E1E';
        const circ = 2 * Math.PI * r;
        const drawProgress = interpolate(localFrame, [0, 8], [0, 1], { extrapolateRight: 'clamp' });
        const dashOffset = circ * (1 - drawProgress);
        const arrowBob = Math.sin(localFrame * 0.4) * 10;

        return (
          <div
            key={`sp-${idx}`}
            style={{
              position: 'absolute',
              left: `${sp.x}%`,
              top: `${sp.y}%`,
              transform: 'translate(-50%, -50%)',
              zIndex: 95,
              pointerEvents: 'none',
            }}
          >
            <svg width={(r + 36) * 2} height={(r + 36) * 2} viewBox={`${-(r + 36)} ${-(r + 36)} ${(r + 36) * 2} ${(r + 36) * 2}`}>
              <circle
                cx="0"
                cy="0"
                r={r}
                fill="none"
                stroke="#000000"
                strokeWidth="13"
                strokeDasharray={circ}
                strokeDashoffset={dashOffset}
              />
              <circle
                cx="0"
                cy="0"
                r={r}
                fill="none"
                stroke={color}
                strokeWidth="7"
                strokeDasharray={circ}
                strokeDashoffset={dashOffset}
              />
              {/* Mechanical bobbing pointer arrow above circle */}
              <g transform={`translate(0, ${-r - 22 + arrowBob})`}>
                <polygon points="0,16 -14,-10 14,-10" fill={color} stroke="#000" strokeWidth="4" />
              </g>
            </svg>
          </div>
        );
      })}
    </>
  );
};

export const DespairOverlay: React.FC<{ freezes: FreezeCue[] }> = ({ freezes }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const nowSec = frame / fps;

  const active = freezes.find((f) => nowSec >= f.atSec && nowSec <= f.atSec + (f.durationSec ?? 1.5));
  if (!active) return null;

  const localFrame = Math.max(0, Math.round((nowSec - active.atSec) * fps));
  const opacity = interpolate(localFrame, [0, 6], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: 'radial-gradient(circle, transparent 35%, rgba(0, 0, 0, 0.86) 100%)',
        opacity,
        pointerEvents: 'none',
        zIndex: 80,
      }}
    />
  );
};
