import { useEffect, useRef, useState, type RefObject } from 'react';

/**
 * Counts from 0 to `target` once the element it observes scrolls into view.
 * Returns [value, ref]; attach ref to the element whose visibility triggers
 * the count. Respects prefers-reduced-motion by showing the target instantly.
 */
export default function useCountUp(
  target: number,
  duration = 1100
): [number, RefObject<HTMLSpanElement | null>] {
  const [value, setValue] = useState(() =>
    typeof window !== 'undefined' &&
    typeof IntersectionObserver !== 'undefined' &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches
      ? 0
      : target
  );
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || value === target) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && !started.current) {
            started.current = true;
            const start = performance.now();
            const tick = (now: number) => {
              const progress = Math.min((now - start) / duration, 1);
              const eased = 1 - Math.pow(1 - progress, 3);
              setValue(Math.round(eased * target));
              if (progress < 1) requestAnimationFrame(tick);
            };
            requestAnimationFrame(tick);
            observer.disconnect();
          }
        }
      },
      { threshold: 0.4 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [target, duration, value]);

  return [value, ref];
}