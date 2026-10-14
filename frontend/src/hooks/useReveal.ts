import { useLayoutEffect, useRef } from "react";
import { animate } from "animejs";

/** Small, bounded entrances. Content stays visible without animation support. */
export function useReveal<T extends HTMLElement>(
  token: string | number = "",
  selector?: string,
  distance = 6,
) {
  const ref = useRef<T>(null);
  useLayoutEffect(() => {
    const element = ref.current;
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!element || preference.matches) return;
    const targets = selector
      ? Array.from(element.querySelectorAll<HTMLElement>(selector)).filter((el) => el.getClientRects().length)
      : [element];
    if (!targets.length) return;
    const animation = animate(targets, {
      opacity: [0, 1],
      translateY: [distance, 0],
      duration: 240,
      delay: (_target?: unknown, index = 0) => Math.min(index * 22, 132),
      ease: "outCubic",
      onComplete: (completed) => completed.revert(),
    });
    const settle = () => animation.revert();
    preference.addEventListener("change", settle);
    return () => {
      preference.removeEventListener("change", settle);
      animation.revert();
    };
  }, [token, selector, distance]);
  return ref;
}
