import { useEffect, useRef, type ReactNode } from "react";
import { animate } from "animejs";

export default function AnimatedDisclosure({ summary, children, className }: {
  summary: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const summaryRef = useRef<HTMLElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const targetOpen = useRef(false);
  const animationRef = useRef<ReturnType<typeof animate> | null>(null);

  function settle() {
    const details = detailsRef.current;
    const body = bodyRef.current;
    if (!details || !body) return;
    details.open = targetOpen.current;
    body.inert = !targetOpen.current;
    body.style.height = "";
    body.style.opacity = "";
    body.style.overflow = "";
    summaryRef.current?.setAttribute("aria-expanded", String(targetOpen.current));
  }

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => {
      animationRef.current?.cancel();
      settle();
    };
    preference.addEventListener("change", onChange);
    return () => {
      preference.removeEventListener("change", onChange);
      animationRef.current?.cancel();
    };
  }, []);

  function toggle() {
    const details = detailsRef.current;
    const body = bodyRef.current;
    if (!details || !body) return;
    const wasOpen = details.open;
    const height = wasOpen ? body.getBoundingClientRect().height : 0;
    const opacity = wasOpen ? Number(getComputedStyle(body).opacity) : 0;
    animationRef.current?.cancel();
    targetOpen.current = !targetOpen.current;
    const opening = targetOpen.current;
    if (!opening && body.contains(document.activeElement)) summaryRef.current?.focus();
    body.inert = !opening;
    summaryRef.current?.setAttribute("aria-expanded", String(opening));
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      settle();
      return;
    }
    details.open = true;
    body.style.height = "auto";
    const fullHeight = body.getBoundingClientRect().height;
    body.style.overflow = "hidden";
    animationRef.current = animate(body, {
      height: [height, opening ? fullHeight : 0],
      opacity: [opacity, opening ? 1 : 0],
      duration: opening ? 240 : 180,
      ease: "outCubic",
      onComplete: settle,
    });
  }

  return <details ref={detailsRef} className={className}>
    <summary ref={summaryRef} onClick={(event) => { event.preventDefault(); toggle(); }}>{summary}</summary>
    <div ref={bodyRef} className="disclosure-body">{children}</div>
  </details>;
}
