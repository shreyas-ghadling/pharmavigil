import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Package, Search, Truck, Upload, Eye } from "lucide-react";
import { api, download } from "../api";
import {
  Badge,
  Drawer,
  Loading,
  Notice,
  number,
  PageTitle,
  Panel,
  Stat,
  Table,
} from "../components/ui";
import type { Batch, Hospital, Stock } from "../types";
import StockReceipt from "../components/StockReceipt";
export default function Inventory() {
  const [params] = useSearchParams();
  const requestedTab = params.get("tab");
  const tab = requestedTab === "import" || requestedTab === "dispatch" || requestedTab === "receive" ? requestedTab : "stock";
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [selected, setSelected] = useState<Stock | null>(null);
  const [error, setError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dispatchBatch, setDispatchBatch] = useState("");
  const cache = useQueryClient();
  const stock = useQuery({
    queryKey: ["inventory"],
    queryFn: () => api<Stock[]>("/inventory"),
  });
  const batches = useQuery({
    queryKey: ["dispatch-batches"],
    queryFn: () => api<Batch[]>("/batches?only_active=true"),
    enabled: tab === "dispatch",
  });
  const hospitals = useQuery({
    queryKey: ["hospitals"],
    queryFn: () => api<Hospital[]>("/hospitals"),
    enabled: tab === "dispatch",
  });
  const invalidate = () => {
    void cache.invalidateQueries({ queryKey: ["inventory"] });
    void cache.invalidateQueries({ queryKey: ["overview"] });
    void cache.invalidateQueries({ queryKey: ["dispatch-batches"] });
    void cache.invalidateQueries({ queryKey: ["batches"] });
  };
  const intake = useMutation({
    mutationFn: (shipment?: File) => {
      const d = new FormData();
      d.append("file", shipment ?? file!);
      return api<{ count: number }>("/inventory/import", {
        method: "POST",
        body: d,
      });
    },
    onSuccess: invalidate,
  });
  const sampleIntake = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/exports/sample.csv", {
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error("Unable to load the sample CSV.");
      const shipment = new File([await response.blob()], "sample_batches.csv", {
        type: "text/csv",
      });
      setFile(shipment);
      return intake.mutateAsync(shipment);
    },
  });
  const dispatch = useMutation({
    mutationFn: (body: object) =>
      api<{ message: string }>("/inventory/dispatch", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: invalidate,
  });
  const close = useCallback(() => setSelected(null), []);
  const rows = stock.data ?? [];
  const filtered = rows.filter(
    (b) =>
      (status === "all" || b.recall_status === status) &&
      `${b.commercial_name} ${b.batch_number} ${b.manufacturer_name} ${b.recall_status}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <PageTitle
        title="Inventory"
        description="Track medicine batches, receive shipments, and dispatch eligible stock."
      />
      <div className="stats-grid">
        <Stat
          title="Batches with available stock"
          value={rows.filter((b) => b.recall_status === "ACTIVE" && Number(b.current_stock) > 0).length}
          detail="Quantities shown per batch and stock unit"
          icon={<Package />}
        />
        <Stat
          title="Batches"
          value={rows.length}
          detail="All inventory records"
          icon={<Package />}
        />
        <Stat
          title="Expiring soon"
          value={
            rows.filter(
              (b) =>
                b.days_left >= 0 &&
                b.days_left <= 30 &&
                b.recall_status === "ACTIVE",
            ).length
          }
          detail="Within 30 days"
          icon={<Truck />}
        />
        <Stat
          title="Recalled batches"
          value={rows.filter((b) => b.recall_status === "RECALLED").length}
          detail="Blocked from dispatch"
          icon={<Package />}
        />
      </div>
      {error ? <Notice>{error}</Notice> : null}
      {tab === "stock" ? (
        <Panel
          title="Medicine batches"
          description="Search and review stock status before making a dispatch."
        >
          <div className="table-toolbar">
            <label className="search-input">
              <Search size={18} />
              <input
                aria-label="Search batches"
                placeholder="Search medicine, batch, or manufacturer"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
            <select
              aria-label="Filter stock status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="all">All statuses</option>
              {["ACTIVE", "EXPIRED", "RECALLED", "UNDER_INVESTIGATION"].map(
                (s) => (
                  <option key={s} value={s}>
                    {s.replaceAll("_", " ").toLowerCase()}
                  </option>
                ),
              )}
            </select>
          </div>
          {stock.isPending ? (
            <Loading />
          ) : stock.error ? (
            <Notice>{stock.error.message}</Notice>
          ) : (
            <Table
              rows={filtered}
              rowKey={(b) => b.batch_number}
              columns={[
                {
                  title: "Medicine",
                  render: (b) => (
                    <>
                      <strong>{b.commercial_name}</strong>
                      <small>
                        {b.generic_name} · {b.strength}
                      </small>
                    </>
                  ),
                },
                { title: "Batch", render: (b) => b.batch_number },
                {
                  title: "Stock",
                  render: (b) => (
                    <>
                      {number(b.current_stock)} {b.stock_unit}s
                      <small>{number(b.total_received_units)} recorded as received</small>
                    </>
                  ),
                },
                {
                  title: "Expiry",
                  render: (b) => (
                    <>
                      {b.expiry_date}
                      <small>
                        {b.days_left < 0
                          ? "Expired"
                          : `${b.days_left} days remaining`}
                      </small>
                    </>
                  ),
                },
                {
                  title: "Status",
                  render: (b) => <Badge value={b.recall_status} />,
                },
                {
                  title: "Details",
                  render: (b) => (
                    <button
                      className="icon-button"
                      aria-label={`View ${b.batch_number}`}
                      onClick={() => setSelected(b)}
                    >
                      <Eye size={18} />
                    </button>
                  ),
                },
              ]}
              empty="No batches found. Adjust your search or import a shipment."
            />
          )}
        </Panel>
      ) : tab === "import" ? (
        <Panel
          title="Register production batches"
          description="Upload a CSV to register batches. Registration does not add received stock."
        >
          <div className="form-content">
            <div className="upload-box">
              <Upload size={34} />
              <h3>Select your batch-registration CSV</h3>
              <p>UTF-8 CSV · Maximum 2 MB</p>
              <input
                aria-label="Shipment CSV"
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  intake.reset();
                }}
              />
            </div>
            <div className="import-note">
              <p>
                Required columns: batch_number, medicine_id, manufacturing_date,
                expiry_date, total_units_produced. recall_status is optional.
              </p>
              <p>If any row is invalid or duplicated, nothing is saved.</p>
              <button
                className="secondary"
                onClick={() =>
                  download("/exports/sample.csv", "sample_batches.csv").catch(
                    (e) => setError(e.message),
                  )
                }
              >
                <Download size={17} />
                Download sample CSV
              </button>
              <button
                className="secondary"
                disabled={intake.isPending || sampleIntake.isPending}
                onClick={() => sampleIntake.mutate()}
              >
                <Upload size={17} />
                {sampleIntake.isPending ? "Importing sample…" : "Import sample CSV"}
              </button>
            </div>
            {file ? <p>Selected file: {file.name}</p> : null}
            {sampleIntake.error && !intake.error ? (
              <Notice>{sampleIntake.error.message}</Notice>
            ) : null}
            {intake.error ? <Notice>{intake.error.message}</Notice> : null}
            {intake.isSuccess ? (
              <Notice success>
                {intake.data.count} batches imported successfully.
              </Notice>
            ) : null}
            <button
              className="primary"
              disabled={!file || intake.isPending || sampleIntake.isPending}
              onClick={() => intake.mutate()}
            >
              <Upload size={18} />
              {intake.isPending ? "Importing…" : "Import batches"}
            </button>
          </div>
        </Panel>
      ) : tab === "receive" ? <StockReceipt /> : (
        <Panel
          title="Dispatch stock"
          description="Send an active batch to a registered hospital."
        >
          <form
            className="form-content"
            onSubmit={(e) => {
              e.preventDefault();
              const d = new FormData(e.currentTarget);
              dispatch.mutate({
                batch_number: d.get("batch"),
                hospital_id: Number(d.get("hospital")),
                quantity: Number(d.get("quantity")),
                dispatch_date: d.get("date"),
              });
            }}
          >
            <div className="form-grid">
              <label>
                Eligible batch
                <select name="batch" required value={dispatchBatch} onChange={(e) => setDispatchBatch(e.target.value)}>
                  <option value="">Select an active batch</option>
                  {batches.data?.map((b) => (
                    <option value={b.batch_number} key={b.batch_number}>
                      {b.commercial_name} — {b.batch_number} ({b.stock_unit})
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Destination hospital
                <select name="hospital" required>
                  <option value="">Select a hospital</option>
                  {hospitals.data?.map((h) => (
                    <option value={h.hospital_id} key={h.hospital_id}>
                      {h.hospital_name} — {h.city}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Quantity ({batches.data?.find((b) => b.batch_number === dispatchBatch)?.stock_unit ?? "select a batch"})
                <input
                  type="number"
                  name="quantity"
                  min="1"
                  max="100000"
                  required
                  defaultValue="100"
                />
              </label>
              <label>
                Dispatch date
                <input
                  type="date"
                  name="date"
                  required
                  defaultValue={new Date().toLocaleDateString("en-CA")}
                />
              </label>
            </div>
            {batches.error ? <Notice>{batches.error.message}</Notice> : null}
            {hospitals.error ? (
              <Notice>{hospitals.error.message}</Notice>
            ) : null}
            {dispatch.error ? <Notice>{dispatch.error.message}</Notice> : null}
            {dispatch.isSuccess ? (
              <Notice success>{dispatch.data.message}</Notice>
            ) : null}
            <p className="small muted">
              Expired, recalled, and investigated batches are blocked by server
              validation.
            </p>
            <button
              className="primary"
              disabled={
                dispatch.isPending ||
                !batches.data?.length ||
                !hospitals.data?.length
              }
            >
              <Truck size={18} />
              {dispatch.isPending ? "Dispatching…" : "Confirm dispatch"}
            </button>
          </form>
        </Panel>
      )}
      {selected ? (
        <Drawer title="Batch details" onClose={close}>
          <h3 className="detail-title">{selected.commercial_name}</h3>
          <Badge value={selected.recall_status} />
          <dl className="detail-list">
            {Object.entries({
              Batch: selected.batch_number,
              Manufacturer: selected.manufacturer_name,
              Formulation: `${selected.generic_name} ${selected.strength}`,
              "Dosage form": selected.dosage_form,
              "Stock unit": selected.stock_unit,
              "Manufactured on": selected.manufacturing_date,
              "Expires on": selected.expiry_date,
              "Units produced": number(selected.total_units_produced),
              "Recorded receipts": number(selected.total_received_units),
              "Units distributed": number(selected.total_distributed_units),
              "Current stock": number(selected.current_stock),
            }).map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
          {selected.has_inferred_opening_balance ? <Notice>This batch includes an inferred legacy opening balance. It preserves earlier records and is not a verified physical receipt.</Notice> : null}
        </Drawer>
      ) : null}
    </>
  );
}
