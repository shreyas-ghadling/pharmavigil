import { lazy, Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, Search } from "lucide-react";
import { api } from "../api";
import {
  Badge,
  Empty,
  Loading,
  Notice,
  PageTitle,
  Panel,
} from "../components/ui";
import type { ClinicalReport, Signal } from "../types";
const SignalChart = lazy(() => import("../components/SignalChart"));
export default function Safety() {
  const [severity, setSeverity] = useState(3);
  const [frequency, setFrequency] = useState(2);
  const [q, setQ] = useState("");
  const [search, setSearch] = useState<string | null>(null);
  const signals = useQuery({
    queryKey: ["signals", severity, frequency],
    queryFn: () =>
      api<Signal[]>(
        `/signals?min_severity=${severity}&min_incidents=${frequency}`,
      ),
  });
  const clinical = useQuery({
    queryKey: ["clinical-search", search],
    queryFn: () =>
      api<ClinicalReport[]>(
        `/clinical-search?q=${encodeURIComponent(search ?? "")}`,
      ),
    enabled: search !== null,
  });
  return (
    <>
      <PageTitle
        title="Safety monitoring"
        description="Identify emerging reactions and investigate clinical observations."
      />
      <Panel
        title="Signal detection"
        description="Adjust thresholds to focus the safety review."
      >
        <div className="filter-grid">
          <label>
            Minimum severity: {severity}/5
            <input
              type="range"
              min="1"
              max="5"
              value={severity}
              onChange={(e) => setSeverity(Number(e.target.value))}
            />
          </label>
          <label>
            Minimum incidents: {frequency}
            <input
              type="range"
              min="1"
              max="10"
              value={frequency}
              onChange={(e) => setFrequency(Number(e.target.value))}
            />
          </label>
        </div>
        {signals.isPending ? (
          <Loading />
        ) : signals.error ? (
          <Notice>{signals.error.message}</Notice>
        ) : signals.data.length ? (
          <>
            <div className="signal-grid">
              {signals.data.map((s) => (
                <article
                  className="signal-card"
                  key={`${s.medicine}-${s.symptom}`}
                >
                  <div className="signal-top">
                    <span className="list-icon">
                      <Activity size={19} />
                    </span>
                    <Badge value={s.risk_level} />
                  </div>
                  <h3>{s.medicine}</h3>
                  <p>{s.symptom}</p>
                  <div className="signal-numbers">
                    <div>
                      <strong>{s.signal_risk_score}</strong>
                      <span>Risk score</span>
                    </div>
                    <div>
                      <strong>{s.incident_count}</strong>
                      <span>Incidents</span>
                    </div>
                    <div>
                      <strong>{s.avg_severity}</strong>
                      <span>Avg. severity</span>
                    </div>
                  </div>
                  <small>{s.critical_cases} critical cases</small>
                  <details>
                    <summary>Review recommendation</summary>
                    <p>{s.recommendation}</p>
                  </details>
                </article>
              ))}
            </div>
            <div className="chart-heading">
              <h3>Risk score by medicine and symptom</h3>
              <p>Relative scores help prioritize investigation.</p>
            </div>
            <Suspense fallback={<Loading />}>
              <SignalChart signals={signals.data} />
            </Suspense>
          </>
        ) : (
          <Empty>
            No signals exceed these thresholds. Adjust the filters to broaden
            your review.
          </Empty>
        )}
      </Panel>
      <Panel
        title="Search clinical notes"
        description="Find reports by symptoms or terms in the clinical narrative."
      >
        <form
          className="table-toolbar"
          onSubmit={(e) => {
            e.preventDefault();
            setSearch(q);
          }}
        >
          <label className="search-input">
            <Search size={18} />
            <input
              aria-label="Clinical search terms"
              maxLength={200}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Try hypotension, dizziness, or arrhythmia"
            />
          </label>
          <button className="primary">Search notes</button>
        </form>
        {clinical.isFetching ? (
          <Loading />
        ) : clinical.error ? (
          <Notice>{clinical.error.message}</Notice>
        ) : clinical.data?.length ? (
          clinical.data.map((r) => (
            <details className="clinical-result" key={r.report_id}>
              <summary>
                <strong>{r.medicine_name}</strong>
                <span>
                  {r.report_id} · Severity {r.severity_score}/5
                </span>
              </summary>
              <p>{r.clinical_notes || "No clinical notes provided."}</p>
              <small>
                Batch {r.batch_number} · Reported {r.reported_at}
              </small>
            </details>
          ))
        ) : search !== null ? (
          <Empty>
            No reports match your search. Try a different symptom or keyword.
          </Empty>
        ) : (
          <div className="search-hint">
            Enter a term to search, or leave it empty to review recent reports.
          </div>
        )}
      </Panel>
    </>
  );
}
