import { useState } from "react";
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
        const groupId = `nav-${item.path.slice(1)}`;
        return (
          <div className="nav-group" key={item.path}>
            <button
              className={`nav-item nav-group-toggle ${active ? "nav-active" : ""}`}
              aria-expanded={expanded}
              aria-controls={groupId}
              onClick={() => setExpansion((previous) => ({
                ...previous,
                paths: expanded
                  ? previous.paths.filter((path) => path !== item.path)
                  : [...previous.paths, item.path],
              }))}
            >
              <item.icon size={20} />
              <span>{item.name}</span>
              <ChevronDown size={16} className={`nav-chevron ${expanded ? "nav-chevron-open" : ""}`} />
            </button>
            <ul id={groupId} className="nav-children" hidden={!expanded}>
              {item.children.map((child) => {
                const current = active && selected === child.value;
                return (
                  <li key={child.value}>
                    <NavLink
                      to={`${item.path}?tab=${child.value}`}
                      onClick={onNavigate}
                      aria-current={current ? "page" : false}
                      className={`nav-child ${current ? "nav-child-active" : ""}`}
                    >
                      {child.name}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
