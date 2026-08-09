import { useEffect, useRef, useState, ReactNode } from "react";

const prefersReduced =
  typeof window !== "undefined" &&
  window.matchMedia &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* One-shot IntersectionObserver reveal. Returns [ref, inView]. */
export function useReveal<T extends HTMLElement>(threshold = 0.12) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(prefersReduced);
  useEffect(() => {
    if (prefersReduced || !ref.current) {
      setInView(true);
      return;
    }
    const el = ref.current;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setInView(true);
            io.unobserve(e.target);
          }
        }
      },
      { threshold, rootMargin: "0px 0px -12% 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return { ref, inView };
}

/* Wrapper that fades + rises into view once. */
export function Reveal({
  children,
  delay = 0,
  className = "",
  as = "div",
  style,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: any;
  style?: React.CSSProperties;
}) {
  const { ref, inView } = useReveal<HTMLDivElement>();
  const Tag = as as any;
  return (
    <Tag
      ref={ref}
      className={`reveal ${inView ? "in" : ""} ${className}`}
      style={{ ...(style || {}), ["--reveal-delay" as any]: `${delay}ms` }}
    >
      {children}
    </Tag>
  );
}

/* Scroll-driven hero sun. Returns sun (0..1) and t (-1..1). */
export function useScrollSun<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [state, setState] = useState({ sun: 0, t: -1 });
  useEffect(() => {
    if (prefersReduced) return;
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        const el = ref.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const p = (window.innerHeight - rect.top) / (rect.height + window.innerHeight);
        const sun = Math.min(1, Math.max(0, (p - 0.45) * 1.9));
        const t = sun * 2 - 1;
        setState({ sun, t });
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);
  return { ref, ...state };
}

/* Magnetic tilt + pointer light for cards. Spread onto the element. */
export function useMagnetic<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  function onMove(e: React.MouseEvent) {
    if (prefersReduced) return;
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = e.clientX - r.left;
    const y = e.clientY - r.top;
    const rx = -(((y / r.height) * 2 - 1) * 5);
    const ry = ((x / r.width) * 2 - 1) * 5;
    el.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-4px)`;
    el.style.setProperty("--mx", `${(x / r.width) * 100}%`);
    el.style.setProperty("--my", `${(y / r.height) * 100}%`);
  }
  function onLeave() {
    const el = ref.current;
    if (el) el.style.transform = "";
  }
  return { ref, onMouseMove: onMove, onMouseLeave: onLeave };
}

/* rAF count-up (easeOutCubic). Fires once when trigger becomes true. */
export function useCountUp(target: number, trigger: boolean, duration = 1400, decimals = 0) {
  const [val, setVal] = useState(prefersReduced ? target : 0);
  const started = useRef(false);
  useEffect(() => {
    if (!trigger || started.current) return;
    started.current = true;
    if (prefersReduced) {
      setVal(target);
      return;
    }
    const t0 = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(target * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [trigger, target, duration]);
  const factor = Math.pow(10, decimals);
  return Math.round(val * factor) / factor;
}
