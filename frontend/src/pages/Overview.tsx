import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  ClipboardPlus,
  Package,
  ShieldAlert,
  Truck,
} from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import {
  ReviewPriorityBadge,
  Empty,
  Loading,
  Notice,
  number,
  PageTitle,
  Panel,
  Stat,
} from "../components/ui";
import type { Overview as OverviewData } from "../types";
export default function Overview() {
  const { user } = useAuth();
  const q = useQuery({
    queryKey: ["overview"],
    queryFn: () => api<OverviewData>("/overview"),
  });
  const doctor = user!.role === "DOCTOR_PATIENT";
  const admin = user!.role === "SAFETY_OFFICER_ADMIN";
  if (q.isPending) return <Loading />;
  if (q.error) return <Notice>{q.error.message}</Notice>;
  const data = q.data;
  const stock = data.inventory;
  const expiring = stock.filter(
    (b) =>
      b.days_left >= 0 && b.days_left <= 30 && b.recall_status === "ACTIVE",
  );
  return (
    <>
      <PageTitle
        title="Overview"
        description={`Welcome back, ${user!.full_name}. Here’s your medicine safety workspace.`}
      />
      {data.warnings.map((w) => (
        <Notice key={w}>{w}</Notice>
      ))}
      {doctor ? (
        <section className="report-intro panel">
          <div className="intro-icon">
            <ClipboardPlus size={36} />
          </div>
          <h2>Report a suspected reaction</h2>
          <p>
            Record the medicine, patient details, and observed symptoms. A clear
            report helps the safety team identify emerging risks.
          </p>
          <Link className="primary" to="/adverse-reports">
            Start a report
            <ArrowRight size={18} />
          </Link>
          <div className="intro-steps">
            <span>1. Identify medication</span>
            <span>2. Describe symptoms</span>
            <span>3. Review and submit</span>
          </div>
        </section>
      ) : (
        <>
          <div className="stats-grid">
            <Stat
              title="Stock on hand"
              value={stock.reduce((n, b) => n + Number(b.current_stock), 0)}
              detail="Units across all batches"
              icon={<Package size={22} />}
            />
            <Stat
              title="Registered batches"
              value={stock.length}
              detail="Inventory records"
              icon={<Truck size={22} />}
            />
            <Stat
              title="Expiring soon"
              value={expiring.length}
              detail="Within the next 30 days"
              icon={<ShieldAlert size={22} />}
            />
            <Stat
              title={admin ? "Patterns for review" : "Units distributed"}
              value={
                admin
                  ? data.signals.length
                  : stock.reduce(
                      (n, b) => n + Number(b.total_distributed_units),
                      0,
                    )
              }
              detail={
                admin
                  ? "At default review thresholds"
                  : "Delivered to partner hospitals"
              }
              icon={<Activity size={22} />}
            />
          </div>
          <div className="overview-grid">
            <Panel
              title={admin ? "Reported patterns" : "Expiry watch"}
              description={
                admin
                  ? "Prioritize reported patterns for investigation."
                  : "Review batches nearing their expiry date."
              }
              action={
                <Link
                  className="text-link"
                  to={admin ? "/safety" : "/inventory"}
                >
                  View all
                  <ArrowRight size={16} />
                </Link>
              }
            >
              {admin ? (
                data.signals.length ? (
                  data.signals.slice(0, 4).map((s) => (
                    <div
                      className="list-row"
                      key={`${s.medicine}-${s.symptom}`}
                    >
                      <div className="list-icon">
                        <Activity size={19} />
                      </div>
                      <div className="grow">
                        <strong>{s.medicine}</strong>
                        <p>
                          {s.symptom} · {s.incident_count} report entries
                        </p>
                      </div>
                      <ReviewPriorityBadge value={s.review_priority} />
                    </div>
                  ))
                ) : (
                  <Empty>No patterns meet the current review thresholds.</Empty>
                )
              ) : expiring.length ? (
                expiring.slice(0, 5).map((b) => (
                  <div className="list-row" key={b.batch_number}>
                    <div className="grow">
                      <strong>{b.commercial_name}</strong>
                      <p>{b.batch_number}</p>
                    </div>
                    <span className="badge badge-amber">
                      {b.days_left} days left
                    </span>
                  </div>
                ))
              ) : (
                <Empty>No active batches expire within 30 days.</Empty>
              )}
            </Panel>
            <Panel
              title="Quick actions"
              description="Go directly to your next task."
            >
              <div className="quick-actions">
                <Link to="/inventory">
                  <Package />
                  <div>
                    <strong>Manage inventory</strong>
                    <p>Search stock, import batches, or dispatch supplies.</p>
                  </div>
                  <ArrowRight size={18} />
                </Link>
                {admin ? (
                  <>
                    <Link to="/adverse-reports">
                      <ClipboardPlus />
                      <div>
                        <strong>Report a reaction</strong>
                        <p>Capture a suspected adverse event.</p>
                      </div>
                      <ArrowRight size={18} />
                    </Link>
                    <Link to="/recalls">
                      <ShieldAlert />
                      <div>
                        <strong>Review recalls</strong>
                        <p>
                          {number(data.recalls.length)} recorded recalls. Trace
                          affected stock.
                        </p>
                      </div>
                      <ArrowRight size={18} />
                    </Link>
                  </>
                ) : (
                  <Link to="/inventory?tab=dispatch">
                    <Truck />
                    <div>
                      <strong>Dispatch stock</strong>
                      <p>Deliver an eligible batch to a partner hospital.</p>
                    </div>
                    <ArrowRight size={18} />
                  </Link>
                )}
              </div>
            </Panel>
          </div>
        </>
      )}
    </>
  );
}
