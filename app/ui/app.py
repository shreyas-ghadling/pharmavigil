"""
Main Streamlit Application Shell for Pharmavigil
Coordinates user authentication, session state, role-based navigation, and portal rendering.
"""

import sys
from pathlib import Path

# Resolve directory paths
CURRENT_DIR = Path(__file__).resolve().parent  # app/ui
PROJECT_ROOT = CURRENT_DIR.parent.parent       # Project root

# Remove CURRENT_DIR (app/ui) from sys.path so Python never resolves app/ui/app.py as package 'app'
sys.path = [p for p in sys.path if Path(p).resolve() != CURRENT_DIR]

# Ensure PROJECT_ROOT is strictly first in sys.path
root_str = str(PROJECT_ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

# Ensure 'app' in sys.modules is the real package directory, not a script module
if "app" in sys.modules and not hasattr(sys.modules["app"], "__path__"):
    del sys.modules["app"]

import streamlit as st

from app.utils.auth import (
    authenticate_user,
    get_allowed_portals,
    ROLE_DOCTOR_PATIENT,
    ROLE_PHARMACIST,
    ROLE_SAFETY_OFFICER_ADMIN,
    DEMO_CREDENTIALS
)
from app.ui.page_patient import render_patient_portal
from app.ui.page_inventory import render_inventory_portal
from app.ui.page_admin import render_admin_portal
from app.database.mysql_client import mysql_client
from app.database.mongo_client import mongo_client

# Page Configuration
st.set_page_config(
    page_title="Pharmavigil - Medicine Safety Tracking",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Light Pharmacy Dashboard Theme)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-page: #F7F7F5;
    --bg-card: #FFFFFF;
    --text-primary: #111111;
    --text-muted: #8A8A8A;
    --accent-amber: #E5A50A;
    --accent-cream: #FEF3DC;
    --dark-element: #1A1A1A;
    --radius-card: 20px;
}

/* Base page background and typography */
html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: var(--bg-page) !important;
    color: var(--text-primary) !important;
}

/* Clean sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #EFEFED !important;
    box-shadow: 2px 0 16px rgba(0, 0, 0, 0.02) !important;
}
section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] {
    display: none !important;
}

/* Sidebar Section Headers (MENU, SETTINGS) */
.pv-sidebar-section {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin: 1.4rem 0 0.5rem 0.2rem;
}

/* Sidebar User Profile Card */
.pv-user-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 14px;
    background: #FAFAFA;
    border-radius: 16px;
    border: 1px solid #EFEFED;
    margin-bottom: 1.2rem;
}
.pv-user-avatar {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: #1A1A1A;
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.95rem;
}
.pv-user-details {
    display: flex;
    flex-direction: column;
}
.pv-user-name {
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
}
.pv-user-role-badge {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text-muted);
    margin-top: 2px;
}

/* Sidebar Navigation Items - Cream Pill #FEF3DC with Amber Accent */
div[data-testid="stRadio"] > div {
    gap: 6px !important;
}
div[data-testid="stRadio"] label {
    background: transparent !important;
    padding: 10px 14px !important;
    border-radius: 14px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    border: 1px solid transparent !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: #4A4A4A !important;
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
}
div[data-testid="stRadio"] label:hover {
    background-color: #F7F7F5 !important;
    color: #111111 !important;
}
div[data-testid="stRadio"] label:has(input:checked) {
    background-color: #FEF3DC !important;
    color: #111111 !important;
    font-weight: 700 !important;
    border: 1px solid #FDE6B0 !important;
}
div[data-testid="stRadio"] label input[type="radio"] {
    accent-color: #E5A50A !important;
}

/* Database Health Cards in Sidebar */
.pv-health-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 9px 12px;
    background: #FAFAFA;
    border: 1px solid #EFEFED;
    border-radius: 12px;
    margin-bottom: 6px;
    font-size: 0.82rem;
    color: var(--text-primary);
}
.pv-dot-connected {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10B981;
    margin-right: 6px;
}
.pv-dot-offline {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #F59E0B;
    margin-right: 6px;
}

/* Top Greeting, Header Title & Breadcrumb */
.pv-greeting {
    font-size: 1.25rem;
    font-weight: 600;
    color: #111111;
    margin-bottom: 0.4rem;
}
.pv-page-title {
    font-size: 2.1rem;
    font-weight: 800;
    color: #111111;
    letter-spacing: -0.02em;
    margin: 0;
    line-height: 1.15;
}
.pv-breadcrumb {
    font-size: 0.85rem;
    color: #8A8A8A;
    font-weight: 500;
    margin-top: 4px;
    margin-bottom: 1.4rem;
}

