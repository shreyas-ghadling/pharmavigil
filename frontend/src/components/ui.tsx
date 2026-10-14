import { useEffect, useRef, type ReactNode } from "react";
import { animate } from "animejs";
import { AlertCircle, X, LoaderCircle, Inbox } from "lucide-react";
export const number = (v: number) => new Intl.NumberFormat("en-IN").format(v);
export const label = (v: string) =>
  v
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/^./, (c) => c.toUpperCase());
export function Notice({
  children,
  success = false,
}: {
  children: ReactNode;
  success?: boolean;
}) {
  return (
    <div
      role={success ? "status" : "alert"}
      className={`notice ${success ? "notice-success" : ""}`}
    >
      <AlertCircle size={18} />
      <span className="whitespace-pre-line">{children}</span>
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={22} /> Loading workspace…
    </div>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="empty">
      <Inbox size={32} />
      <p>{children}</p>
    </div>
  );
}
export function PageTitle({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Panel({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function ReviewPriorityBadge({ value }: { value: "URGENT" | "HIGH" | "ROUTINE" }) {
  const tone = value === "URGENT" ? "badge-red" : value === "HIGH" ? "badge-amber" : "badge-blue";
  const label = value === "URGENT" ? "Urgent review" : value === "HIGH" ? "Prioritized review" : "Routine review";
  return <span className={`badge ${tone}`}>{label}</span>;
}

export function Badge({ value }: { value: string }) {
  return (
    <span
      className={`badge ${["RECALLED", "CRITICAL", "EXPIRED"].includes(value) ? "badge-red" : ["HIGH", "WARNING", "UNDER_INVESTIGATION", "EXPIRING_SOON"].includes(value) ? "badge-amber" : "badge-green"}`}
    >
      {label(value)}
    </span>
  );
}
export function Stat({
  title,
  value,
  detail,
  icon,
}: {
  title: string;
  value: string | number;
  detail: string;
  icon: ReactNode;
}) {
  return (
    <div className="stat">
      <div className="stat-icon">{icon}</div>
      <p>{title}</p>
      <strong>{typeof value === "number" ? number(value) : value}</strong>
      <small>{detail}</small>
    </div>
  );
}
export interface Column<T> {
  title: string;
  render: (row: T) => ReactNode;
}
export function Table<T>({
  rows,
  columns,
  rowKey,
  empty = "No records match your selection.",
}: {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  empty?: string;
}) {
  return rows.length ? (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.title}>{c.title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c) => (
                <td key={c.title}>{c.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty>{empty}</Empty>
  );
}
export function Drawer({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const focused = document.activeElement as HTMLElement | null;
    const el = ref.current;
    el?.focus();
    const animation = window.matchMedia("(prefers-reduced-motion: reduce)")
      .matches
      ? null
      : animate(el!, { translateX: [28, 0], opacity: [0, 1], duration: 200 });
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && el) {
        const items = Array.from(
          el.querySelectorAll<HTMLElement>(
            'button,input,select,textarea,a[href],[tabindex="0"]',
          ),
        ).filter((x) => !x.hasAttribute("disabled"));
        const first = items[0],
          last = items.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      animation?.revert();
      document.removeEventListener("keydown", key);
      focused?.focus();
    };
  }, [onClose]);
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div
        ref={ref}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="panel-heading">
          <h2>{title}</h2>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close panel"
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
