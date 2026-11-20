import React from 'react';
import { spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { CaptionCue, ThemeType } from '../types';

interface Props {
  captions: CaptionCue[];
  theme: ThemeType;
  streamerCaptionY?: number;
}

export const SmartCaptions: React.FC<Props> = ({ captions, theme, streamerCaptionY = 27 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const nowSec = frame / fps;

  // Render all active captions (allows simultaneous top streamer karaoke + bottom NPC speech + editorial popup)
  const activeList = captions.filter((c) => nowSec >= c.startSec && nowSec <= c.endSec);
  if (!activeList.length) return null;

  return (
    <>
      {activeList.map((active, i) => {
        const localFrame = Math.max(0, Math.round((nowSec - active.startSec) * fps));
        // Crisp 3-frame CHM/Red Arcade syllabic pop (0.85 -> 1.0)
        const pop = spring({
          frame: localFrame,
          fps,
          config: { damping: 12, stiffness: 320, mass: 0.45 },
        });
        const scale = 0.85 + 0.15 * pop;

        const isNpc = active.role === 'npc';
        const isEditorial = active.role === 'editorial';
        const isStreamer = !isNpc && !isEditorial;
        const hasCoords = active.x !== undefined && active.y !== undefined;

        const baseColor = isNpc
          ? '#00F0FF' // Electric cyan for in-game NPC dialogue (bottom zone)
          : isEditorial
            ? theme === 'gta6_vaporwave'
              ? '#FF5CD6'
              : '#A855F7'
            : '#FFFFFF'; // Crisp pure white base for streamer speech (top zone)

        const activeWordColor = isNpc ? '#4ADE80' : '#FFE600'; // Neon mint-green for NPC active word (never white), neon yellow for streamer

        const fontSize = isNpc ? 44 : isEditorial ? 54 : 60;
        const rot = active.rotateDeg ?? (hasCoords ? -6 : 0);

        let posStyle: React.CSSProperties;
        if (hasCoords) {
          posStyle = {
            position: 'absolute',
            left: `${active.x}%`,
            top: `${active.y}%`,
            transform: `translate(-50%, -50%) rotate(${rot}deg) scale(${scale})`,
            maxWidth: '78%',
          };
        } else if (isEditorial) {
          posStyle = {
            position: 'absolute',
            left: 52,
            right: 52,
            top: '42%',
            display: 'flex',
            justifyContent: 'center',
            transform: `translateY(-50%) rotate(${rot}deg) scale(${scale})`,
          };
        } else if (isStreamer) {
          posStyle = {
            position: 'absolute',
            left: 48,
            right: 48,
            top: `${streamerCaptionY}%`,
            display: 'flex',
            justifyContent: 'center',
            transform: `translateY(-50%) rotate(${rot}deg) scale(${scale})`,
          };
        } else {
          // Bottom zone for in-game NPC dialogue
          posStyle = {
            position: 'absolute',
            left: 52,
            right: 52,
            bottom: 215,
            display: 'flex',
            justifyContent: 'center',
            transform: `rotate(${rot}deg) scale(${scale})`,
          };
        }

        const sharedTextStyle: React.CSSProperties = {
          textAlign: 'center',
          fontFamily: "'Montserrat', 'Bahnschrift Condensed', 'Impact', 'Segoe UI', sans-serif",
          fontSize,
          fontWeight: isNpc ? 800 : 900,
          fontStyle: isNpc || (isEditorial && !hasCoords) ? 'italic' : 'normal',
          lineHeight: 1.08,
          letterSpacing: isNpc ? '0.02em' : '0.04em',
          textTransform: isEditorial ? 'none' : 'uppercase',
          WebkitTextStroke: isNpc ? '6px #000000' : '7px #000000',
          paintOrder: 'stroke fill',
          textShadow: '3px 4px 0px #000000',
        };

        const words = active.words && active.words.length > 0 ? active.words : null;
        let activeWordIdx = -1;
        if (words) {
          activeWordIdx = words.findIndex((w) => nowSec >= w.startSec && nowSec < w.endSec);
          if (activeWordIdx === -1) {
            for (let idx = words.length - 1; idx >= 0; idx--) {
              if (nowSec >= words[idx].startSec) {
                activeWordIdx = idx;
                break;
              }
            }
            if (activeWordIdx === -1) activeWordIdx = 0;
          }
        }

        const npcPillStyle: React.CSSProperties = isNpc
          ? {
              backgroundColor: 'rgba(4, 16, 26, 0.72)',
              border: '2px solid rgba(0, 240, 255, 0.55)',
              borderRadius: 16,
              padding: '8px 20px',
              boxShadow: '0 6px 20px rgba(0, 0, 0, 0.45)',
            }
          : {};

        return (
          <div key={`${active.startSec}-${active.role}-${i}`} style={{ ...posStyle, pointerEvents: 'none', zIndex: 90 }}>
            {words ? (
              <div
                style={{
                  ...sharedTextStyle,
                  ...npcPillStyle,
                  display: 'flex',
                  flexWrap: 'wrap',
                  justifyContent: 'center',
                  alignItems: 'center',
                  columnGap: isNpc ? '10px' : '14px',
                  rowGap: '4px',
                }}
              >
                {words.map((w, wIdx) => {
                  const isActiveWord = wIdx === activeWordIdx;
                  const label = isNpc
                    ? words.length === 1
                      ? `"${w.text}"`
                      : wIdx === 0
                        ? `"${w.text}`
                        : wIdx === words.length - 1
                          ? `${w.text}"`
                          : w.text
                    : w.text;
                  return (
                    <span
                      key={`${wIdx}-${w.startSec}`}
                      style={{
                        display: 'inline-block',
                        color: isActiveWord ? activeWordColor : baseColor,
                        transform: isActiveWord
                          ? isNpc
                            ? 'scale(1.06)'
                            : 'scale(1.10)'
                          : 'scale(1.0)',
                        transformOrigin: 'center center',
                        WebkitTextStroke: isNpc ? '6px #000000' : '7px #000000',
                        paintOrder: 'stroke fill',
                      }}
                    >
                      {label}
                    </span>
                  );
                })}
              </div>
            ) : (
              <div
                style={{
                  ...sharedTextStyle,
                  ...npcPillStyle,
                  color: baseColor,
                }}
              >
                {isNpc ? `"${active.text}"` : active.text}
              </div>
            )}
          </div>
        );
      })}
    </>
  );
};
