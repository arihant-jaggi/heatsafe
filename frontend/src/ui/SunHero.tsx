import { useScrollSun } from "./motion";

/**
 * Scroll-driven sun + hatched shadow triangle. The whole SVG is wrapped in an
 * element whose scroll position drives the sun/shadow translation; inner parts
 * (disc breathe, ray pulse, shadow swing) loop on their own.
 */
export function SunHero() {
  const { ref, t } = useScrollSun<HTMLDivElement>();

  const sunTransform = `translate(${t * 62}px, ${Math.pow(Math.abs(t), 2) * 40}px)`;
  const shadowTransform = `translate(${-t * 40}px, 0) skewX(${-t * 18}deg)`;

  const rays = Array.from({ length: 12 }, (_, i) => {
    const a = (i / 12) * Math.PI * 2;
    const cx = 250,
      cy = 178,
      r0 = 126,
      r1 = 166;
    return {
      x1: cx + Math.cos(a) * r0,
      y1: cy + Math.sin(a) * r0,
      x2: cx + Math.cos(a) * r1,
      y2: cy + Math.sin(a) * r1,
      d: i * 0.22,
    };
  });

  return (
    <div ref={ref}>
      <svg className="sun-svg" viewBox="0 0 500 380" fill="none" aria-hidden="true">
        {/* hatched shadow triangle */}
        <defs>
          <pattern id="hatch" width="9" height="9" patternTransform="rotate(58)" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="0" y2="9" stroke="#2f4a6b" strokeOpacity="0.5" strokeWidth="1.4" />
          </pattern>
          <radialGradient id="sunFill" cx="42%" cy="38%" r="70%">
            <stop offset="0%" stopColor="#ffc247" />
            <stop offset="60%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#e0870b" />
          </radialGradient>
        </defs>

        <g className="sun-shadow-outer" style={{ transform: shadowTransform }}>
          <g className="sun-shadow-swing">
            <path
              d="M250 250 L492 366 L250 366 Z"
              fill="url(#hatch)"
              stroke="#2f4a6b"
              strokeOpacity="0.55"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </g>
        </g>

        <g className="sun-move" style={{ transform: sunTransform }}>
          <g>
            {rays.map((r, i) => (
              <line
                key={i}
                className="sun-ray"
                x1={r.x1}
                y1={r.y1}
                x2={r.x2}
                y2={r.y2}
                stroke="#f5a623"
                strokeWidth="1.6"
                strokeLinecap="round"
                style={{ animationDelay: `${r.d}s` }}
              />
            ))}
          </g>
          <circle className="sun-disc" cx="250" cy="178" r="112" fill="url(#sunFill)" stroke="#1e3a5f" strokeWidth="3" />
          {/* subtle limb shading stroke */}
          <path d="M312 214 q-22 28 -56 38" stroke="#1e3a5f" strokeOpacity="0.32" strokeWidth="2.4" fill="none" strokeLinecap="round" />
        </g>
      </svg>
    </div>
  );
}
