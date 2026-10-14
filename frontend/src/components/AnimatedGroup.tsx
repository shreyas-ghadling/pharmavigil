import type { ReactNode } from "react";
import { useReveal } from "../hooks/useReveal";

export default function AnimatedGroup({ children, className, animationKey = "" }: {
  children: ReactNode;
  className?: string;
  animationKey?: string | number;
}) {
  const ref = useReveal<HTMLDivElement>(animationKey, ":scope > *");
  return <div ref={ref} className={className}>{children}</div>;
}
