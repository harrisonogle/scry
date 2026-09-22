import React from 'react';
import {theme} from '../theme';

// The short on-screen line for a scene, set in a band at the bottom (or as a pill over a full-bleed image).
export const Caption: React.FC<{text: string; pill?: boolean; top?: number; position?: 'top' | 'bottom'}> = ({text, pill, top, position}) => {
  if (pill) {
    return (
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          ...(position === 'top' ? {top: 40} : {bottom: 40}),
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            background: 'rgba(252, 252, 251, 0.96)',
            color: theme.ink,
            fontSize: 34,
            lineHeight: 1.25,
            padding: '16px 30px',
            borderRadius: 14,
            borderLeft: `8px solid ${theme.orange}`,
            boxShadow: '0 6px 24px rgba(0,0,0,0.25)',
            maxWidth: 1500,
          }}
        >
          {text}
        </div>
      </div>
    );
  }
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: top ?? 984,
        bottom: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 22,
        color: theme.muted,
        fontSize: 34,
        lineHeight: 1.2,
        padding: '0 80px',
      }}
    >
      <div style={{width: 14, height: 14, borderRadius: 7, background: theme.blue, flex: '0 0 auto'}} />
      <div style={{textAlign: 'center'}}>{text}</div>
    </div>
  );
};
