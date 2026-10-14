import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { Signal } from "../types";
import { Notice } from "./ui";
import AnimatedDisclosure from "./AnimatedDisclosure";

export default function PatternReview({ signal, days }: { signal: Signal; days: number }) {
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("REVIEWED");
  const cache = useQueryClient();
  const mutation = useMutation({ mutationFn: () => api("/signal-reviews", { method: "POST", body: JSON.stringify({ medicine_key: signal.medicine_key, symptom: signal.symptom, window_days: days, revision: signal.revision, status, notes }) }),
    onSuccess: () => { void cache.invalidateQueries({ queryKey: ["signals"] }); void cache.invalidateQueries({ queryKey: ["overview"] }); } });
  return <AnimatedDisclosure summary="Record pattern review">
    <p>{signal.review_status.replaceAll("_", " ").toLowerCase()}</p>
    {signal.review ? <p>Previous assessment: {signal.review.notes} · {signal.review.reviewed_at}</p> : null}
    <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
      <label>Pattern review status<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="REVIEWED">Reviewed</option><option value="CLOSED">Review closed</option></select></label>
      <label>Assessment notes<textarea minLength={5} maxLength={1000} required value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
      <p className="small muted">New reports reopen this pattern for review. Closing a review does not certify medicine safety.</p>
      {mutation.error ? <Notice>{mutation.error.message}</Notice> : null}
      <button className="secondary" disabled={mutation.isPending}>Save pattern review</button>
    </form>
  </AnimatedDisclosure>;
}
