import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ClipboardPlus,
} from "lucide-react";
import { api } from "../api";
import { Loading, Notice, PageTitle, Panel } from "../components/ui";
import type { AdverseReport, Batch, Medicine, Hospital } from "../types";
const symptoms = [
  "Severe Dizziness",
  "Acute Hypotension",
  "Arrhythmia",
  "Tachycardia",
  "Bradycardia",
  "Paradoxical Bronchospasm",
  "Dyspnea",
  "Severe Hypoglycemia",
  "Anaphylaxis",
  "Seizure",
  "Nausea",
  "Vomiting",
  "Headache",
  "Skin Rash",
  "Facial Edema",
  "Tremors",
  "Somnolence",
];
const conditions = [
  "Hypertension",
  "Type 2 Diabetes",
  "Coronary Artery Disease",
  "Asthma",
  "COPD",
  "Chronic Kidney Disease",
  "Neuropathic Pain",
];
const seriousOutcomes = [
  ["DEATH", "Death"],
  ["LIFE_THREATENING", "Life-threatening at the time of the event"],
  ["HOSPITALIZATION", "Hospital admission or prolonged hospitalization"],
  ["DISABILITY", "Persistent or significant disability"],
  ["CONGENITAL_ANOMALY", "Congenital anomaly or birth defect"],
  ["MEDICALLY_IMPORTANT", "Other medically important event"],
] as const;
type ReportDraft = Omit<AdverseReport, "patient_demographics" | "symptoms" | "severity_score"> & {
  patient_demographics: {
    age: number | "";
    gender: string;
    pre_existing_conditions: string[];
  };
  symptoms: Array<{ name: string; onset_minutes: number | null | ""; is_critical: boolean }>;
  severity_score: number | "";
};
const initial: ReportDraft = {
  medicine_id: 0,
  medicine_name: "",
  batch_number: "",
  reporter_type: "",
  hospital_id: null,
  patient_demographics: {
    age: "",
    gender: "",
    pre_existing_conditions: [],
  },
  symptoms: [],
  severity_score: "",
  seriousness_criteria: null,
  clinical_notes: "",
};
export default function Reporting() {
  const [draft, setDraft] = useState<ReportDraft>(initial);
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [customSymptoms, setCustomSymptoms] = useState<string[]>([]);
  const [customConditions, setCustomConditions] = useState<string[]>([]);
  const [symptomName, setSymptomName] = useState("");
  const [conditionName, setConditionName] = useState("");
  const [seriousnessChoice, setSeriousnessChoice] = useState("");
  const cache = useQueryClient();
  const meds = useQuery({
    queryKey: ["medicines"],
    queryFn: () => api<Medicine[]>("/medicines"),
  });
  const hospitals = useQuery({
    queryKey: ["hospitals"],
    queryFn: () => api<Hospital[]>("/hospitals"),
  });
  const batches = useQuery({
    queryKey: ["batches", draft.medicine_id],
    queryFn: () =>
      api<Batch[]>(
        `/batches?medicine_id=${draft.medicine_id}`,
      ),
    enabled: !!draft.medicine_id && draft.batch_number !== null,
  });
  const submit = useMutation({
    mutationFn: () =>
      api<{ report_id: string }>("/adverse-reports", {
        method: "POST",
        body: JSON.stringify(draft),
      }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["overview"] });
      void cache.invalidateQueries({ queryKey: ["signals"] });
    },
  });
  const patch = (p: Partial<ReportDraft>) =>
    setDraft((d) => ({ ...d, ...p }));
  function addObservation(kind: "symptom" | "condition") {
    const entered = (kind === "symptom" ? symptomName : conditionName).trim().replace(/\s+/g, " ");
    if (entered.length < 2) {
      setError("Enter at least two characters for the observation.");
      return;
    }
    setError("");
    if (kind === "symptom") {
      const existing = [...symptoms, ...customSymptoms].find((s) => s.toLowerCase() === entered.toLowerCase());
      const name = existing ?? entered;
      if (!existing) setCustomSymptoms((items) => [...items, name]);
      if (!draft.symptoms.some((s) => s.name === name))
        patch({ symptoms: [...draft.symptoms, { name, onset_minutes: "", is_critical: false }] });
      setSymptomName("");
    } else {
      const existing = [...conditions, ...customConditions].find((c) => c.toLowerCase() === entered.toLowerCase());
      const name = existing ?? entered;
      if (!existing) setCustomConditions((items) => [...items, name]);
      if (!draft.patient_demographics.pre_existing_conditions.includes(name))
        patch({ patient_demographics: { ...draft.patient_demographics,
          pre_existing_conditions: [...draft.patient_demographics.pre_existing_conditions, name] } });
      setConditionName("");
    }
  }
  function next() {
    setError("");
    if (step === 0 && (!draft.medicine_id || !draft.reporter_type)) {
      setError("Choose the medicine and reporter type.");
      return;
    }
    if (
      step === 0 &&
      draft.batch_number !== null &&
      (!draft.batch_number ||
        !batches.data?.some((b) => b.batch_number === draft.batch_number))
    ) {
      setError("Choose a batch for this medicine.");
      return;
    }
    if (step === 1 && (draft.patient_demographics.age === "" || !draft.patient_demographics.gender)) {
      setError("Enter the patient's age and select a gender.");
      return;
    }
    if (step === 2 && (!draft.symptoms.length || draft.severity_score === "" || draft.symptoms.some((s) => s.onset_minutes === ""))) {
      setError("Select at least one symptom, enter its onset, and choose a severity.");
      return;
    }
    if (step === 2 && (!seriousnessChoice || (seriousnessChoice === "reported" && !draft.seriousness_criteria?.length))) {
      setError("Indicate whether serious outcomes are reported, absent, or unknown. Select any reported outcomes.");
      return;
    }
    setStep((s) => Math.min(3, s + 1));
  }
  if (meds.isPending) return <Loading />;
  if (meds.error) return <Notice>{meds.error.message}</Notice>;
  if (submit.isSuccess)
    return (
      <>
        <PageTitle
          title="Report submitted"
          description="Your observations have been recorded for safety monitoring."
        />
        <div className="success-card panel">
          <CheckCircle2 size={56} />
          <h2>Thank you for reporting</h2>
          <p>Keep this tracking ID for your records.</p>
          <strong className="receipt-id">{submit.data.report_id}</strong>
          <p>
            {draft.medicine_name} · {draft.batch_number ?? "Batch unknown"}
          </p>
          <p>
            Severity {draft.severity_score}/5 · {draft.symptoms.length} observed
            symptoms
          </p>
          <p>{draft.symptoms.map((symptom) => symptom.name).join(", ")}</p>
          <button
            className="primary"
            onClick={() => {
              submit.reset();
              setDraft(initial);
              setStep(0);
              setCustomSymptoms([]);
              setCustomConditions([]);
              setSymptomName("");
              setConditionName("");
              setSeriousnessChoice("");
            }}
          >
            Start another report
            <ClipboardPlus size={18} />
          </button>
        </div>
      </>
    );
  return (
    <>
      <PageTitle
        title="Adverse reports"
        description="Report a suspected reaction with clear, complete observations."
      />
      <div className="stepper">
        {["Medication", "Patient", "Symptoms", "Review"].map((s, i) => (
          <div className={`step ${i <= step ? "step-active" : ""}`} key={s}>
            <span>{i < step ? <CheckCircle2 size={19} /> : i + 1}</span>
            <strong>{s}</strong>
          </div>
        ))}
      </div>
      <Panel
        title={
          [
            "Identify the medication",
            "Patient details",
            "Describe the reaction",
            "Review your report",
          ][step]
        }
        description={
          [
            "Choose the medicine and batch involved, or indicate that the batch is unknown.",
            "Record relevant demographics without personal identifiers.",
            "Add symptoms, onset, and the severity of the reaction.",
            "Check the details before submitting to the safety team.",
          ][step]
        }
      >
        {error ? <Notice>{error}</Notice> : null}
        {submit.error ? <Notice>{submit.error.message}</Notice> : null}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (step === 3) submit.mutate();
            else next();
          }}
        >
          <div className="form-content">
            {step === 0 ? (
              <div className="form-grid">
                <label>
                  Medicine
                  <select
                    required
                    value={draft.medicine_id || ""}
                    onChange={(e) => {
                      const m = meds.data!.find(
                        (m) => m.medicine_id === Number(e.target.value),
                      );
                      patch({
                        medicine_id: m?.medicine_id ?? 0,
                        medicine_name: m?.commercial_name ?? "",
                        batch_number: "",
                      });
                    }}
                  >
                    <option value="">Select a medicine</option>
                    {meds.data!.map((m) => (
                      <option value={m.medicine_id} key={m.medicine_id}>
                        {m.commercial_name} — {m.generic_name} {m.strength}
                      </option>
                    ))}
                  </select>
                </label>
                <div>
                <label>
                  Production batch
                  <select
                    required={draft.batch_number !== null}
                    disabled={!draft.medicine_id || draft.batch_number === null}
                    value={draft.batch_number ?? ""}
                    onChange={(e) => patch({ batch_number: e.target.value })}
                  >
                    <option value="">
                      {!draft.medicine_id ? "Select a medicine first" : draft.batch_number === null ? "Batch unknown" : batches.isFetching
                        ? "Loading batches…"
                        : "Select a batch"}
                    </option>
                    {batches.data?.map((b) => (
                      <option key={b.batch_number} value={b.batch_number}>
                        {b.batch_number} · {b.recall_status.replaceAll("_", " ").toLowerCase()}
                      </option>
                    ))}
                  </select>
                  {draft.batch_number !== null && batches.error ? (
                    <span className="field-error">{batches.error.message}</span>
                  ) : null}
                  {draft.batch_number !== null && batches.data?.length === 0 ? (
                    <span className="field-error">
                      No registered batches are available for this medicine.
                    </span>
                  ) : null}
                </label>
                <label className="check-label">
                  <input
                    type="checkbox"
                    checked={draft.batch_number === null}
                    onChange={(e) => patch({ batch_number: e.target.checked ? null : "" })}
                  />
                  I don't know the batch number
                </label>
                <p className="small muted">Expired and recalled batches can also be reported.</p>
                </div>
                <label>
                  Reporter type
                  <select
                    required
                    value={draft.reporter_type}
                    onChange={(e) => patch({ reporter_type: e.target.value })}
                  >
                    <option value="">Select reporter type</option>
                    <option value="HOSPITAL_DOCTOR">Hospital doctor</option>
                    <option value="PATIENT">Patient</option>
                    <option value="PHARMACIST">Pharmacist</option>
                  </select>
                </label>
                <label>
                  Reporting hospital (optional)
                  <select
                    value={draft.hospital_id ?? ""}
                    onChange={(e) =>
                      patch({
                        hospital_id: e.target.value
                          ? Number(e.target.value)
                          : null,
                      })
                    }
                  >
                    <option value="">Not specified</option>
                    {hospitals.data?.map((h) => (
                      <option key={h.hospital_id} value={h.hospital_id}>
                        {h.hospital_name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            ) : step === 1 ? (
              <>
                <div className="form-grid">
                  <label>
                    Age (years)
                    <input
                      required
                      type="number"
                      min="0"
                      max="120"
                      value={draft.patient_demographics.age}
                      onChange={(e) =>
                        patch({
                          patient_demographics: {
                            ...draft.patient_demographics,
                            age: e.target.value === "" ? "" : Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                  <label>
                    Gender
                    <select
                      required
                      value={draft.patient_demographics.gender}
                      onChange={(e) =>
                        patch({
                          patient_demographics: {
                            ...draft.patient_demographics,
                            gender: e.target.value,
                          },
                        })
                      }
                    >
                      <option value="">Select gender</option>
                      {["Female", "Male", "Non-binary", "Other"].map((g) => (
                        <option key={g}>{g}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <fieldset>
                  <legend>Pre-existing conditions</legend>
                  <p className="small muted">Leave unchecked if none apply.</p>
                  <div className="checkbox-grid">
                    {[...conditions, ...customConditions].map((c) => (
                      <label className="check-label" key={c}>
                        <input
                          type="checkbox"
                          checked={draft.patient_demographics.pre_existing_conditions.includes(
                            c,
                          )}
                          onChange={(e) =>
                            patch({
                              patient_demographics: {
                                ...draft.patient_demographics,
                                pre_existing_conditions: e.target.checked
                                  ? [
                                      ...draft.patient_demographics
                                        .pre_existing_conditions,
                                      c,
                                    ]
                                  : draft.patient_demographics.pre_existing_conditions.filter(
                                      (v) => v !== c,
                                    ),
                              },
                            })
                          }
                        />
                        {c}
                      </label>
                    ))}
                  </div>
                  <div className="form-grid">
                    <label>Other pre-existing condition
                      <input value={conditionName} maxLength={100} onChange={(e) => setConditionName(e.target.value)} placeholder="Enter a condition not listed above" />
                    </label>
                    <button className="secondary" type="button" onClick={() => addObservation("condition")}>Add condition</button>
                  </div>
                </fieldset>
              </>
            ) : step === 2 ? (
              <>
                <fieldset>
                  <legend>Observed symptoms</legend>
                  <div className="symptom-pills">
                    {[...symptoms, ...customSymptoms].map((s) => (
                      <label
                        className={`symptom-pill ${draft.symptoms.some((x) => x.name === s) ? "selected" : ""}`}
                        key={s}
                      >
                        <input
                          type="checkbox"
                          checked={draft.symptoms.some((x) => x.name === s)}
                          onChange={(e) =>
                            patch({
                              symptoms: e.target.checked
                                ? [
                                    ...draft.symptoms,
                                    {
                                      name: s,
                                      onset_minutes: "",
                                      is_critical: false,
                                    },
                                  ]
                                : draft.symptoms.filter((x) => x.name !== s),
                            })
                          }
                        />
                        {s}
                      </label>
                    ))}
                  </div>
                  <div className="form-grid">
                    <label>Other observed symptom
                      <input value={symptomName} maxLength={100} onChange={(e) => setSymptomName(e.target.value)} placeholder="Enter a symptom not listed above" />
                    </label>
                    <button className="secondary" type="button" onClick={() => addObservation("symptom")}>Add symptom</button>
                  </div>
                </fieldset>
                {draft.symptoms.map((s, i) => (
                  <div className="symptom-detail" key={s.name}>
                    <strong>{s.name}</strong>
                    <label>
                      Onset (minutes after medicine use)
                      <input
                        required={s.onset_minutes !== null}
                        disabled={s.onset_minutes === null}
                        type="number"
                        min="0"
                        value={s.onset_minutes ?? ""}
                        onChange={(e) =>
                          patch({
                            symptoms: draft.symptoms.map((v, j) =>
                              j === i
                                ? {
                                    ...v,
                                    onset_minutes: e.target.value === "" ? "" : Number(e.target.value),
                                  }
                                : v,
                            ),
                          })
                        }
                      />
                    </label>
                    <label className="check-label">
                      <input type="checkbox" checked={s.onset_minutes === null}
                        onChange={(e) => patch({ symptoms: draft.symptoms.map((v, j) => j === i
                          ? { ...v, onset_minutes: e.target.checked ? null : "" } : v) })} />
                      Onset unknown
                    </label>
                  </div>
                ))}
                <label>
                  Reaction intensity
                  <select
                    required
                    value={draft.severity_score}
                    onChange={(e) =>
                      patch({ severity_score: e.target.value === "" ? "" : Number(e.target.value) })
                    }
                  >
                    <option value="">Select severity</option>
                    {["Mild", "Mild to moderate", "Moderate", "Severe", "Very severe"].map((label, i) => (
                      <option key={label} value={i + 1}>{i + 1}/5 - {label}</option>
                    ))}
                  </select>
                  <span className="small muted">Project intensity scale. Intensity and seriousness are recorded separately.</span>
                </label>
                <fieldset>
                  <legend>Serious outcomes</legend>
                  <label>Seriousness information
                    <select required value={seriousnessChoice} onChange={(e) => {
                      setSeriousnessChoice(e.target.value);
                      patch({ seriousness_criteria: e.target.value === "unknown" || !e.target.value ? null : [] });
                    }}>
                      <option value="">Select an assessment</option>
                      <option value="reported">One or more serious outcomes reported</option>
                      <option value="none">No serious outcomes reported</option>
                      <option value="unknown">Unknown</option>
                    </select>
                  </label>
                  {seriousnessChoice === "reported" ? <div className="checkbox-grid">
                    {seriousOutcomes.map(([value, label]) => <label className="check-label" key={value}>
                      <input type="checkbox" checked={draft.seriousness_criteria?.includes(value) ?? false}
                        onChange={(e) => patch({ seriousness_criteria: e.target.checked
                          ? [...(draft.seriousness_criteria ?? []), value]
                          : draft.seriousness_criteria?.filter((v) => v !== value) ?? [] })} />
                      {label}
                    </label>)}
                  </div> : null}
                  <p className="small muted">Record known outcomes; a symptom name alone does not establish seriousness.</p>
                </fieldset>
                <label>
                  Clinical notes
                  <textarea
                    maxLength={2000}
                    rows={5}
                    value={draft.clinical_notes}
                    onChange={(e) => patch({ clinical_notes: e.target.value })}
                    placeholder="Describe the reaction, onset, and any treatment given."
                  />
                </label>
              </>
            ) : (
              <>
                <dl className="review-grid">
                  <div>
                    <dt>Medicine</dt>
                    <dd>{draft.medicine_name}</dd>
                  </div>
                  <div>
                    <dt>Batch</dt>
                    <dd>{draft.batch_number ?? "Unknown"}</dd>
                  </div>
                  <div>
                    <dt>Patient</dt>
                    <dd>
                      {draft.patient_demographics.age} years ·{" "}
                      {draft.patient_demographics.gender}
                    </dd>
                  </div>
                  <div>
                    <dt>Reaction intensity</dt>
                    <dd>{draft.severity_score}/5</dd>
                  </div>
                  <div>
                    <dt>Serious outcomes</dt>
                    <dd>{draft.seriousness_criteria === null ? "Unknown" : draft.seriousness_criteria.length
                      ? draft.seriousness_criteria.map((c) => seriousOutcomes.find(([value]) => value === c)?.[1] ?? c).join("; ")
                      : "None reported"}</dd>
                  </div>
                  <div>
                    <dt>Conditions</dt>
                    <dd>
                      {draft.patient_demographics.pre_existing_conditions.join(
                        ", ",
                      ) || "None specified"}
                    </dd>
                  </div>
                  <div>
                    <dt>Symptoms</dt>
                    <dd>
                      {draft.symptoms
                        .map(
                          (s) =>
                            `${s.name} (${s.onset_minutes === null ? "onset unknown" : `${s.onset_minutes} min after medicine use`}${s.is_critical ? ", critical" : ""})`,
                        )
                        .join("; ")}
                    </dd>
                  </div>
                </dl>
                <div className="review-notes">
                  <strong>Clinical notes</strong>
                  <p>{draft.clinical_notes || "No notes provided."}</p>
                </div>
              </>
            )}
          </div>
          <div className="form-footer">
            <button
              type="button"
              className="secondary"
              disabled={step === 0 || submit.isPending}
              onClick={() => {
                setError("");
                setStep((s) => s - 1);
              }}
            >
              <ArrowLeft size={17} />
              Back
            </button>
            <span className="small muted">Step {step + 1} of 4</span>
            <button className="primary" disabled={submit.isPending}>
              {step === 3
                ? submit.isPending
                  ? "Submitting…"
                  : "Submit report"
                : "Continue"}
              <ArrowRight size={17} />
            </button>
          </div>
        </form>
      </Panel>
    </>
  );
}
