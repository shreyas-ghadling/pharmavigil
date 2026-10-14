import { useState } from "react";
import { Download, FileText, Table2 } from "lucide-react";
import { download } from "../api";
import { Notice, PageTitle } from "../components/ui";
import AnimatedGroup from "../components/AnimatedGroup";
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
        description="Download recall decisions and historical distribution records."
      />
      {error ? <Notice>{error}</Notice> : null}
      {success ? <Notice success>{success}</Notice> : null}
      <AnimatedGroup className="export-grid">
        {[
          {
            kind: "pdf",
            title: "Safety audit manifest",
            description:
              "A paginated PDF containing complete recall reasons, historical affected-batch deliveries, and affected central balances.",
            icon: FileText,
            label: "Download PDF",
          },
          {
            kind: "csv",
            title: "Affected-delivery manifest",
            description:
              "A CSV with separate rows for recall initiations, historical hospital deliveries, and affected central balances.",
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
      </AnimatedGroup>
      <p className="small muted">
        Downloads reflect the data available at the time of generation.
        CSV record_type identifies each row. Batch totals appear only on recall initiation rows.
        Delivery quantities and central balances are separate measures. Compare quantities only within the same stock unit.
        Blank cells mean not recorded or not applicable to that row, rather than zero or a confirmed outcome.
      </p>
    </>
  );
}
