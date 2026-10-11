"""
MongoDB Seed Script for Pharmavigil
Populates the adverse_reports collection with 22 realistic polymorphic adverse event records.
Includes clear signal clusters (Cardiomax -> Severe Dizziness / Hypotension; Neurocalm -> Arrhythmia).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.database.mongo_client import mongo_client


SAMPLE_ADVERSE_REPORTS = [
    # --- Cluster 1: Cardiomax (Batch BCH-PCM-9042) -> Severe Dizziness & Hypotension ---
    {
        "report_id": "ADR-2026-0001",
        "batch_number": "BCH-PCM-9042",
        "medicine_id": 101,
        "medicine_name": "Cardiomax",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 58,
            "gender": "Female",
            "pre_existing_conditions": ["Hypertension", "Type 2 Diabetes"]
        },
        "symptoms": [
            {"name": "Severe Dizziness", "onset_minutes": 45, "is_critical": True},
            {"name": "Acute Hypotension", "onset_minutes": 60, "is_critical": True},
            {"name": "Nausea", "onset_minutes": 30, "is_critical": False}
        ],
        "severity_score": 5,
        "hospital_id": 1,
        "clinical_notes": "Patient experienced sudden blood pressure drop post-administration of morning dosage. Vital stabilization required IV saline infusion.",
        "reported_at": "2026-03-10T09:30:00Z"
    },
    {
        "report_id": "ADR-2026-0002",
        "batch_number": "BCH-PCM-9042",
        "medicine_id": 101,
        "medicine_name": "Cardiomax",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 64,
            "gender": "Male",
            "pre_existing_conditions": ["Coronary Artery Disease"]
        },
        "symptoms": [
            {"name": "Severe Dizziness", "onset_minutes": 30, "is_critical": True},
            {"name": "Syncope", "onset_minutes": 40, "is_critical": True}
        ],
        "severity_score": 4,
        "hospital_id": 2,
        "clinical_notes": "Syncopal episode observed within 40 minutes. Severe dizziness reported prior to loss of consciousness.",
        "reported_at": "2026-03-12T11:15:00Z"
    },
    {
        "report_id": "ADR-2026-0003",
        "batch_number": "BCH-PCM-9042",
        "medicine_id": 101,
        "medicine_name": "Cardiomax",
        "reporter_type": "PATIENT",
        "patient_demographics": {
            "age": 52,
            "gender": "Female",
            "pre_existing_conditions": ["Hypertension"]
        },
        "symptoms": [
            {"name": "Severe Dizziness", "onset_minutes": 50, "is_critical": True},
            {"name": "Headache", "onset_minutes": 120, "is_critical": False}
        ],
        "severity_score": 4,
        "hospital_id": 3,
        "clinical_notes": "Self-reported feeling extreme lightheadedness and acute dizziness after taking Cardiomax 50mg.",
        "reported_at": "2026-03-14T14:00:00Z"
    },
    {
        "report_id": "ADR-2026-0004",
        "batch_number": "BCH-PCM-9042",
        "medicine_id": 101,
        "medicine_name": "Cardiomax",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 70,
            "gender": "Male",
            "pre_existing_conditions": ["Chronic Kidney Disease", "Hypertension"]
        },
        "symptoms": [
            {"name": "Acute Hypotension", "onset_minutes": 25, "is_critical": True},
            {"name": "Bradycardia", "onset_minutes": 35, "is_critical": True}
        ],
        "severity_score": 5,
        "hospital_id": 1,
        "clinical_notes": "Profound acute hypotension with systolic BP dropping below 70 mmHg. Monitored in ICU.",
        "reported_at": "2026-03-15T08:45:00Z"
    },
    {
        "report_id": "ADR-2026-0005",
        "batch_number": "BCH-PCM-9043",
        "medicine_id": 101,
        "medicine_name": "Cardiomax",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 49,
            "gender": "Female",
            "pre_existing_conditions": []
        },
        "symptoms": [
            {"name": "Mild Dizziness", "onset_minutes": 90, "is_critical": False},
            {"name": "Fatigue", "onset_minutes": 180, "is_critical": False}
        ],
        "severity_score": 2,
        "hospital_id": 4,
        "clinical_notes": "Transient dizziness resolved spontaneously after rest.",
        "reported_at": "2026-03-18T16:20:00Z"
    },

    # --- Cluster 2: Neurocalm (Batch BCH-NRC-1011) -> Arrhythmia & Dyspnea ---
    {
        "report_id": "ADR-2026-0006",
        "batch_number": "BCH-NRC-1011",
        "medicine_id": 102,
        "medicine_name": "Neurocalm",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 41,
            "gender": "Male",
            "pre_existing_conditions": ["Neuropathic Pain"]
        },
        "symptoms": [
            {"name": "Arrhythmia", "onset_minutes": 30, "is_critical": True},
            {"name": "Dyspnea", "onset_minutes": 45, "is_critical": True}
        ],
        "severity_score": 5,
        "hospital_id": 1,
        "clinical_notes": "Patient presented with sudden onset cardiac arrhythmia and severe shortness of breath.",
        "reported_at": "2026-03-20T10:10:00Z"
    },
    {
        "report_id": "ADR-2026-0007",
        "batch_number": "BCH-NRC-1011",
        "medicine_id": 102,
        "medicine_name": "Neurocalm",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 55,
            "gender": "Female",
            "pre_existing_conditions": ["Fibromyalgia", "Asthma"]
        },
        "symptoms": [
            {"name": "Arrhythmia", "onset_minutes": 20, "is_critical": True},
            {"name": "Palpitations", "onset_minutes": 15, "is_critical": False}
        ],
        "severity_score": 4,
        "hospital_id": 4,
        "clinical_notes": "ECG revealed premature ventricular contractions and arrhythmia following standard 75mg dose.",
        "reported_at": "2026-03-21T13:40:00Z"
    },
    {
        "report_id": "ADR-2026-0008",
        "batch_number": "BCH-NRC-1011",
        "medicine_id": 102,
        "medicine_name": "Neurocalm",
        "reporter_type": "PATIENT",
        "patient_demographics": {
            "age": 36,
            "gender": "Female",
            "pre_existing_conditions": ["Anxiety"]
        },
        "symptoms": [
            {"name": "Arrhythmia", "onset_minutes": 60, "is_critical": True},
            {"name": "Tremors", "onset_minutes": 40, "is_critical": False}
        ],
        "severity_score": 4,
        "hospital_id": 1,
        "clinical_notes": "Rapid irregular heartbeat reported by patient; emergency clinic confirmed irregular cardiac rhythm.",
        "reported_at": "2026-03-22T18:00:00Z"
    },
    {
        "report_id": "ADR-2026-0009",
        "batch_number": "BCH-NRC-1012",
        "medicine_id": 102,
        "medicine_name": "Neurocalm",
        "reporter_type": "PATIENT",
        "patient_demographics": {
            "age": 60,
            "gender": "Male",
            "pre_existing_conditions": ["Diabetes"]
        },
        "symptoms": [
            {"name": "Somnolence", "onset_minutes": 120, "is_critical": False}
        ],
        "severity_score": 2,
        "hospital_id": 3,
        "clinical_notes": "Expected mild drowsiness reported during titration phase.",
        "reported_at": "2026-03-23T09:00:00Z"
    },

    # --- Cluster 3: Glucoguard (Batch BCH-GLU-5501) -> Hypoglycemia & Gastrointestinal Distress ---
    {
        "report_id": "ADR-2026-0010",
        "batch_number": "BCH-GLU-5501",
        "medicine_id": 103,
        "medicine_name": "Glucoguard",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 62,
            "gender": "Female",
            "pre_existing_conditions": ["Type 2 Diabetes"]
        },
        "symptoms": [
            {"name": "Severe Hypoglycemia", "onset_minutes": 90, "is_critical": True},
            {"name": "Diaphoresis", "onset_minutes": 75, "is_critical": False}
        ],
        "severity_score": 4,
        "hospital_id": 1,
        "clinical_notes": "Blood glucose dropped unexpectedly to 42 mg/dL. Required dextrose administration.",
        "reported_at": "2026-03-24T12:30:00Z"
    },
    {
        "report_id": "ADR-2026-0011",
        "batch_number": "BCH-GLU-5501",
        "medicine_id": 103,
        "medicine_name": "Glucoguard",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 68,
            "gender": "Male",
            "pre_existing_conditions": ["Type 2 Diabetes", "Renal Impairment"]
        },
        "symptoms": [
            {"name": "Severe Hypoglycemia", "onset_minutes": 100, "is_critical": True},
            {"name": "Confusion", "onset_minutes": 110, "is_critical": True}
        ],
        "severity_score": 4,
        "hospital_id": 2,
        "clinical_notes": "Acute hypoglycemic episode with confusion and disorientation in elderly diabetic patient.",
        "reported_at": "2026-03-25T15:10:00Z"
    },
    {
        "report_id": "ADR-2026-0012",
        "batch_number": "BCH-GLU-5501",
        "medicine_id": 103,
        "medicine_name": "Glucoguard",
        "reporter_type": "PATIENT",
        "patient_demographics": {
            "age": 45,
            "gender": "Male",
            "pre_existing_conditions": ["Pre-diabetes"]
        },
        "symptoms": [
            {"name": "Abdominal Cramps", "onset_minutes": 60, "is_critical": False},
            {"name": "Diarrhea", "onset_minutes": 90, "is_critical": False}
        ],
        "severity_score": 2,
        "hospital_id": 1,
        "clinical_notes": "Mild gastrointestinal upset post meal.",
        "reported_at": "2026-03-26T17:45:00Z"
    },

    # --- Cluster 4: PulmoBreeze (Batch BCH-PLM-3301) -> Bronchospasm & Tachycardia ---
    {
        "report_id": "ADR-2026-0013",
        "batch_number": "BCH-PLM-3301",
        "medicine_id": 104,
        "medicine_name": "PulmoBreeze",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 29,
            "gender": "Female",
            "pre_existing_conditions": ["Severe Asthma"]
        },
        "symptoms": [
            {"name": "Paradoxical Bronchospasm", "onset_minutes": 5, "is_critical": True},
            {"name": "Tachycardia", "onset_minutes": 10, "is_critical": True}
        ],
        "severity_score": 5,
        "hospital_id": 4,
        "clinical_notes": "Patient suffered paradoxical bronchospasm immediately after using inhaler. Administered epinephrine and nebulized ipratropium.",
        "reported_at": "2026-03-27T08:00:00Z"
    },
    {
        "report_id": "ADR-2026-0014",
        "batch_number": "BCH-PLM-3301",
        "medicine_id": 104,
        "medicine_name": "PulmoBreeze",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 34,
            "gender": "Male",
            "pre_existing_conditions": ["COPD"]
        },
        "symptoms": [
            {"name": "Paradoxical Bronchospasm", "onset_minutes": 8, "is_critical": True},
            {"name": "Wheezing", "onset_minutes": 10, "is_critical": False}
        ],
        "severity_score": 4,
        "hospital_id": 4,
        "clinical_notes": "Bronchospasm flared minutes post dose. Emergency oxygen required.",
        "reported_at": "2026-03-28T11:30:00Z"
    },
    {
        "report_id": "ADR-2026-0015",
        "batch_number": "BCH-PLM-3301",
        "medicine_id": 104,
        "medicine_name": "PulmoBreeze",
        "reporter_type": "PATIENT",
        "patient_demographics": {
            "age": 22,
            "gender": "Male",
            "pre_existing_conditions": ["Mild Asthma"]
        },
        "symptoms": [
            {"name": "Hand Tremors", "onset_minutes": 15, "is_critical": False},
            {"name": "Palpitations", "onset_minutes": 20, "is_critical": False}
        ],
        "severity_score": 2,
        "hospital_id": 4,
        "clinical_notes": "Slight jitteriness after two puffs of inhaler.",
        "reported_at": "2026-03-29T14:15:00Z"
    },

    # --- Cluster 5: GastroRelief & Dermacure (Additional Clinical Reports) ---
    {
        "report_id": "ADR-2026-0016",
        "batch_number": "BCH-GST-7701",
        "medicine_id": 105,
        "medicine_name": "GastroRelief",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 50,
            "gender": "Female",
            "pre_existing_conditions": ["GERD"]
        },
        "symptoms": [
            {"name": "Skin Rash", "onset_minutes": 360, "is_critical": False},
            {"name": "Pruritus", "onset_minutes": 360, "is_critical": False}
        ],
        "severity_score": 3,
        "hospital_id": 1,
        "clinical_notes": "Erythematous rash developed across torso several hours after ingestion.",
        "reported_at": "2026-03-30T09:45:00Z"
    },
    {
        "report_id": "ADR-2026-0017",
        "batch_number": "BCH-GST-7702",
        "medicine_id": 105,
        "medicine_name": "GastroRelief",
        "reporter_type": "PATIENT",
        "patient_demographics": {
            "age": 38,
            "gender": "Male",
            "pre_existing_conditions": ["Gastritis"]
        },
        "symptoms": [
            {"name": "Headache", "onset_minutes": 180, "is_critical": False}
        ],
        "severity_score": 1,
        "hospital_id": 2,
        "clinical_notes": "Mild dull headache reported.",
        "reported_at": "2026-03-31T13:20:00Z"
    },
    {
        "report_id": "ADR-2026-0018",
        "batch_number": "BCH-DER-8801",
        "medicine_id": 106,
        "medicine_name": "Dermacure",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 27,
            "gender": "Female",
            "pre_existing_conditions": ["Eczema", "Atopic Dermatitis"]
        },
        "symptoms": [
            {"name": "Anaphylaxis", "onset_minutes": 15, "is_critical": True},
            {"name": "Facial Edema", "onset_minutes": 20, "is_critical": True}
        ],
        "severity_score": 5,
        "hospital_id": 3,
        "clinical_notes": "Severe hypersensitivity and acute anaphylaxis reaction observed within 15 minutes of topical application.",
        "reported_at": "2026-04-01T10:00:00Z"
    },
    {
        "report_id": "ADR-2026-0019",
        "batch_number": "BCH-DER-8801",
        "medicine_id": 106,
        "medicine_name": "Dermacure",
        "reporter_type": "PATIENT",
        "patient_demographics": {
            "age": 33,
            "gender": "Female",
            "pre_existing_conditions": ["Contact Dermatitis"]
        },
        "symptoms": [
            {"name": "Burning Sensation", "onset_minutes": 10, "is_critical": False}
        ],
        "severity_score": 2,
        "hospital_id": 3,
        "clinical_notes": "Mild localized stinging upon skin application.",
        "reported_at": "2026-04-02T16:30:00Z"
    },
    {
        "report_id": "ADR-2026-0020",
        "batch_number": "BCH-PCM-9042",
        "medicine_id": 101,
        "medicine_name": "Cardiomax",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 73,
            "gender": "Male",
            "pre_existing_conditions": ["Hypertension", "Atrial Fibrillation"]
        },
        "symptoms": [
            {"name": "Severe Dizziness", "onset_minutes": 40, "is_critical": True},
            {"name": "Acute Hypotension", "onset_minutes": 50, "is_critical": True},
            {"name": "Syncope", "onset_minutes": 55, "is_critical": True}
        ],
        "severity_score": 5,
        "hospital_id": 3,
        "clinical_notes": "Critical collapse after blood pressure dropped to 65/40 mmHg. High-risk signal confirmed on batch BCH-PCM-9042.",
        "reported_at": "2026-04-03T11:10:00Z"
    },
    {
        "report_id": "ADR-2026-0021",
        "batch_number": "BCH-NRC-1011",
        "medicine_id": 102,
        "medicine_name": "Neurocalm",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 48,
            "gender": "Male",
            "pre_existing_conditions": ["Peripheral Neuropathy"]
        },
        "symptoms": [
            {"name": "Arrhythmia", "onset_minutes": 35, "is_critical": True},
            {"name": "Seizure", "onset_minutes": 50, "is_critical": True}
        ],
        "severity_score": 5,
        "hospital_id": 2,
        "clinical_notes": "Focal seizure preceded by sudden severe arrhythmia. Neurological and cardiology workup initiated.",
        "reported_at": "2026-04-04T14:50:00Z"
    },
    {
        "report_id": "ADR-2026-0022",
        "batch_number": "BCH-GLU-5502",
        "medicine_id": 103,
        "medicine_name": "Glucoguard",
        "reporter_type": "HOSPITAL_DOCTOR",
        "patient_demographics": {
            "age": 67,
            "gender": "Female",
            "pre_existing_conditions": ["Type 2 Diabetes"]
        },
        "symptoms": [
            {"name": "Nausea", "onset_minutes": 60, "is_critical": False},
            {"name": "Vomiting", "onset_minutes": 75, "is_critical": False}
        ],
        "severity_score": 3,
        "hospital_id": 3,
        "clinical_notes": "Patient consumed medication from expired batch BCH-GLU-5502 inadvertently. Managed with antiemetics.",
        "reported_at": "2026-04-05T09:15:00Z"
    }
]


def seed_mongodb():
    """Seeds the adverse_reports collection with sample documents."""
    print("Connecting to MongoDB for adverse event seeding...")
    collection = mongo_client.get_adverse_reports_collection()
    
    # Clean previous sample records
    print("Clearing existing adverse reports...")
    collection.delete_many({})
    
    print(f"Inserting {len(SAMPLE_ADVERSE_REPORTS)} clinical adverse event documents...")
    result = collection.insert_many(SAMPLE_ADVERSE_REPORTS)
    print(f"Successfully seeded {len(result.inserted_ids)} adverse reports into MongoDB.")


if __name__ == "__main__":
    try:
        seed_mongodb()
    except Exception as e:
        print(f"Error seeding MongoDB: {e}")
        sys.exit(1)
