"""
Portal 1: Doctor & Patient Adverse Reaction Reporting Portal
Interactive Streamlit form for logging adverse events into MongoDB with Pydantic validation.
"""

from datetime import datetime, timezone
import streamlit as st
from app.services.sql_service import sql_service
from app.services.mongo_service import mongo_service
from app.utils.exceptions import InvalidSeverityScoreError, DatabaseConnectionError, BatchMedicineMismatchError


COMMON_SYMPTOMS = [
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
    "Somnolence"
]

COMORBIDITIES = [
    "Hypertension",
    "Type 2 Diabetes",
    "Coronary Artery Disease",
    "Asthma",
    "COPD",
    "Chronic Kidney Disease",
    "Neuropathic Pain",
    "None"
]


def render_patient_portal():
    st.header("🩺 Doctor & Patient Adverse Reaction Reporting Portal")
    st.markdown(
        "Report suspected adverse drug reactions (ADRs), therapeutic failures, or acute side-effects. "
        "Incoming reports are ingested into the polymorphic NoSQL adverse event repository."
    )

    # 1. Fetch live medicines and batches from SQL
    try:
        medicines = sql_service.get_all_medicines()
    except Exception:
        # Fallback offline list if database connection is pending
        medicines = [
            {"medicine_id": 101, "commercial_name": "Cardiomax", "generic_name": "Amlodipine Besylate", "strength": "50mg"},
            {"medicine_id": 102, "commercial_name": "Neurocalm", "generic_name": "Pregabalin", "strength": "75mg"},
            {"medicine_id": 103, "commercial_name": "Glucoguard", "generic_name": "Metformin HCl", "strength": "500mg"},
            {"medicine_id": 104, "commercial_name": "PulmoBreeze", "generic_name": "Salbutamol Sulfate", "strength": "100mcg"},
            {"medicine_id": 105, "commercial_name": "GastroRelief", "generic_name": "Omeprazole", "strength": "20mg"},
            {"medicine_id": 106, "commercial_name": "Dermacure", "generic_name": "Hydrocortisone", "strength": "10mg"}
        ]

    med_map = {f"{m['commercial_name']} ({m['generic_name']} {m['strength']})": m for m in medicines}

    # Medicine and Batch Selection (Reactive - outside form so changing medicine updates batches instantly)
    st.subheader("Medication & Batch Identification")
    col_med, col_batch = st.columns(2)

    with col_med:
        selected_med_label = st.selectbox(
            "1. Medicine Formulation *",
            options=list(med_map.keys()),
            key="adr_selected_medicine"
        )
        selected_med = med_map[selected_med_label]

    # Query active batches strictly belonging to the chosen medicine
    try:
        batches = sql_service.get_batches(medicine_id=selected_med["medicine_id"], only_active=True)
        batch_numbers = [b["batch_number"] for b in batches]
    except Exception:
        batch_numbers = []

    with col_batch:
        if batch_numbers:
            selected_batch = st.selectbox(
                f"2. Production Batch for {selected_med['commercial_name']} *",
                options=batch_numbers,
                key=f"adr_batch_select_{selected_med['medicine_id']}"
            )
        else:
            st.warning(f"No active batches currently registered for {selected_med['commercial_name']}.")
            selected_batch = None

    with st.form("adr_report_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            reporter_type = st.selectbox("3. Reporter Classification *", options=["HOSPITAL_DOCTOR", "PATIENT", "PHARMACIST"])

        with col2:
            st.markdown("**Patient Demographics**")
            age = st.number_input("Patient Age (Years) *", min_value=0, max_value=120, value=45, step=1)
            gender = st.selectbox("Gender *", options=["Female", "Male", "Non-binary", "Other"])
            selected_comorbidities = st.multiselect("Pre-existing Medical Conditions", options=COMORBIDITIES, default=["None"])

        st.divider()

        # Symptoms Section
        st.subheader("Clinical Manifestations & Symptom Telemetry")
        selected_symptoms_list = st.multiselect(
            "Select Observed Symptoms *",
            options=COMMON_SYMPTOMS,
            default=["Severe Dizziness"]
        )

        symptoms_data = []
        if selected_symptoms_list:
            st.markdown("*Specify details for selected symptoms:*")
            cols = st.columns(min(len(selected_symptoms_list), 3))
            for idx, sym in enumerate(selected_symptoms_list):
                col = cols[idx % len(cols)]
                with col:
                    st.caption(f"**{sym}**")
                    onset = st.number_input(f"Onset (min) [{sym}]", min_value=0, max_value=2880, value=30, key=f"onset_{sym}")
                    critical = st.checkbox(f"Critical / Life Threatening", value=(sym in ["Acute Hypotension", "Arrhythmia", "Anaphylaxis", "Seizure"]), key=f"crit_{sym}")
                    symptoms_data.append({
                        "name": sym,
                        "onset_minutes": onset,
                        "is_critical": critical
                    })

        # Severity Score Slider
        st.divider()
        severity_score = st.slider(
            "Clinical Severity Score (1 = Mild discomfort, 5 = Critical / Hospitalization / Life-Threatening) *",
            min_value=1,
            max_value=5,
            value=3,
            help="1: Mild, 2: Moderate, 3: Severe, 4: Very Severe, 5: Life Threatening"
        )

        # Doctor clinical observations text area
        clinical_notes = st.text_area(
            "Doctor Clinical Notes & Observations (Free-Text Search Indexed)",
            placeholder="Detailed clinical narrative, onset progression, administered countermeasures (e.g., 'Patient presented with acute hypotension post morning dose...')"
        )

        submitted = st.form_submit_button("🚀 Submit Adverse Drug Reaction Report", use_container_width=True)

    if submitted:
        if not selected_batch:
            st.error("Validation Error: No valid production batch selected for this medicine.")
            return

        if not selected_symptoms_list:
            st.error("Validation Error: At least one observed symptom must be reported.")
            return

        # Clean comorbidities
        cleaned_comorbidities = [c for c in selected_comorbidities if c != "None"]

        report_payload = {
            "batch_number": selected_batch,
            "medicine_id": selected_med["medicine_id"],
            "medicine_name": selected_med["commercial_name"],
            "reporter_type": reporter_type,
            "patient_demographics": {
                "age": int(age),
                "gender": gender,
                "pre_existing_conditions": cleaned_comorbidities
            },
            "symptoms": symptoms_data,
            "severity_score": int(severity_score),
            "hospital_id": 1,
            "clinical_notes": clinical_notes,
            "reported_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            report_id = mongo_service.insert_adverse_report(report_payload)
            st.success(f"Adverse Report Successfully Ingested into MongoDB Repository!")
            
            # Receipt Card
            st.info(
                f"**Confirmation Receipt**\n\n"
                f"- **Tracking Report ID:** `{report_id}`\n"
                f"- **Medicine:** {selected_med['commercial_name']} (Batch: `{selected_batch}`)\n"
                f"- **Severity Level:** {severity_score} / 5\n"
                f"- **Symptoms Recorded:** {', '.join([s['name'] for s in symptoms_data])}\n"
                f"- **Indexed for Signal Detection:** Yes (Active Telemetry)"
            )
        except BatchMedicineMismatchError as e:
            st.error(f"🛑 Batch-Medicine Mismatch Error: {str(e)}")
        except InvalidSeverityScoreError as e:
            st.error(f"Validation Error: {str(e)}")
        except Exception as e:
            st.error(f"Failed to submit adverse reaction report: {str(e)}")
