import React from 'react';
import { Composition } from 'remotion';
import { MontageVideo, TRANSITION_FRAMES } from './MontageVideo';
import { MontageProps } from './types';

const defaultProps: MontageProps = {
  channelId: 'gta6',
  theme: 'gta6_vaporwave',
  fps: 30,
  segments: [],
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="MontageVideo"
      component={MontageVideo}
      durationInFrames={30 * 65}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultProps}
      calculateMetadata={({ props }: { props: MontageProps }) => {
        const fps = props.fps || 30;
        const segs = props.segments || [];
        let totalFrames = 0;
        segs.forEach((s, idx) => {
          const effDur = Math.max(0.5, (s.endSec - s.startSec) / (s.playbackRate ?? 1.0));
          totalFrames += Math.max(1, Math.round(effDur * fps));
          if (idx > 0) {
            const prev = segs[idx - 1];
            const kind = s.transitionIn ?? (prev.author === s.author ? 'none' : 'slide');
            if (kind !== 'none') totalFrames -= TRANSITION_FRAMES;
          }
        });
        return {
          fps,
          durationInFrames: Math.max(30, totalFrames),
        };
      }}
    />
  );
};
