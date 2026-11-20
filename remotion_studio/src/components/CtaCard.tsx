import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { CtaConfig, ThemeType } from '../types';

interface Props {
  cta: CtaConfig;
  theme: ThemeType;
}

export const CtaCard: React.FC<Props> = ({ cta, theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pop = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 260, mass: 0.45 },
  });
  const cardScale = 0.9 + 0.1 * pop;
  const glowPulse = 0.72 + 0.28 * Math.sin(frame * 0.16);

  const isOutro = cta.variant === 'outro';
  const isSponsor = cta.variant === 'sponsor';
  const accentPrimary = theme === 'gta6_vaporwave' ? '#FF5CD6' : '#F59E0B';
  const accentSecondary = theme === 'gta6_vaporwave' ? '#00F0FF' : '#38BDF8';
  const topTag = isSponsor ? 'SPONSORED SPOTLIGHT' : isOutro ? 'GTA 6 FEED' : 'QUICK CHECK';
  const badges = cta.badges || [];

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(155deg, #090414 0%, #19092C 52%, #081826 100%)',
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'hidden',
        padding: '0 64px',
      }}
    >
      {/* Ambient vaporwave radial glows */}
      <div
        style={{
          position: 'absolute',
          width: 820,
          height: 820,
          borderRadius: '50%',
          top: '18%',
          left: '-18%',
          background: `radial-gradient(circle, rgba(255,92,214,${0.26 * glowPulse}) 0%, rgba(255,92,214,0) 68%)`,
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 780,
          height: 780,
          borderRadius: '50%',
          bottom: '12%',
          right: '-18%',
          background: `radial-gradient(circle, rgba(0,240,255,${0.22 * glowPulse}) 0%, rgba(0,240,255,0) 68%)`,
          pointerEvents: 'none',
        }}
      />

      {/* Subtle scanline texture */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'repeating-linear-gradient(to bottom, rgba(255,255,255,0.03) 0px, rgba(255,255,255,0.03) 1px, transparent 1px, transparent 5px)',
          pointerEvents: 'none',
        }}
      />

      {/* Main glassmorphic CTA panel */}
      <div
        style={{
          width: '100%',
          maxWidth: 920,
          backgroundColor: 'rgba(13, 8, 27, 0.84)',
          border: `2.5px solid ${accentPrimary}`,
          borderRadius: 32,
          padding: isOutro ? '60px 44px' : '48px 40px',
          boxShadow: `0 0 48px rgba(255, 92, 214, ${0.28 * glowPulse}), 0 22px 60px rgba(0, 0, 0, 0.65)`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          transform: `scale(${cardScale})`,
          gap: isOutro ? 30 : 24,
        }}
      >
        <div
          style={{
            padding: '8px 22px',
            borderRadius: 999,
            backgroundColor: 'rgba(0, 240, 255, 0.14)',
            border: `1.5px solid ${accentSecondary}`,
            color: accentSecondary,
            fontFamily: "'Montserrat', 'Segoe UI', sans-serif",
            fontSize: 22,
            fontWeight: 800,
            letterSpacing: '0.16em',
            textTransform: 'uppercase',
          }}
        >
          {topTag}
        </div>

        <div
          style={{
            fontFamily: "'Montserrat', 'Bahnschrift Condensed', 'Impact', sans-serif",
            fontSize: isOutro ? 66 : 60,
            fontWeight: 900,
            lineHeight: 1.06,
            color: '#FFFFFF',
            letterSpacing: '0.03em',
            textTransform: 'uppercase',
            textShadow: `0 4px 24px rgba(255, 92, 214, 0.45)`,
          }}
        >
          {cta.headline}
        </div>

        {badges.length > 0 ? (
          <div
            style={{
              display: 'flex',
              flexDirection: isOutro ? 'column' : 'row',
              flexWrap: 'wrap',
              justifyContent: 'center',
              alignItems: 'center',
              gap: isOutro ? 16 : 14,
              width: '100%',
            }}
          >
            {badges.map((badge, idx) => {
              const badgePop = interpolate(frame, [idx * 3, idx * 3 + 8], [0.88, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              });
              const borderCol = idx % 2 === 0 ? accentSecondary : accentPrimary;
              return (
                <div
                  key={`${badge}-${idx}`}
                  style={{
                    minWidth: isOutro ? 480 : undefined,
                    padding: isOutro ? '18px 34px' : '14px 24px',
                    borderRadius: 18,
                    background: 'linear-gradient(135deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.04) 100%)',
                    border: `2px solid ${borderCol}`,
                    color: '#FFFFFF',
                    fontFamily: "'Montserrat', 'Segoe UI', sans-serif",
                    fontSize: isOutro ? 34 : 28,
                    fontWeight: 800,
                    letterSpacing: '0.05em',
                    boxShadow: `0 6px 24px rgba(0, 0, 0, 0.35)`,
                    transform: `scale(${badgePop})`,
                  }}
                >
                  {badge}
                </div>
              );
            })}
          </div>
        ) : null}

        <div
          style={{
            fontFamily: "'Montserrat', 'Segoe UI', sans-serif",
            fontSize: isOutro ? 30 : 32,
            fontWeight: 800,
            color: '#FFE600',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}
        >
          {cta.subline}
        </div>

        {cta.sponsorText ? (
          <div
            style={{
              marginTop: 6,
              paddingTop: 18,
              borderTop: '1px solid rgba(255, 255, 255, 0.16)',
              width: '86%',
              fontFamily: "'Montserrat', 'Segoe UI', sans-serif",
              fontSize: 22,
              fontWeight: 700,
              color: 'rgba(255, 255, 255, 0.78)',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
            }}
          >
            {cta.sponsorText}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
