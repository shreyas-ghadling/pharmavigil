import { useLayoutEffect, useRef, useState } from "react";
import { animate, stagger } from "animejs";
import { NavLink, useLocation } from "react-router-dom";
import { ChevronDown, type LucideIcon } from "lucide-react";
import type { Role } from "../types";

export interface NavigationItem {
  path: string;
  name: string;
  icon: LucideIcon;
  roles: Role[];
  children?: { name: string; value: string }[];
}

function NavigationGroup({
  item,
  active,
  expanded,
  selected,
  onToggle,
  onNavigate,
}: {
  item: NavigationItem;
  active: boolean;
  expanded: boolean;
  selected: string | null;
  onToggle: () => void;
  onNavigate: () => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const chevronRef = useRef<HTMLSpanElement>(null);
  const previousExpanded = useRef<boolean | null>(null);
  const groupId = `nav-${item.path.slice(1)}`;

  useLayoutEffect(() => {
    const panel = panelRef.current!;
    const chevron = chevronRef.current!;
    const links = Array.from(panel.querySelectorAll<HTMLElement>(".nav-child"));
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const initial = previousExpanded.current === null || previousExpanded.current === expanded;
    previousExpanded.current = expanded;
    const animations: ReturnType<typeof animate>[] = [];
    const settle = () => {
      panel.hidden = !expanded;
      panel.style.height = expanded ? "auto" : "0px";
      panel.style.overflow = expanded ? "visible" : "hidden";
      panel.style.marginTop = expanded ? "5px" : "0px";
      panel.style.marginBottom = expanded ? "5px" : "0px";
      chevron.style.transform = `rotate(${expanded ? 180 : 0}deg)`;
      links.forEach((link) => {
        link.style.opacity = "1";
        link.style.transform = "none";
      });
    };

    if (initial || preference.matches || !chevron.getClientRects().length) {
      settle();
    } else {
      const wasHidden = panel.hidden;
      panel.hidden = false;
      const height = panel.getBoundingClientRect().height;
      panel.style.height = `${height}px`;
      panel.style.overflow = "hidden";
      if (expanded && wasHidden) {
        links.forEach((link) => {
          link.style.opacity = "0";
          link.style.transform = "translateY(-4px)";
        });
      }
      animations.push(
        animate(panel, {
          height: expanded ? panel.scrollHeight : 0,
          marginTop: expanded ? 5 : 0,
          marginBottom: expanded ? 5 : 0,
          duration: expanded ? 270 : 210,
          ease: "outCubic",
          onComplete: settle,
        }),
        animate(chevron, {
          rotate: expanded ? 180 : 0,
          duration: 220,
          ease: "outCubic",
        }),
        animate(links, {
          opacity: expanded ? 1 : 0,
          translateY: expanded ? 0 : -2,
          duration: expanded ? 180 : 120,
          delay: expanded ? stagger(24, { start: 35 }) : 0,
          ease: "outCubic",
        }),
      );
    }
    const onPreferenceChange = () => {
      animations.forEach((animation) => animation.cancel());
      settle();
    };
    preference.addEventListener("change", onPreferenceChange);
    return () => {
      animations.forEach((animation) => animation.cancel());
      preference.removeEventListener("change", onPreferenceChange);
    };
  }, [expanded]);

  return (
    <div className="nav-group">
      <button
        className={`nav-item nav-group-toggle ${active ? "nav-active" : ""}`}
        aria-expanded={expanded}
        aria-controls={groupId}
        onClick={onToggle}
      >
        <item.icon size={20} />
        <span>{item.name}</span>
        <span className="nav-chevron" ref={chevronRef} aria-hidden="true">
          <ChevronDown size={16} />
        </span>
      </button>
      <div
        id={groupId}
        className="nav-dropdown"
        ref={panelRef}
        inert={!expanded}
        aria-hidden={!expanded}
      >
        <ul className="nav-children">
          {item.children?.map((child) => {
            const current = active && selected === child.value;
            return (
              <li key={child.value}>
                <NavLink
                  to={`${item.path}?tab=${child.value}`}
                  onClick={onNavigate}
                  aria-current={current ? "page" : false}
                  tabIndex={expanded ? undefined : -1}
                  className={`nav-child ${current ? "nav-child-active" : ""}`}
                >
                  {child.name}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

export default function SidebarNavigation({
  items,
  onNavigate,
}: {
  items: NavigationItem[];
  onNavigate: () => void;
}) {
  const location = useLocation();
  const [expansion, setExpansion] = useState({
    locationKey: location.key,
    paths: [location.pathname],
  });
  if (expansion.locationKey !== location.key) {
    setExpansion({
      locationKey: location.key,
      paths: expansion.paths.includes(location.pathname)
        ? expansion.paths
        : [...expansion.paths, location.pathname],
    });
  }
  const params = new URLSearchParams(location.search);
  return (
    <nav aria-label="Main navigation">
      {items.map((item) => {
        const active = location.pathname === item.path;
        if (!item.children) {
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end
              onClick={onNavigate}
              className={({ isActive }) => `nav-item ${isActive ? "nav-active" : ""}`}
            >
              <item.icon size={20} />
              <span>{item.name}</span>
            </NavLink>
          );
        }
        const expanded = expansion.paths.includes(item.path);
        const selected = item.children.some((child) => child.value === params.get("tab"))
          ? params.get("tab")
          : item.children[0].value;
        return (
          <NavigationGroup
            key={item.path}
            item={item}
            active={active}
            expanded={expanded}
            selected={selected}
            onNavigate={onNavigate}
            onToggle={() => setExpansion((previous) => ({
                ...previous,
                paths: expanded
                  ? previous.paths.filter((path) => path !== item.path)
                  : [...previous.paths, item.path],
              }))}
          />
        );
      })}
    </nav>
  );
}
