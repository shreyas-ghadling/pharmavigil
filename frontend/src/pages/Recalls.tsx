import { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  const [batch, setBatch] = useState("");
  const [reason, setReason] = useState("");
  const [confirm, setConfirm] = useState(false);
  const cache = useQueryClient();
  const close = useCallback(() => setConfirm(false), []);
  const batches = useQuery({
    queryKey: ["recall-batches"],
    queryFn: () => api<Batch[]>("/batches"),
  });
  const recalls = useQuery({
    queryKey: ["recalls"],
    queryFn: () => api<Recall[]>("/recalls"),
  });
  const quarantine = useQuery({
    queryKey: ["quarantine"],
    queryFn: () => api<Quarantine[]>("/quarantine"),
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
        description="Take action on unsafe batches and trace affected hospital stock."
      />
      <Panel
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
      </Panel>
      <Panel
        title="Affected hospital stock"
        description="Recalled or expired units already delivered to partner hospitals."
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
              {
                title: "Units to quarantine",
                render: (q) => number(q.total_quarantine_units),
              },
              { title: "Contact", render: (q) => q.contact_phone },
            ]}
            empty="No recalled stock is currently recorded at partner hospitals."
          />
        )}
      </Panel>
      <Panel
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
      </Panel>
      {confirm ? (
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
