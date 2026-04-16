import { useEffect, useState } from 'react';

const SPLASH_DURATION_MS = 10000;   // 10 seconds
const FADE_MS = 600;

const BEAVER_LOGO_URL = 'https://customer-assets.emergentagent.com/job_design-review-38/artifacts/tqw73ol3_Screenshot%202026-04-16%20at%206.20.25%E2%80%AFPM.png';
const TIPSONS_LOGO_URL = 'https://customer-assets.emergentagent.com/job_design-review-38/artifacts/sble7mpu_logo.png';

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

    const fadeTimer = setTimeout(() => setFadingOut(true), SPLASH_DURATION_MS);
    const doneTimer = setTimeout(() => { if (onDone) onDone(); }, SPLASH_DURATION_MS + FADE_MS);

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
        transition: `opacity ${FADE_MS}ms ease-out`,
        pointerEvents: fadingOut ? 'none' : 'auto',
      }}
      data-testid="splash-screen"
    >
      {/* Subtle gold radial glow */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(201, 168, 76, 0.10) 0%, transparent 65%)',
          pointerEvents: 'none',
        }}
      />

      {/* Beaver logo (centered, 180px) */}
      <div className="relative flex flex-col items-center">
        <div
          style={{
            width: 200,
            height: 200,
            borderRadius: '50%',
            overflow: 'hidden',
            backgroundColor: '#0A1628',
            boxShadow: '0 4px 24px rgba(201, 168, 76, 0.25)',
          }}
        >
          <img
            src={BEAVER_LOGO_URL}
            alt="Beaver Intelligence"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              mixBlendMode: 'lighten',
            }}
            data-testid="splash-logo"
          />
        </div>
      </div>

      {/* Progress bar */}
      <div
        className="relative mt-12 overflow-hidden"
        style={{
          width: 'min(420px, 65vw)',
          height: '2px',
          backgroundColor: 'rgba(201, 168, 76, 0.15)',
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
          color: 'rgba(245, 240, 232, 0.6)',
          fontSize: '11px',
          letterSpacing: '0.4em',
        }}
      >
        EQUITY RESEARCH <span style={{ color: '#C9A84C' }}>·</span> DECISION INTELLIGENCE
      </p>

      {/* In partnership with Tipsons */}
      <div
        className="absolute bottom-10 flex flex-col items-center"
        style={{ opacity: 0.85 }}
      >
        <p
          className="font-medium mb-2"
          style={{
            color: 'rgba(245, 240, 232, 0.4)',
            fontSize: '9px',
            letterSpacing: '0.32em',
          }}
        >
          IN PARTNERSHIP WITH
        </p>
        <img
          src={TIPSONS_LOGO_URL}
          alt="Tipsons"
          style={{
            width: 60,
            height: 60,
            objectFit: 'contain',
            opacity: 0.75,
            filter: 'brightness(1.1)',
          }}
        />
      </div>
    </div>
  );
};

export default SplashScreen;
