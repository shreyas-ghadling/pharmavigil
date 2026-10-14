import { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import {
  Badge,
  Drawer,
  Loading,
  Notice,
  number,
  PageTitle,
  Panel,
  Table,
} from "../components/ui";
import type { Batch, Quarantine, Recall } from "../types";
export default function Recalls() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  const stockView = params.get("tab") === "stock";
  const [batch, setBatch] = useState("");
  const [reason, setReason] = useState("");
  const [confirm, setConfirm] = useState(false);
  const cache = useQueryClient();
  const close = useCallback(() => setConfirm(false), []);
  const batches = useQuery({
    queryKey: ["recall-batches"],
    queryFn: () => api<Batch[]>("/batches"),
    enabled: !stockView,
  });
  const recalls = useQuery({
    queryKey: ["recalls"],
    queryFn: () => api<Recall[]>("/recalls"),
    enabled: !stockView,
  });
  const quarantine = useQuery({
    queryKey: ["quarantine"],
    queryFn: () => api<Quarantine[]>("/quarantine"),
    enabled: stockView,
  });
  const mutation = useMutation({
    mutationFn: () =>
      api<{ affected_hospitals: number; total_units_recalled: number }>(
        "/recalls",
        {
          method: "POST",
          body: JSON.stringify({ batch_number: batch, reason }),
        },
      ),
    onSuccess: () => {
      setConfirm(false);
      setBatch("");
      setReason("");
      for (const key of [
        "recalls",
        "quarantine",
        "recall-batches",
        "inventory",
        "overview",
        "batches",
        "dispatch-batches",
      ])
        void cache.invalidateQueries({ queryKey: [key] });
    },
  });
  return (
    <>
      <PageTitle
        title="Recalls"
        description="Record recall decisions and trace historical hospital deliveries."
      />
      {!stockView ? <Panel
        title="Initiate a batch recall"
        description="Recalling a batch blocks further dispatch and records an audit trail."
      >
        <form
          className="form-content"
          onSubmit={(e) => {
            e.preventDefault();
            setConfirm(true);
          }}
        >
          <div className="form-grid">
            <label>
              Batch to recall
              <select
                required
                value={batch}
                onChange={(e) => setBatch(e.target.value)}
              >
                <option value="">Select a batch</option>
                {batches.data
                  ?.filter((b) => b.recall_status !== "RECALLED")
                  .map((b) => (
                    <option key={b.batch_number} value={b.batch_number}>
                      {b.commercial_name} — {b.batch_number}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Reason for recall
              <input
                required
                minLength={5}
                maxLength={255}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Describe the safety concern"
              />
            </label>
          </div>
          {batches.error ? <Notice>{batches.error.message}</Notice> : null}
          {mutation.error ? <Notice>{mutation.error.message}</Notice> : null}
          {mutation.isSuccess ? (
            <Notice success>
              Recall recorded. {mutation.data.affected_hospitals} hospitals
              affected; {number(mutation.data.total_units_recalled)} units
              traced.
            </Notice>
          ) : null}
          <button className="danger" disabled={!batches.data?.length}>
            <ShieldAlert size={18} />
            Review recall
          </button>
        </form>
      </Panel> : null}
      {stockView ? <Panel
        title="Affected hospital deliveries"
        description="Historical deliveries of recalled or expired batches. These quantities are not verified remaining hospital stock."
      >
        {quarantine.isPending ? (
          <Loading />
        ) : quarantine.error ? (
          <Notice>{quarantine.error.message}</Notice>
        ) : (
          <Table
            rows={quarantine.data}
            rowKey={(q) => `${q.batch_number}-${q.hospital_name}`}
            columns={[
              {
                title: "Hospital",
                render: (q) => (
                  <>
                    <strong>{q.hospital_name}</strong>
                    <small>{q.city}</small>
                  </>
                ),
              },
              { title: "Medicine", render: (q) => q.commercial_name },
              { title: "Batch", render: (q) => q.batch_number },
              { title: "Reason flagged", render: (q) => <Badge value={q.affected_reason} /> },
              {
                title: "Historically delivered",
                render: (q) => `${number(q.historically_distributed_units)} ${q.stock_unit}s`,
              },
              { title: "Contact", render: (q) => q.contact_phone },
            ]}
            empty="No affected hospital deliveries are recorded."
          />
        )}
      </Panel> : null}
      {!stockView ? <Panel
        title="Recall history"
        description="A permanent record of recall decisions and their impact."
      >
        {recalls.isPending ? (
          <Loading />
        ) : recalls.error ? (
          <Notice>{recalls.error.message}</Notice>
        ) : (
          <Table
            rows={recalls.data}
            rowKey={(r) => String(r.audit_id)}
            columns={[
              {
                title: "Batch",
                render: (r) => (
                  <>
                    {r.batch_number}
                    <small>
                      <Badge value="RECALLED" />
                    </small>
                  </>
                ),
              },
              { title: "Reason", render: (r) => r.reason },
              { title: "Recorded by", render: (r) => r.recalled_by },
              {
                title: "Hospitals / units",
                render: (r) =>
                  `${r.affected_hospitals} / ${number(r.total_units_recalled)}`,
              },
              {
                title: "Date",
                render: (r) => new Date(r.recalled_at).toLocaleString(),
              },
            ]}
            empty="No recalls have been recorded."
          />
        )}
      </Panel> : null}
      {confirm && !stockView ? (
        <Drawer title="Confirm batch recall" onClose={close}>
          <div className="recall-confirm">
            <ShieldAlert size={38} />
            <h3>Recall {batch}?</h3>
            <p>
              This will block future dispatch and record the recall for all
              affected hospitals.
            </p>
            <div className="review-notes">
              <strong>Authorizing officer</strong>
              <p>{user?.full_name}</p>
              <strong>Reason</strong>
              <p>{reason}</p>
            </div>
            <p className="small muted">
              This action cannot be reversed from this workspace.
            </p>
            {mutation.error ? <Notice>{mutation.error.message}</Notice> : null}
            <div className="button-row">
              <button
                className="secondary"
                onClick={close}
                disabled={mutation.isPending}
              >
                Cancel
              </button>
              <button
                className="danger"
                disabled={mutation.isPending}
                onClick={() => mutation.mutate()}
              >
                {mutation.isPending ? "Recording recall…" : "Confirm recall"}
              </button>
            </div>
          </div>
        </Drawer>
      ) : null}
    </>
  );
}
