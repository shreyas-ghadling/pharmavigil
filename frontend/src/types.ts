export type Role = "DOCTOR_PATIENT" | "PHARMACIST" | "SAFETY_OFFICER_ADMIN";
export interface User {
  user_id: number;
  username: string;
  role: Role;
  full_name: string;
  email: string;
  csrf: string;
}
export interface Medicine {
  medicine_id: number;
  commercial_name: string;
  generic_name: string;
  strength: string;
  dosage_form: string;
  stock_unit: string;
  manufacturer_name: string;
}
export interface Batch {
  batch_number: string;
  medicine_id: number;
  commercial_name: string;
  manufacturing_date: string;
  expiry_date: string;
  total_units_produced: number;
  recall_status: string;
  days_left: number;
  stock_unit: string;
}
export interface Stock extends Batch {
  generic_name: string;
  dosage_form: string;
  strength: string;
  manufacturer_name: string;
  current_stock: number;
  total_distributed_units: number;
  total_received_units: number;
  has_inferred_opening_balance: boolean;
  distribution_count: number;
}
export interface Hospital {
  hospital_id: number;
  hospital_name: string;
  city: string;
  state: string;
  contact_phone: string;
}
export interface Signal {
  medicine: string;
  medicine_id: number | null;
  medicine_key: string;
  formulation: string;
  symptom: string;
  incident_count: number;
  avg_severity: number;
  critical_cases: number;
  signal_risk_score: number;
  risk_level: string;
  alert_level: string;
  recommendation: string;
  priority_score: number;
  review_priority: "URGENT" | "HIGH" | "ROUTINE";
  reported_serious_cases: number;
  seriousness_unknown_entries: number;
  revision: string;
  review_status: "NEEDS_REVIEW" | "REVIEWED" | "CLOSED";
  review?: { status: string; notes: string; reviewed_at: string } | null;
  previous_period_count: number | null;
}
export interface Recall {
  audit_id: number;
  batch_number: string;
  reason: string;
  recalled_by: string;
  affected_hospitals: number;
  total_units_recalled: number;
  recalled_at: string;
  distributed_quantity_at_initiation: number;
  recall_stage: "INITIATED";
  stock_unit: string;
}
export interface Quarantine {
  hospital_id: number;
  hospital_name: string;
  city: string;
  contact_phone: string;
  commercial_name: string;
  batch_number: string;
  total_quarantine_units: number;
  historically_distributed_units: number;
  affected_reason: "RECALLED" | "EXPIRED";
  stock_unit: string;
}
export interface ClinicalReport {
  report_id: string;
  batch_number: string | null;
  medicine_name: string;
  severity_score: number;
  clinical_notes: string;
  reported_at: string;
  reporter_type: string;
  seriousness_criteria?: string[] | null;
  symptoms?: Symptom[];
  review?: { status: "REVIEWED" | "FOLLOW_UP"; notes: string; reviewed_at: string };
  submitted_by?: { user_id: number; username: string; full_name: string; role: string } | null;
  patient_demographics?: {
    age: number;
    gender: string;
    pre_existing_conditions: string[];
  };
}
export interface Overview {
  inventory: Stock[];
  signals: Signal[];
  recalls: Recall[];
  warnings: string[];
}
export interface Symptom {
  name: string;
  onset_minutes: number | null;
  is_critical: boolean;
}
export interface AdverseReport {
  medicine_id: number;
  medicine_name: string;
  batch_number: string | null;
  reporter_type: string;
  hospital_id: number | null;
  patient_demographics: {
    age: number;
    gender: string;
    pre_existing_conditions: string[];
  };
  symptoms: Symptom[];
  severity_score: number;
  seriousness_criteria: string[] | null;
  clinical_notes: string;
}