/* Rounded Pill Tabs Toggle (Matching Reference) */
div[data-testid="stTabs"] {
    margin-top: 0.8rem;
    margin-bottom: 1.5rem;
}
div[data-testid="stTabs"] > div[role="tablist"] {
    background-color: #ECECE9 !important;
    padding: 5px !important;
    border-radius: 9999px !important;
    display: inline-flex !important;
    gap: 4px !important;
    border-bottom: none !important;
}
div[data-testid="stTabs"] button[role="tab"] {
    border-radius: 9999px !important;
    padding: 8px 22px !important;
    font-size: 0.86rem !important;
    font-weight: 600 !important;
    color: #666666 !important;
    border: none !important;
    background-color: transparent !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background-color: #FFFFFF !important;
    color: #111111 !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
}
div[data-testid="stTabs"] button[role="tab"]:hover {
    color: #111111 !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
div[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
}

/* White Card Containers with 20px Radius */
.pv-card {
    background-color: #FFFFFF !important;
    border-radius: 20px !important;
    padding: 24px !important;
    border: 1px solid #EFEFED !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02) !important;
    margin-bottom: 1.5rem !important;
}

/* Metric Cards */
.pv-metric-card {
    background-color: #FFFFFF;
    border-radius: 20px;
    padding: 20px 22px;
    border: 1px solid #EFEFED;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.02);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 120px;
}
.pv-metric-title {
    color: #8A8A8A;
    font-size: 0.85rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.pv-metric-number {
    font-size: 2.3rem;
    font-weight: 800;
    color: #111111;
    letter-spacing: -0.02em;
    line-height: 1.2;
    margin: 8px 0;
}
.pv-metric-caption {
    color: #8A8A8A;
    font-size: 0.78rem;
    font-weight: 500;
}

/* Status Badges - Soft Pills */
.pv-pill {
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    letter-spacing: 0.02em;
}
.pv-pill-expired {
    background-color: #FDE8E8;
    color: #DC2626;
}
.pv-pill-warning {
    background-color: #FEF3C7;
    color: #D97706;
}
.pv-pill-active {
    background-color: #DEF7EC;
    color: #059669;
}
.pv-pill-recalled {
    background-color: #FEE2E2;
    color: #991B1B;
}

/* Monospace font */
.pv-mono {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
}

/* Custom Table Styling */
.pv-table-container {
    width: 100%;
    overflow-x: auto;
    margin-top: 1rem;
}
.pv-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.86rem;
    text-align: left;
}
.pv-table th {
    padding: 12px 16px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #8A8A8A;
    border-bottom: 1px solid #EFEFED;
    background-color: #FAFAFA;
}
.pv-table th:first-child {
    border-top-left-radius: 12px;
    border-bottom-left-radius: 12px;
}
.pv-table th:last-child {
    border-top-right-radius: 12px;
    border-bottom-right-radius: 12px;
}
.pv-table td {
    padding: 14px 16px;
    color: #111111;
    border-bottom: 1px solid #F0F0EE;
    vertical-align: middle;
}
.pv-table tr:last-child td {
    border-bottom: none;
}
.pv-table tbody tr {
    transition: background-color 0.15s ease;
}
.pv-table tbody tr:hover {
    background-color: #FBFBFA;
}

/* Action Buttons */
.stButton > button {
    background-color: #1A1A1A !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 10px 22px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background-color: #333333 !important;
    color: #FFFFFF !important;
    transform: translateY(-1px) !important;
}
.stDownloadButton > button {
    background-color: #FFFFFF !important;
    color: #111111 !important;
    border: 1px solid #E5E5E5 !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}
.stDownloadButton > button:hover {
    background-color: #F7F7F5 !important;
    border-color: #111111 !important;
}

/* Forms and Inputs */
div[data-testid="stForm"] {
    background-color: #FFFFFF !important;
    border-radius: 20px !important;
    padding: 26px !important;
    border: 1px solid #EFEFED !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02) !important;
}
.stTextInput > div > div, 
.stSelectbox > div > div, 
.stNumberInput > div > div, 
.stDateInput > div > div {
    background-color: #FAFAFA !important;
    border-radius: 12px !important;
    border: 1px solid #E5E5E5 !important;
    color: #111111 !important;
}
.stTextInput > div > div:focus-within, 
.stSelectbox > div > div:focus-within {
    border-color: #E5A50A !important;
    box-shadow: 0 0 0 1px #E5A50A !important;
}

/* Light Mode Alert Boxes */
div[data-testid="stAlert"] {
    border-radius: 14px !important;
    border: none !important;
    border-left: 4px solid !important;
    padding: 14px 18px !important;
    color: #111111 !important;
}
div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
    color: #111111 !important;
}
div[data-testid="stAlert"]:has([data-testid="stAlertErrorIcon"]) {
    background-color: #FEF2F2 !important;
    border-left-color: #DC2626 !important;
}
div[data-testid="stAlert"]:has([data-testid="stAlertWarningIcon"]) {
    background-color: #FFFBEB !important;
    border-left-color: #E5A50A !important;
}
div[data-testid="stAlert"]:has([data-testid="stAlertSuccessIcon"]) {
    background-color: #F0FDF4 !important;
    border-left-color: #16A34A !important;
}
div[data-testid="stAlert"]:has([data-testid="stAlertInfoIcon"]) {
    background-color: #F8FAFC !important;
    border-left-color: #0284C7 !important;
}
</style>
""", unsafe_allow_html=True)


def check_db_health():
    """Checks liveness of MySQL and MongoDB connections."""
    mysql_ok = False
    mongo_ok = False
    
    try:
        mysql_client.execute_one("SELECT 1;")
        mysql_ok = True
    except Exception:
        mysql_ok = False

    try:
        mongo_ok = mongo_client.ping()
    except Exception:
        mongo_ok = False

    return mysql_ok, mongo_ok


def render_login_screen():
    """Renders the Bcrypt authentication and login interface."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='main-header'>💊 Pharmavigil</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-header'>Drug Adverse Reaction & Medicine Safety Tracking System</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.subheader("🔐 Secure Portal Login")
            st.caption("Role-Based Access Control enforced with bcrypt hashed credentials.")

            with st.form("login_form"):
                username = st.text_input("Username", placeholder="e.g. doctor_smith, pharmacist_jane, admin_officer")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.warning("Please provide both username and password.")
                else:
                    user_data = authenticate_user(username, password)
                    if user_data:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user_data
                        st.success(f"Welcome back, {user_data['full_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please verify your username and password.")

            st.divider()
            st.markdown("**Quick Demo Logins (Click to pre-fill):**")
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                if st.button("👩‍⚕️ Doctor", use_container_width=True):
                    user_data = authenticate_user("doctor_smith", "doctor123")
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = user_data
                    st.rerun()
            with col_d2:
                if st.button("💊 Pharmacist", use_container_width=True):
                    user_data = authenticate_user("pharmacist_jane", "pharmacist123")
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = user_data
                    st.rerun()
            with col_d3:
                if st.button("🛡️ Admin", use_container_width=True):
                    user_data = authenticate_user("admin_officer", "admin123")
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = user_data
                    st.rerun()


def render_authenticated_app():
    """Renders the main authenticated dashboard with role-based portal switcher."""
    user = st.session_state["user"]
    allowed_portals = get_allowed_portals(user["role"])

    # Sidebar Navigation & Status
    with st.sidebar:
        # Brand Header
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1.2rem; padding-left: 4px;">
                <span style="font-size: 1.6rem;">💊</span>
                <div>
                    <div style="font-size: 1.2rem; font-weight: 800; color: #111111; letter-spacing: -0.02em;">Pharmavigil</div>
                    <div style="font-size: 0.72rem; color: #8A8A8A; font-weight: 500;">Medicine Safety Tracking</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # User Profile Card
        role_label = user['role'].replace('_', ' ').title()
        name_parts = [part for part in user['full_name'].split() if part]
        initials = "".join([p[0] for p in name_parts[:2]]) if name_parts else "PV"
        st.markdown(
            f"""
            <div class="pv-user-card">
                <div class="pv-user-avatar">{initials}</div>
                <div class="pv-user-details">
                    <div class="pv-user-name">{user['full_name']}</div>
                    <div class="pv-user-role-badge">{role_label}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown('<div class="pv-sidebar-section">MENU</div>', unsafe_allow_html=True)
        selected_portal = st.radio(
            "Navigation Portals",
            options=allowed_portals,
            index=0,
            label_visibility="collapsed"
        )

        st.markdown('<div class="pv-sidebar-section">SETTINGS</div>', unsafe_allow_html=True)
        mysql_status, mongo_status = check_db_health()
        
        mysql_dot = "pv-dot-connected" if mysql_status else "pv-dot-offline"
        mysql_txt = "Connected" if mysql_status else "Standby"
        mongo_dot = "pv-dot-connected" if mongo_status else "pv-dot-offline"
        mongo_txt = "Connected" if mongo_status else "Standby"

        st.markdown(
            f"""
            <div class="pv-health-card">
                <span><span class="{mysql_dot}"></span>MySQL Relational Core</span>
                <span style="font-weight: 700; color: {'#059669' if mysql_status else '#D97706'};">{mysql_txt}</span>
            </div>
            <div class="pv-health-card">
                <span><span class="{mongo_dot}"></span>MongoDB Telemetry</span>
                <span style="font-weight: 700; color: {'#059669' if mongo_status else '#D97706'};">{mongo_txt}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user"] = None
            st.rerun()

    # Top Greeting (Above page title)
    greeting_name = user.get("full_name", "Doctor / Pharmacist")
    st.markdown(
        f'<div class="pv-greeting">Good morning, {greeting_name}!</div>',
        unsafe_allow_html=True
    )

    # Server-side role authorization guard
    try:
        from app.utils.auth import verify_portal_access
        from app.utils.exceptions import UnauthorizedAccessError
        verify_portal_access(user["role"], selected_portal)
    except UnauthorizedAccessError as auth_err:
        st.error(f"🛑 Security Block (UnauthorizedAccessError): {str(auth_err)}")
        return

    # Render authorized portal
    if "Doctor & Patient" in selected_portal:
        render_patient_portal()
    elif "Hospital Pharmacist" in selected_portal:
        render_inventory_portal()
    elif "Safety Officer" in selected_portal:
        render_admin_portal()


def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["user"] = None

    if not st.session_state["authenticated"]:
        render_login_screen()
    else:
        render_authenticated_app()


if __name__ == "__main__":
    main()
