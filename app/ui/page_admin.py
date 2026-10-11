"""
Portal 3: Safety Officer & Admin Control Center
Features real-time pharmacovigilance signal detection, Plotly visualization,
emergency stored procedure recalls, CTE quarantine tracing, and PDF/CSV audit generation.
"""

from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from app.services.sql_service import sql_service
from app.services.mongo_service import mongo_service
from app.services.report_generator import report_generator


def render_admin_portal():
    st.header("🛡️ Safety Officer & Regulatory Admin Control Center")
    st.markdown(
        "Real-time pharmacovigilance surveillance, signal detection analytics, "
        "emergency batch recalls, and regulatory audit manifest generation."
    )

    tab_alarms, tab_recall, tab_quarantine, tab_search, tab_export = st.tabs([
        "🚨 Signal Detection Alarms",
        "⚠️ Emergency Batch Recall (Stored Procedure)",
        "🗺️ Quarantined Stock (CTE Tracing)",
        "🔍 Clinical Notes Keyword Search",
        "📄 Safety Audit Manifest Export"
    ])

    # --- TAB 1: SIGNAL DETECTION ALARMS ---
    with tab_alarms:
        st.subheader("Live Real-Time Risk Alarms (MongoDB 6-Stage Aggregation Pipeline)")
        st.caption("Executes $match -> $unwind -> $group -> $match (threshold) -> $project -> $sort")

        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1:
            min_sev = st.slider("Filter: Minimum Severity Score", min_value=1, max_value=5, value=3)
        with col_ctrl2:
            min_inc = st.slider("Filter: Minimum Incident Frequency", min_value=1, max_value=10, value=2)

        try:
            signals = mongo_service.execute_safety_signal_detection_pipeline(
                min_severity=min_sev,
                min_incidents=min_inc
            )
        except Exception as e:
            st.warning(f"Unable to run MongoDB Aggregation Pipeline: {e}")
            signals = []

        if signals:
            # Display Alarm Badges
            for s in signals:
                alert_color = "red" if s.get("alert_level") == "CRITICAL" else "orange"
                st.error(
                    f"**[{s.get('alert_level')}] {s['medicine']} — {s['symptom']}**\n\n"
                    f"- **Signal Risk Score:** `{s['signal_risk_score']}` "
                    f"(Incident Count: {s['incident_count']}, Avg Severity: {s['avg_severity']}, Critical Cases: {s['critical_cases']})\n"
                    f"- **System Recommendation:** {s.get('recommendation')}"
                )

            # Interactive Plotly Charts
            df_signals = pd.DataFrame(signals)
            st.subheader("Signal Risk Score by Drug & Clinical Symptom")
            fig = px.bar(
                df_signals,
                x="medicine",
                y="signal_risk_score",
                color="symptom",
                barmode="group",
                title="Calculated Signal Risk Scores (Severity × Frequency)",
                labels={"signal_risk_score": "Risk Score", "medicine": "Medicine Formulation"}
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.success("No critical pharmacovigilance safety signals currently breach the alarm threshold.")

    # --- TAB 2: EMERGENCY BATCH RECALL VIA STORED PROCEDURE ---
    with tab_recall:
        st.subheader("Emergency Batch Recall Action Panel (MySQL Stored Procedure)")
        st.markdown(
            "Invokes the real MySQL Stored Procedure `sp_recall_batch(p_batch_number, p_reason, p_recalled_by, OUT affected, OUT units)`. "
            "Atomically updates batch lifecycle status, computes affected distribution across hospitals, and logs an audit row."
        )

        try:
            available_batches = sql_service.get_batches()
            active_batch_numbers = [b["batch_number"] for b in available_batches if b.get("recall_status") != "RECALLED"]
        except Exception:
            active_batch_numbers = ["BCH-PCM-9042", "BCH-NRC-1011", "BCH-GLU-5501"]

        # Automatically fill Authorizing Officer from logged-in user
        logged_in_user = st.session_state.get("user", {})
        authorizing_officer = logged_in_user.get("full_name") or logged_in_user.get("username") or "Chief Safety Officer Miller"

        with st.form("recall_stored_procedure_form"):
            selected_batch = st.selectbox(
                "Select Batch to Recall *",
                options=active_batch_numbers,
                index=None,
                placeholder="-- Select Batch to Recall --"
            )
            recall_reason = st.text_input(
                "Reason for Regulatory Recall *",
                value="",
                placeholder="Enter clinical or regulatory reason..."
            )
            recalled_by = st.text_input(
                "Authorizing Officer",
                value=authorizing_officer,
                disabled=True
            )

            submit_recall = st.form_submit_button("🚨 EXECUTE ATOMIC EMERGENCY BATCH RECALL", use_container_width=True)

        if submit_recall:
            if not selected_batch:
                st.error("Please select a batch to recall.")
            elif not recall_reason or not recall_reason.strip():
                st.error("Please enter a reason for the regulatory recall.")
            else:
                try:
                    with st.spinner("Invoking MySQL Stored Procedure 'sp_recall_batch'..."):
                        recall_result = sql_service.execute_emergency_recall(
                            batch_number=selected_batch,
                            reason=recall_reason.strip(),
                            recalled_by=authorizing_officer
                        )

                    st.success(f"Stored Procedure Executed Successfully! Batch '{selected_batch}' is now RECALLED.")
                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("Quarantined Healthcare Facilities", f"{recall_result['affected_hospitals']} Hospitals")
                    col_m2.metric("Total Quarantine Units Recalled", f"{recall_result['total_units_recalled']:,} Units")

                except Exception as e:
                    st.error(f"Stored procedure call failed: {str(e)}")

        # Display Recall Audit Log
        st.divider()
        st.subheader("Historical Recall Audit Log (`recall_audit` Table)")
        try:
            audits = sql_service.get_recall_audits()
            if audits:
                st.dataframe(pd.DataFrame(audits), use_container_width=True, hide_index=True)
            else:
                st.info("No recalls recorded yet in `recall_audit`.")
        except Exception as e:
            st.caption(f"Could not load audit log: {e}")

    # --- TAB 3: HIGH-RISK QUARANTINE TRACING (CTE QUERY) ---
    with tab_quarantine:
        st.subheader("High-Risk Inventory Quarantine Tracing (SQL Common Table Expressions)")
        st.markdown(
            "Runs the advanced analytical CTE query (`WITH FlaggedBatches AS (...)`) joining "
            "`batch_distribution`, `hospitals`, and `medicines` with `HAVING SUM(quantity_delivered) > 0`."
        )

        try:
            quarantine_data = sql_service.get_high_risk_quarantine_trace()
            if quarantine_data:
                st.dataframe(
                    pd.DataFrame(quarantine_data),
                    column_config={
                        "hospital_name": "Hospital Name",
                        "city": "City",
                        "contact_phone": "Emergency Contact",
                        "commercial_name": "Medicine",
                        "batch_number": "Recalled Batch",
                        "total_quarantine_units": "Units in Quarantine"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No recalled units are currently in hospital distribution. Trigger a recall in Tab 2 to trace.")
        except Exception as e:
            st.warning(f"Could not execute CTE query: {e}")

    # --- TAB 4: CLINICAL NOTES KEYWORD SEARCH ---
    with tab_search:
        st.subheader("Clinical Keyword Retrieval (MongoDB Text Index)")
        st.markdown(
            "Query unstructured doctor clinical notes using MongoDB's native full-text search index "
            "(`$text: {$search: 'keyword'}`). Fast retrieval without external NLP overhead."
        )

        keyword = st.text_input(
            "Search Clinical Terms (e.g., 'hypotension', 'arrhythmia', 'anaphylaxis', 'seizure', 'syncope')",
            value="hypotension"
        )

        if st.button("🔍 Search Doctor Notes"):
            try:
                results = mongo_service.search_clinical_notes_text(keyword)
                st.write(f"Found **{len(results)}** matching clinical reports:")
                for r in results:
                    with st.expander(f"Report: {r.get('report_id')} | Batch: {r.get('batch_number')} | Severity: {r.get('severity_score')}/5"):
                        st.markdown(f"**Clinical Narrative:** *\"{r.get('clinical_notes')}\"*")
                        st.caption(
                            f"Reporter: {r.get('reporter_type')} | "
                            f"Patient Age: {r.get('patient_demographics', {}).get('age')} | "
                            f"Reported At: {r.get('reported_at')}"
                        )
            except Exception as e:
                st.error(f"Search failed: {e}")

    # --- TAB 5: SAFETY AUDIT MANIFEST EXPORT ---
    with tab_export:
        st.subheader("Regulatory Safety Audit Manifest Generator")
        st.markdown(
            "Compile and export formal regulatory documentation detailing recalled batches, "
            "affected hospital inventory, and adverse event metrics."
        )

        try:
            quarantine_records = sql_service.get_high_risk_quarantine_trace()
            audit_records = sql_service.get_recall_audits()
        except Exception:
            quarantine_records = []
            audit_records = []

        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:
            st.markdown("**1. Download Formal PDF Manifest**")
            if st.button("📄 Generate & Build PDF Audit Report"):
                try:
                    pdf_file_path = report_generator.generate_pdf_recall_manifest(
                        quarantine_data=quarantine_records,
                        recall_audits=audit_records
                    )
                    with open(pdf_file_path, "rb") as f:
                        pdf_bytes = f.read()

                    st.success("Regulatory PDF manifest generated successfully. Click below to download:")
                    st.download_button(
                        label="⬇️ Download Regulatory PDF Manifest",
                        data=pdf_bytes,
                        file_name="Safety_Audit_Recall_Manifest.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {e}")

        with col_dl2:
            st.markdown("**2. Download CSV Quarantine Manifest**")
            csv_data = report_generator.generate_csv_quarantine_manifest(quarantine_records)
            st.download_button(
                label="⬇️ Download Quarantine Data (.CSV)",
                data=csv_data,
                file_name="quarantine_distribution_manifest.csv",
                mime="text/csv"
            )
