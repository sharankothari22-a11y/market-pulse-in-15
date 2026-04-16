import { useEffect, useState } from 'react';

const SPLASH_DURATION_MS = 15000;
const FADE_MS = 700;

export const SplashScreen = ({ onDone }) => {
  const [progress, setProgress] = useState(0);
  const [fadingOut, setFadingOut] = useState(false);

  useEffect(() => {
    const start = Date.now();
    const tick = setInterval(() => {
      const elapsed = Date.now() - start;
      const pct = Math.min(100, (elapsed / SPLASH_DURATION_MS) * 100);
      setProgress(pct);
    }, 50);

    const fadeTimer = setTimeout(() => {
      setFadingOut(true);
    }, SPLASH_DURATION_MS);

    const doneTimer = setTimeout(() => {
      if (onDone) onDone();
    }, SPLASH_DURATION_MS + FADE_MS);

    return () => {
      clearInterval(tick);
      clearTimeout(fadeTimer);
      clearTimeout(doneTimer);
    };
  }, [onDone]);

  return (
    <div
      className="fixed inset-0 flex flex-col items-center justify-center"
      style={{
        zIndex: 9999,
        backgroundColor: '#0A1628',
        opacity: fadingOut ? 0 : 1,
        visibility: fadingOut && progress >= 100 ? 'visible' : 'visible',
        transition: `opacity ${FADE_MS}ms ease-out`,
        pointerEvents: fadingOut ? 'none' : 'auto',
      }}
      data-testid="splash-screen"
    >
      {/* Subtle gold radial glow */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(201, 168, 76, 0.08) 0%, transparent 60%)',
          pointerEvents: 'none',
        }}
      />

      {/* Logos row */}
      <div className="relative flex items-center gap-10 md:gap-16 px-8">
        {/* BEAVER INTELLIGENCE */}
        <div className="flex flex-col items-center text-center">
          <div
            className="font-serif-display font-black text-[#F5F0E8] leading-none"
            style={{
              fontSize: 'clamp(44px, 7vw, 84px)',
              letterSpacing: '0.02em',
            }}
          >
            BEAVER
          </div>
          <div
            className="my-3"
            style={{
              width: '100%',
              height: '1px',
              background: 'linear-gradient(90deg, transparent, #C9A84C 20%, #C9A84C 80%, transparent)',
            }}
          />
          <div
            className="text-[#C9A84C] font-medium"
            style={{
              fontSize: 'clamp(10px, 1.1vw, 14px)',
              letterSpacing: '0.45em',
            }}
          >
            INTELLIGENCE
          </div>
        </div>

        {/* Vertical divider */}
        <div
          style={{
            width: '1px',
            height: 'clamp(70px, 10vw, 120px)',
            background: 'linear-gradient(180deg, transparent, rgba(201, 168, 76, 0.55) 30%, rgba(201, 168, 76, 0.55) 70%, transparent)',
          }}
        />

        {/* TIPSONS */}
        <div className="flex flex-col items-center text-center">
          <div
            className="font-serif-display font-black text-[#F5F0E8] leading-none"
            style={{
              fontSize: 'clamp(44px, 7vw, 84px)',
              letterSpacing: '0.04em',
            }}
          >
            TIPSONS
          </div>
          <div
            className="my-3"
            style={{
              width: '100%',
              height: '1px',
              background: 'linear-gradient(90deg, transparent, #C9A84C 20%, #C9A84C 80%, transparent)',
            }}
          />
          <div
            className="text-[#C9A84C] font-medium"
            style={{
              fontSize: 'clamp(10px, 1.1vw, 14px)',
              letterSpacing: '0.45em',
            }}
          >
            CAPITAL
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div
        className="relative mt-16 overflow-hidden"
        style={{
          width: 'min(520px, 70vw)',
          height: '2px',
          backgroundColor: 'rgba(201, 168, 76, 0.12)',
          borderRadius: '1px',
        }}
        data-testid="splash-progress-track"
      >
        <div
          className="h-full"
          style={{
            width: `${progress}%`,
            backgroundColor: '#C9A84C',
            boxShadow: '0 0 8px rgba(201, 168, 76, 0.6)',
            transition: 'width 0.1s linear',
          }}
          data-testid="splash-progress-fill"
        />
      </div>

      {/* Tagline */}
      <p
        className="mt-6 font-medium"
        style={{
          color: 'rgba(245, 240, 232, 0.55)',
          fontSize: '11px',
          letterSpacing: '0.38em',
        }}
      >
        EQUITY RESEARCH <span style={{ color: '#C9A84C' }}>·</span> DECISION INTELLIGENCE
      </p>

      {/* Tiny version mark */}
      <p
        className="absolute bottom-6 font-mono-tight"
        style={{
          color: 'rgba(201, 168, 76, 0.4)',
          fontSize: '10px',
          letterSpacing: '0.2em',
        }}
      >
        v1.0 · INITIALIZING MARKET SYSTEMS
      </p>
    </div>
  );
};

export default SplashScreen;
