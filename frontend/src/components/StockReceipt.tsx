import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api";
import type { Batch } from "../types";
import { Notice, Panel } from "./ui";

export default function StockReceipt() {
  const cache = useQueryClient();
  const [batch, setBatch] = useState("");
  const batches = useQuery({ queryKey: ["receipt-batches"], queryFn: () => api<Batch[]>("/batches") });
  const mutation = useMutation({ mutationFn: (body: object) => api<{message:string}>("/inventory/receipts", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => { void cache.invalidateQueries({queryKey:["inventory"]}); void cache.invalidateQueries({queryKey:["overview"]}); } });
  return <Panel title="Receive stock" description="Record delivered quantities separately from batch production capacity.">
    <form className="form-content" onSubmit={(e) => { e.preventDefault(); const form = new FormData(e.currentTarget);
      mutation.mutate({ batch_number: form.get("batch"), quantity: Number(form.get("quantity")), receipt_date: form.get("date"), reference: form.get("reference") }); }}>
      <div className="form-grid">
        <label>Registered batch<select name="batch" required value={batch} onChange={(e) => setBatch(e.target.value)}><option value="">Select a batch</option>{batches.data?.map((b) => <option value={b.batch_number} key={b.batch_number}>{b.commercial_name} · {b.batch_number} ({b.stock_unit})</option>)}</select></label>
        <label>Quantity received ({batches.data?.find((b) => b.batch_number === batch)?.stock_unit ?? "select a batch"})<input required name="quantity" type="number" min={1} max={1000000} /></label>
        <label>Receipt date<input required name="date" type="date" max={new Date().toLocaleDateString("en-CA")} /></label>
        <label>Receipt reference<input required name="reference" minLength={3} maxLength={100} placeholder="Delivery note or shipment reference" /></label>
      </div>
      <p className="small muted">A batch can have several receipts. Reuse the same reference when retrying the same receipt.</p>
      {batches.error ? <Notice>{batches.error.message}</Notice> : null}
      {mutation.error ? <Notice>{mutation.error.message}</Notice> : null}
      {mutation.data ? <Notice success>{mutation.data.message}</Notice> : null}
      <button className="primary" disabled={mutation.isPending || !batches.data?.length}>Record receipt</button>
    </form>
  </Panel>;
}
