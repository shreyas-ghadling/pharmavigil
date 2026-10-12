import { useState } from "react";
import { Download, FileText, Table2 } from "lucide-react";
import { download } from "../api";
import { Notice, PageTitle } from "../components/ui";
export default function Exports() {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  async function get(kind: string) {
    setBusy(kind);
    setError("");
    setSuccess("");
    try {
      await download(
        kind === "pdf" ? "/exports/audit.pdf" : "/exports/quarantine.csv",
        kind === "pdf"
          ? "Safety_Audit_Recall_Manifest.pdf"
          : "quarantine_manifest.csv",
      );
      setSuccess("Your report has been downloaded.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  return (
    <>
      <PageTitle
        title="Reports & exports"
        description="Download the latest recall audit and affected-stock records."
      />
      {error ? <Notice>{error}</Notice> : null}
      {success ? <Notice success>{success}</Notice> : null}
      <div className="export-grid">
        {[
          {
            kind: "pdf",
            title: "Safety audit manifest",
            description:
              "A formal PDF containing recall decisions and affected hospital stock.",
            icon: FileText,
            label: "Download PDF",
          },
          {
            kind: "csv",
            title: "Quarantine stock manifest",
            description:
              "A CSV of affected batches, recall reasons, hospitals, contacts, and quantities.",
            icon: Table2,
            label: "Download CSV",
          },
        ].map((x) => (
          <section className="export-card panel" key={x.kind}>
            <div className="export-icon">
              <x.icon size={32} />
            </div>
            <span className="badge badge-blue">{x.kind.toUpperCase()}</span>
            <h2>{x.title}</h2>
            <p>{x.description}</p>
            <ul>
              <li>Generated from current database records</li>
              <li>Includes recall history and distribution tracing</li>
            </ul>
            <button
              className="primary"
              disabled={!!busy}
              onClick={() => get(x.kind)}
            >
              <Download size={18} />
              {busy === x.kind ? "Generating…" : x.label}
            </button>
          </section>
        ))}
      </div>
      <p className="small muted">
        Downloads reflect the data available at the time of generation.
      </p>
    </>
  );
}
