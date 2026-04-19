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
        backgroundColor: '#FFFFFF',
        opacity: fadingOut ? 0 : 1,
        transition: `opacity ${FADE_MS}ms ease-out`,
        pointerEvents: fadingOut ? 'none' : 'auto',
      }}
      data-testid="splash-screen"
    >
      {/* Beaver × Tipsons lockup */}
      <div className="relative flex flex-row items-center justify-center">
        <div
          style={{
            width: 240,
            height: 240,
            borderRadius: '50%',
            overflow: 'hidden',
            backgroundColor: '#FFFFFF',
            filter: 'drop-shadow(0 12px 28px rgba(15,37,64,0.18))',
          }}
        >
          <img
            src={BEAVER_LOGO_URL}
            alt="Beaver Intelligence"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
            data-testid="splash-logo"
          />
        </div>
        <span
          style={{
            margin: '0 56px',
            fontFamily: 'Georgia, serif',
            fontWeight: 200,
            fontSize: 64,
            color: '#475569',
            lineHeight: 1,
          }}
          aria-hidden="true"
        >
          ×
        </span>
        <img
          src={TIPSONS_LOGO_URL}
          alt="Tipsons"
          style={{
            maxHeight: 220,
            width: 'auto',
            objectFit: 'contain',
          }}
          onError={(e) => {
            e.currentTarget.outerHTML =
              '<span style="font-family:Georgia,serif;font-weight:700;font-size:56px;color:#0D3B2E;letter-spacing:0.08em;">TIPSONS</span>';
          }}
        />
      </div>

      {/* Gold hairline divider / progress */}
      <div
        className="relative mt-12 overflow-hidden"
        style={{
          width: 'min(420px, 65vw)',
          height: '1px',
          backgroundColor: 'rgba(184, 147, 64, 0.18)',
          borderRadius: '1px',
        }}
        data-testid="splash-progress-track"
      >
        <div
          className="h-full"
          style={{
            width: `${progress}%`,
            backgroundColor: '#B89340',
            transition: 'width 0.1s linear',
          }}
          data-testid="splash-progress-fill"
        />
      </div>

      {/* Tagline */}
      <p
        className="mt-8"
        style={{
          color: '#475569',
          fontSize: '13px',
          letterSpacing: '0.15em',
          fontFamily: 'Georgia, serif',
        }}
      >
        EQUITY RESEARCH <span style={{ color: '#B89340' }}>·</span> DECISION INTELLIGENCE
      </p>

    </div>
  );
};

export default SplashScreen;
