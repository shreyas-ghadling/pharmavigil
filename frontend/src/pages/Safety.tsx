import { lazy, Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Activity, Search } from "lucide-react";
import { api } from "../api";
import {
  ReviewPriorityBadge,
  Empty,
  Loading,
  Notice,
  PageTitle,
  Panel,
} from "../components/ui";
import type { ClinicalReport, Signal } from "../types";
const SignalChart = lazy(() => import("../components/SignalChart"));
export default function Safety() {
  const [params] = useSearchParams();
  const clinicalView = params.get("tab") === "clinical";
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
    enabled: !clinicalView,
  });
  const clinical = useQuery({
    queryKey: ["clinical-search", search],
    queryFn: () =>
      api<ClinicalReport[]>(
        `/clinical-search?q=${encodeURIComponent(search ?? "")}`,
      ),
    enabled: clinicalView && search !== null,
  });
  return (
    <>
      <PageTitle
        title="Safety monitoring"
        description="Review reported patterns and investigate clinical observations."
      />
      {!clinicalView ? <Panel
        title="Signal detection"
        description="Screen reported patterns for further review."
      >
        <p className="small muted">Priority score = report entries × average intensity. This project heuristic does not estimate incidence, probability of harm, or establish causality. Review priorities use project thresholds: 12 or above for urgent review, 6 or above for prioritized review, otherwise routine review.</p>
        <div className="filter-grid">
          <label>
            Minimum average intensity: {severity}/5
            <input
              type="range"
              min="1"
              max="5"
              step="0.5"
              value={severity}
              onChange={(e) => setSeverity(Number(e.target.value))}
            />
          </label>
          <label>
            Minimum report entries: {frequency}
            <input
              type="range"
              min="1"
              max="10"
              value={frequency}
              onChange={(e) => setFrequency(Number(e.target.value))}
            />
          </label>
        </div>
        <p className="small muted">Counts and averages include all reports for each medicine and symptom, across the available history. Filters select completed groups and do not remove lower-intensity reports from their calculations.</p>
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
                    <ReviewPriorityBadge value={s.review_priority} />
                  </div>
                  <h3>{s.medicine}</h3>
                  <p>{s.symptom}</p>
                  <div className="signal-numbers">
                    <div>
                      <strong>{s.priority_score}</strong>
                      <span>Priority score</span>
                    </div>
                    <div>
                      <strong>{s.incident_count}</strong>
                      <span>Report entries</span>
                    </div>
                    <div>
                      <strong>{s.avg_severity}</strong>
                      <span>Avg. intensity</span>
                    </div>
                  </div>
                  <small>{s.reported_serious_cases} entries with reported serious outcomes</small>
                  {s.seriousness_unknown_entries ? <p className="small muted">Seriousness is unknown or unrecorded in {s.seriousness_unknown_entries} entries.</p> : null}
                  {s.critical_cases ? <p className="small muted">{s.critical_cases} legacy symptom flags; seriousness was not established by these flags.</p> : null}
                  <details>
                    <summary>Review recommendation</summary>
                    <p>{s.recommendation}</p>
                  </details>
                </article>
              ))}
            </div>
            <div className="chart-heading">
              <h3>Review priority score by medicine and symptom</h3>
              <p>Scores rank reported patterns for investigation.</p>
            </div>
            <Suspense fallback={<Loading />}>
              <SignalChart signals={signals.data} />
            </Suspense>
          </>
        ) : (
          <Empty>
            No reported patterns meet these thresholds. Adjust the filters to broaden
            your review.
          </Empty>
        )}
      </Panel> : null}
      {clinicalView ? <Panel
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
                  {r.report_id} · Intensity {r.severity_score}/5
                </span>
              </summary>
              <p>{r.clinical_notes || "No clinical notes provided."}</p>
              <small>
                Batch {r.batch_number ?? "unknown"} · Reported {r.reported_at}
              </small>
              <p>
                Declared reporting source: {r.reporter_type.replaceAll("_", " ").toLowerCase()} ·
                Patient age: {r.patient_demographics?.age ?? "Not recorded"}
              </p>
              <p>Submitted by: {r.submitted_by ? `${r.submitted_by.full_name} (${r.submitted_by.username})` : "Not recorded in this older report"}</p>
              <p>Serious outcomes: {r.seriousness_criteria == null ? "Not recorded or unknown"
                : r.seriousness_criteria.length ? r.seriousness_criteria.map((c) => c.replaceAll("_", " ").toLowerCase()).join(", ")
                : "None reported"}</p>
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
      </Panel> : null}
    </>
  );
}
