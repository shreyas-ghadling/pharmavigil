import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { ClinicalReport } from "../types";
import { Empty, Loading, Notice, Panel } from "./ui";

function CaseReviewItem({ report }: { report: ClinicalReport }) {
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("REVIEWED");
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => api("/case-reviews", { method: "POST", body: JSON.stringify({ report_id: report.report_id, notes, status }) }),
    onSuccess: () => { void cache.invalidateQueries({ queryKey: ["case-reviews"] }); },
  });
  return <details className="clinical-result">
    <summary><strong>{report.medicine_name}</strong><span>{report.report_id} · {report.review?.status === "FOLLOW_UP" ? "Follow-up needed" : "Needs review"}</span></summary>
    <p>{report.seriousness_criteria?.length ? `Reported serious outcomes: ${report.seriousness_criteria.join(", ").replaceAll("_", " ").toLowerCase()}` : "Legacy symptom flag: seriousness needs assessment."}</p>
    <p>Intensity {report.severity_score}/5 · Batch {report.batch_number ?? "unknown"}</p>
    <p>{report.symptoms?.map((s) => `${s.name} (${s.onset_minutes == null ? "onset unknown" : `${s.onset_minutes} minutes after use`})`).join("; ")}</p>
    <p>{report.clinical_notes || "No clinical notes recorded."}</p>
    {report.review ? <p>Previous review: {report.review.notes}</p> : null}
    <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
      <label>Review outcome<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="REVIEWED">Reviewed</option><option value="FOLLOW_UP">Follow-up needed</option></select></label>
      <label>Review notes<textarea required minLength={5} maxLength={1000} value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
      {mutation.error ? <Notice>{mutation.error.message}</Notice> : null}
      <button className="primary" disabled={mutation.isPending}>Save case review</button>
    </form>
  </details>;
}

export default function CaseReviews() {
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["case-reviews", page], queryFn: () => api<{ items: ClinicalReport[]; total: number }>(`/case-reviews?page=${page}`) });
  return <Panel title="Individual case reviews" description="Reported serious outcomes and legacy flags are reviewed individually, independently of pattern thresholds.">
    {query.isPending ? <Loading /> : query.error ? <Notice>{query.error.message}</Notice> : <>
      <p>{query.data.total} reports awaiting review or follow-up. Marking a case reviewed records your assessment; it does not establish medicine safety.</p>
      {query.data.items.length ? query.data.items.map((r) => <CaseReviewItem report={r} key={r.report_id} />) : <Empty>No reports on this page require review.</Empty>}
      <div className="button-row"><button className="secondary" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Previous</button><span>Page {page}</span><button className="secondary" disabled={page * 25 >= query.data.total} onClick={() => setPage((p) => p + 1)}>Next</button></div>
    </>}
  </Panel>;
}
