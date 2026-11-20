import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { PlatformType, ThemeType } from '../types';

interface Props {
  platform: PlatformType;
  author: string;
  theme: ThemeType;
}

const PlatformIcon: React.FC<{ platform: PlatformType; size?: number }> = ({
  platform,
  size = 28,
}) => {
  if (platform === 'twitch') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <rect width="24" height="24" rx="5" fill="#9146FF" />
        <path
          d="M6.2 4.5L4.8 7.5V17.5h3.5v2l2-2h2.8l5.1-5.1V4.5H6.2zm10.4 7.1l-2.3 2.3h-3.2l-1.8 1.8v-1.8H7.5V6.1h9.1v5.5z"
          fill="#FFFFFF"
        />
        <rect x="13.2" y="8" width="1.5" height="3.6" fill="#FFFFFF" />
        <rect x="10.2" y="8" width="1.5" height="3.6" fill="#FFFFFF" />
      </svg>
    );
  }
  if (platform === 'youtube') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <rect x="1.5" y="4" width="21" height="16" rx="4.5" fill="#FF204E" />
        <path d="M9.8 8.6L16 12L9.8 15.4V8.6Z" fill="#FFFFFF" />
      </svg>
    );
  }
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M16.6 5.8c-.9-.9-1.4-2.1-1.5-3.4h-2.8v12.5c0 1.4-1.1 2.5-2.5 2.5s-2.5-1.1-2.5-2.5 1.1-2.5 2.5-2.5c.3 0 .5 0 .8.1V9.6c-.3 0-.5-.1-.8-.1-2.9 0-5.3 2.4-5.3 5.3s2.4 5.3 5.3 5.3 5.3-2.4 5.3-5.3V8.6c1.1.8 2.5 1.3 4 1.3V7.1c-1 0-1.9-.5-2.5-1.3z"
        fill="#00F0FF"
        transform="translate(-1,-0.6)"
      />
      <path
        d="M16.6 5.8c-.9-.9-1.4-2.1-1.5-3.4h-2.8v12.5c0 1.4-1.1 2.5-2.5 2.5s-2.5-1.1-2.5-2.5 1.1-2.5 2.5-2.5c.3 0 .5 0 .8.1V9.6c-.3 0-.5-.1-.8-.1-2.9 0-5.3 2.4-5.3 5.3s2.4 5.3 5.3 5.3 5.3-2.4 5.3-5.3V8.6c1.1.8 2.5 1.3 4 1.3V7.1c-1 0-1.9-.5-2.5-1.3z"
        fill="#FF007F"
        transform="translate(1,0.6)"
      />
      <path
        d="M16.6 5.8c-.9-.9-1.4-2.1-1.5-3.4h-2.8v12.5c0 1.4-1.1 2.5-2.5 2.5s-2.5-1.1-2.5-2.5 1.1-2.5 2.5-2.5c.3 0 .5 0 .8.1V9.6c-.3 0-.5-.1-.8-.1-2.9 0-5.3 2.4-5.3 5.3s2.4 5.3 5.3 5.3 5.3-2.4 5.3-5.3V8.6c1.1.8 2.5 1.3 4 1.3V7.1c-1 0-1.9-.5-2.5-1.3z"
        fill="#FFFFFF"
      />
    </svg>
  );
};

export const CreatorCredit: React.FC<Props> = ({ platform, author, theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // GTA 6 Vaporwave Theme (Red Arcade flush-ribbon × Vice City neon)
  if (theme === 'gta6_vaporwave') {
    const enter = spring({ frame, fps, config: { damping: 14, stiffness: 200, mass: 0.7 } });
    const exitStart = Math.round(4.5 * fps);
    const exit = spring({
      frame: Math.max(0, frame - exitStart),
      fps,
      config: { damping: 16, stiffness: 180 },
    });
    const tx = interpolate(enter, [0, 1], [-420, 0]) - interpolate(exit, [0, 1], [0, 420]);
    const opacity = interpolate(exit, [0, 0.9], [1, 0], { extrapolateRight: 'clamp' });

    return (
      <div
        style={{
          position: 'absolute',
          top: 96,
          left: 0,
          transform: `translateX(${tx}px)`,
          opacity,
          zIndex: 100,
        }}
      >
        {/* Header tag */}
        <div
          style={{
            backgroundColor: '#FF007F',
            color: '#FFFFFF',
            fontFamily: "'Bahnschrift', 'Segoe UI', sans-serif",
            fontWeight: 800,
            fontSize: 16,
            letterSpacing: '0.18em',
            padding: '4px 16px 4px 28px',
            width: 'fit-content',
            borderRadius: '0 6px 0 0',
          }}
        >
          GTA 6 FEED
        </div>
        {/* Flush-left obsidian body + razor-thin cyan->pink underline */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            background: 'linear-gradient(90deg, rgba(10,10,16,0.92) 0%, rgba(16,12,28,0.78) 82%, rgba(16,12,28,0) 100%)',
            padding: '10px 56px 12px 28px',
            borderBottom: '3px solid transparent',
            borderImage: 'linear-gradient(90deg, #00F0FF 0%, #FF007F 75%, transparent 100%) 1',
            backdropFilter: 'blur(10px)',
          }}
        >
          <PlatformIcon platform={platform} size={30} />
          <span
            style={{
              fontFamily: "'Bahnschrift SemiCondensed', 'Impact', 'Segoe UI', sans-serif",
              fontSize: 34,
              fontWeight: 700,
              letterSpacing: '0.06em',
              color: '#FFFFFF',
              textTransform: 'uppercase',
              textShadow: '0 0 10px rgba(0, 240, 255, 0.55), 0 2px 4px rgba(0,0,0,0.9)',
            }}
          >
            {author}
          </span>
        </div>
      </div>
    );
  }

  // WoW Classic Hardcore Theme (CHM top-center gold-bordered pill, persistent)
  const pop = spring({ frame, fps, config: { damping: 14, stiffness: 240, mass: 0.6 } });
  const scale = interpolate(pop, [0, 1], [0.82, 1.0]);
  const opacity = interpolate(frame, [0, 5], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        position: 'absolute',
        top: 68,
        left: '50%',
        transform: `translateX(-50%) scale(${scale})`,
        opacity,
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 24px 8px 16px',
        borderRadius: 999,
        backgroundColor: 'rgba(13, 14, 18, 0.90)',
        border: '2px solid #C69B6D',
        boxShadow: '0 6px 18px rgba(0,0,0,0.8)',
      }}
    >
      <PlatformIcon platform={platform} size={28} />
      <span
        style={{
          fontFamily: "'Segoe UI', system-ui, sans-serif",
          fontSize: 30,
          fontWeight: 700,
          color: '#FFFFFF',
          textShadow: '1px 2px 3px #000000',
        }}
      >
        {author}
      </span>
    </div>
  );
};
