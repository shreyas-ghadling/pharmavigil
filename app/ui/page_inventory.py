"""
Portal 2: Hospital Pharmacist Inventory Portal
Live stock tracking via SQL multi-table JOINs, expiry alarms, CSV batch ingestion,
and safe distribution dispatch with domain constraint enforcement.
"""

from datetime import date
import html
from pathlib import Path
import pandas as pd
import streamlit as st

from app.services.sql_service import sql_service
from app.services.report_generator import report_generator
from app.utils.exceptions import (
    ExpiredBatchDispenseError,
    RecalledBatchOperationError,
    DatabaseConnectionError
)


def render_inventory_portal():
    # Breadcrumb & Page Title
    st.markdown('<div class="pv-breadcrumb">Pharmavigil / Hospital Pharmacist Portal</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="pv-page-title">Inventory Management</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color: #666666; font-size: 0.92rem; margin-top: 6px; margin-bottom: 18px;">'
        'Monitor live batch inventories across hospital networks, ingest bulk production shipments, '
        'and dispatch medications with strict regulatory safeguards.'
        '</p>',
        unsafe_allow_html=True
    )

    tab1, tab2, tab3 = st.tabs(["📊 Stock Inventory", "📥 Bulk Intake", "🚚 Regional Dispatch"])

    # --- TAB 1: LIVE STOCK TABLE WITH EXPIRATION ALARMS ---
    with tab1:
        try:
            inventory = sql_service.get_inventory_stock_overview()
        except Exception as e:
            st.warning(f"Could not load live MySQL inventory: {e}")
            inventory = []

        if inventory:
            df = pd.DataFrame(inventory)

            # Determine status classification
            def classify_status(row):
                status = str(row.get("recall_status", "ACTIVE")).upper()
                days = row.get("days_left", 999)
                if status == "RECALLED":
                    return "RECALLED", "pv-pill-recalled", "Quarantined"
                elif status == "EXPIRED" or (days is not None and days < 0):
                    return "EXPIRED", "pv-pill-expired", "Past Expiry"
                elif days is not None and days <= 30:
                    return "EXPIRING SOON", "pv-pill-warning", f"{days}d left"
                else:
                    return "ACTIVE", "pv-pill-active", "Active"

            status_tuples = [classify_status(r) for _, r in df.iterrows()]
            df["status_code"] = [s[0] for s in status_tuples]
            df["pill_class"] = [s[1] for s in status_tuples]
            df["status_badge_txt"] = [f"{s[0]} ({s[2]})" if s[0] == "EXPIRING SOON" else s[0] for s in status_tuples]

            # Metric totals
            total_batches = len(df)
            active_count = int((df["status_code"] == "ACTIVE").sum())
            expiring_soon_count = int((df["status_code"] == "EXPIRING SOON").sum())
            expired_count = int((df["status_code"] == "EXPIRED").sum())
            recalled_count = int((df["status_code"] == "RECALLED").sum())

            # 5 Clean Metric Cards
            m1, m2, m3, m4, m5 = st.columns(5)
            with m1:
                st.markdown(
                    f"""
                    <div class="pv-metric-card">
                        <div class="pv-metric-title">
                            <span>Total Batches</span>
                            <span style="font-size: 1.05rem;">📦</span>
                        </div>
                        <div class="pv-metric-number">{total_batches}</div>
                        <div class="pv-metric-caption">Monitored product lots</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with m2:
                st.markdown(
                    f"""
                    <div class="pv-metric-card">
                        <div class="pv-metric-title">
                            <span>Active Batches</span>
                            <span style="font-size: 1.05rem;">🟢</span>
                        </div>
                        <div class="pv-metric-number">{active_count}</div>
                        <div class="pv-metric-caption">Safe for dispensing</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with m3:
                st.markdown(
                    f"""
                    <div class="pv-metric-card">
                        <div class="pv-metric-title">
                            <span>Expiring Soon</span>
                            <span style="font-size: 1.05rem;">🟡</span>
                        </div>
                        <div class="pv-metric-number">{expiring_soon_count}</div>
                        <div class="pv-metric-caption">Within 30 days</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with m4:
                st.markdown(
                    f"""
                    <div class="pv-metric-card">
                        <div class="pv-metric-title">
                            <span>Expired Batches</span>
                            <span style="font-size: 1.05rem;">🔴</span>
                        </div>
                        <div class="pv-metric-number">{expired_count}</div>
                        <div class="pv-metric-caption">Locked from dispatch</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with m5:
                st.markdown(
                    f"""
                    <div class="pv-metric-card">
                        <div class="pv-metric-title">
                            <span>Recalled Batches</span>
                            <span style="font-size: 1.05rem;">⚠️</span>
                        </div>
                        <div class="pv-metric-number">{recalled_count}</div>
                        <div class="pv-metric-caption">Regulatory quarantine</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

            # Search / Filter Bar
            search_query = st.text_input(
                "Filter stock table",
                placeholder="🔍 Search batch number, medication name, manufacturer...",
                label_visibility="collapsed"
            ).strip().lower()

            # Filter rows if search query is entered
            filtered_df = df
            if search_query:
                mask = (
                    df["batch_number"].astype(str).str.lower().str.contains(search_query) |
                    df["commercial_name"].astype(str).str.lower().str.contains(search_query) |
                    df["manufacturer_name"].astype(str).str.lower().str.contains(search_query) |
                    df["status_code"].astype(str).str.lower().str.contains(search_query)
                )
                filtered_df = df[mask]

            # Render HTML Card Table Matching Reference Design
            rows_html = []
            for _, row in filtered_df.iterrows():
                b_num = html.escape(str(row.get("batch_number", "")))
                c_name = html.escape(str(row.get("commercial_name", "")))
                d_form = html.escape(str(row.get("dosage_form", "")))
                strength = html.escape(str(row.get("strength", "")))
                m_name = html.escape(str(row.get("manufacturer_name", "")))
                exp_date = str(row.get("expiry_date", ""))
                produced = f"{int(row.get('total_units_produced', 0)):,}"
                distrib = f"{int(row.get('total_distributed_units', 0)):,}"
                stock = f"{int(row.get('current_stock', 0)):,}"
                pill_cls = row["pill_class"]
                badge_lbl = row["status_badge_txt"]

                row_snippet = f"""
                <tr>
                    <td style="font-weight: 700;"><span class="pv-mono">{b_num}</span></td>
                    <td>
                        <div style="font-weight: 700; color: #111111;">{c_name}</div>
                        <div style="font-size: 0.76rem; color: #8A8A8A;">{d_form} • {strength}</div>
                    </td>
                    <td style="color: #4A4A4A;">{m_name}</td>
                    <td style="color: #4A4A4A; font-weight: 500;">{exp_date}</td>
                    <td style="text-align: right; color: #666666;">{produced}</td>
                    <td style="text-align: right; color: #666666;">{distrib}</td>
                    <td style="text-align: right; font-weight: 800; color: #111111;">{stock}</td>
                    <td><span class="pv-pill {pill_cls}">● {badge_lbl}</span></td>
                </tr>
                """
                rows_html.append(row_snippet)

            if not rows_html:
                rows_rendered = '<tr><td colspan="8" style="text-align: center; color: #8A8A8A; padding: 28px;">No batches match the search criteria.</td></tr>'
            else:
                rows_rendered = "".join(rows_html)

            table_card_html = f"""
            <div class="pv-card" style="padding: 22px 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #111111;">Batch Inventory Overview</div>
                        <div style="font-size: 0.8rem; color: #8A8A8A; margin-top: 2px;">
                            Showing {len(filtered_df)} of {len(df)} production batches across regional facilities
                        </div>
                    </div>
                </div>
                <div class="pv-table-container">
                    <table class="pv-table">
                        <thead>
                            <tr>
                                <th>Batch No</th>
                                <th>Medication</th>
                                <th>Manufacturer</th>
                                <th>Expiration</th>
                                <th style="text-align: right;">Produced</th>
                                <th style="text-align: right;">Dispatched</th>
                                <th style="text-align: right;">Remaining Stock</th>
                                <th>Safety Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_rendered}
                        </tbody>
                    </table>
                </div>
            </div>
            """
            st.markdown(table_card_html, unsafe_allow_html=True)

        else:
            st.info("No batch records found in the database. Intake batches using the Bulk Intake tab.")

    # --- TAB 2: BULK BATCH CSV INTAKE ---
    with tab2:
        st.markdown(
            """
            <div class="pv-card" style="margin-bottom: 1.2rem;">
                <div style="font-size: 1.15rem; font-weight: 800; color: #111111;">Bulk Batch CSV Ingestion</div>
                <div style="font-size: 0.82rem; color: #8A8A8A; margin-top: 2px;">
                    Upload production shipment manifests for atomic database ingestion. Invalid rows are safely rejected without corrupting database integrity.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_up, col_demo = st.columns([2, 1])

        with col_demo:
            st.markdown("**Sample Manifest File**")
            st.caption("Standard formatted batch shipment template (`data/sample_batches.csv`):")
            sample_path = Path("data/sample_batches.csv")
            if sample_path.exists():
                with open(sample_path, "r") as f:
                    st.download_button(
                        "📄 Download Sample CSV Template",
                        data=f.read(),
                        file_name="sample_batches.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

        with col_up:
            uploaded_file = st.file_uploader("Upload Shipment CSV File", type=["csv"])

        col_btn1, col_btn2 = st.columns([1, 2])
        with col_btn1:
            load_sample = st.button("⚡ Test Load Sample CSV", use_container_width=True)

        file_to_process = None
        if uploaded_file is not None:
            file_to_process = uploaded_file
        elif load_sample and sample_path.exists():
            file_to_process = sample_path

        if file_to_process is not None:
            with st.spinner("Parsing and validating batch records with Pydantic..."):
                success_count, errors = report_generator.ingest_batches_from_csv(file_to_process)

                if success_count > 0:
                    st.success(f"Transaction Committed: Successfully ingested {success_count} batches into MySQL!")
                if errors:
                    st.warning(f"Encountered {len(errors)} validation/transaction issues:")
                    for err in errors:
                        st.write(f"- {err}")

    # --- TAB 3: REGIONAL DISTRIBUTION DISPATCH ---
    with tab3:
        st.markdown(
            """
            <div class="pv-card" style="margin-bottom: 1.2rem;">
                <div style="font-size: 1.15rem; font-weight: 800; color: #111111;">Regional Hospital Distribution Dispatcher</div>
                <div style="font-size: 0.82rem; color: #8A8A8A; margin-top: 2px; margin-bottom: 16px;">
                    Authorize medication dispatches to licensed healthcare institutions. Automated regulatory checks block expired or recalled lots.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        try:
            all_batches = sql_service.get_batches()
            hospitals = sql_service.get_hospitals()
        except Exception:
            all_batches = []
            hospitals = []

        if not all_batches:
            all_batches = [{"batch_number": "BCH-PCM-9042", "commercial_name": "Cardiomax", "recall_status": "ACTIVE"}]
        if not hospitals:
            hospitals = [{"hospital_id": 1, "hospital_name": "St. Jude Memorial Hospital", "city": "Metropolis"}]

        batch_options = {f"{b['batch_number']} - {b['commercial_name']} ({b['recall_status']})": b for b in all_batches}
        hospital_options = {f"{h['hospital_name']} ({h['city']})": h for h in hospitals}

        with st.form("dispatch_form"):
            selected_batch_str = st.selectbox("Select Batch to Dispatch *", options=list(batch_options.keys()))
            selected_hosp_str = st.selectbox("Select Destination Hospital *", options=list(hospital_options.keys()))
            quantity = st.number_input("Quantity of Units to Deliver *", min_value=1, max_value=100000, value=2500, step=100)
            dispatch_date = st.date_input("Dispatch Date", value=date.today())

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            dispatch_submitted = st.form_submit_button("🚚 Confirm & Dispatch Stock", use_container_width=True)

        if dispatch_submitted:
            batch_obj = batch_options[selected_batch_str]
            hosp_obj = hospital_options[selected_hosp_str]

            try:
                sql_service.dispatch_batch_to_hospital(
                    batch_number=batch_obj["batch_number"],
                    hospital_id=hosp_obj["hospital_id"],
                    quantity=int(quantity),
                    dispatch_date=str(dispatch_date)
                )
                st.success(
                    f"Dispatched {quantity:,} units of {batch_obj['batch_number']} to {hosp_obj['hospital_name']}."
                )
            except ExpiredBatchDispenseError as e:
                st.error(f"🛑 Critical Safety Block (ExpiredBatchDispenseError): {str(e)}")
            except RecalledBatchOperationError as e:
                st.error(f"🛑 Critical Regulatory Block (RecalledBatchOperationError): {str(e)}")
            except Exception as e:
                st.error(f"Failed to record distribution: {str(e)}")
