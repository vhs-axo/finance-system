import time

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIGURATION & THEME
# -----------------------------------------------------------------------------
API_URL = "http://127.0.0.1:8000"

# Theme Colors
PRIMARY_GREEN = "#006241"  # La Salle Green
SECONDARY_GOLD = "#FFC72C"  # School Gold
BG_LIGHT = "#F4F4F4"
TEXT_DARK = "#333333"

ROLES = {
    "admin": "Admin",
    "staff": "Finance Staff",
    "officer": "Finance Officer",
    "auditor": "Auditor",
    "it": "System Admin",
    "student": "Student",  # NEW ROLE ADDED
}

STRANDS = ["ABM", "STEM", "HUMSS", "General"]
CATEGORIES = {
    "Collection": ["Tuition Fee", "Miscellaneous Fee", "Organization Fund", "Donation"],
    "Disbursement": [
        "Utility Bill",
        "Teacher Salary",
        "Event Expense",
        "Maintenance",
        "Refund",
    ],
}


# -----------------------------------------------------------------------------
# CSS STYLING
# -----------------------------------------------------------------------------
def inject_custom_css():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;700&family=Roboto:wght@300;400;700&display=swap');

        .stApp {{
            background-color: {BG_LIGHT};
            font-family: 'Roboto', 'Arial', sans-serif;
            color: {TEXT_DARK};
        }}

        h1, h2, h3, h4 {{
            font-family: 'EB Garamond', 'Garamond', serif !important;
            color: {PRIMARY_GREEN} !important;
            font-weight: 700 !important;
        }}

        section[data-testid="stSidebar"] {{
            background-color: {PRIMARY_GREEN};
        }}
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{
            color: {SECONDARY_GOLD} !important;
        }}
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] div {{
            color: white !important;
        }}

        .stButton > button {{
            background-color: {SECONDARY_GOLD};
            color: {PRIMARY_GREEN};
            border-radius: 6px;
            border: none;
            padding: 0.6rem 1.2rem;
            font-weight: bold;
            font-family: 'Roboto', sans-serif;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stButton > button:hover {{
            background-color: #e5b020;
            color: #00402a;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}

        .css-card {{
            background-color: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 20px;
            border-top: 4px solid {SECONDARY_GOLD};
        }}

        .landing-header {{
            background: linear-gradient(135deg, {PRIMARY_GREEN} 0%, #004d33 100%);
            padding: 40px 20px;
            text-align: center;
            color: white;
            border-bottom: 6px solid {SECONDARY_GOLD};
            margin-bottom: 30px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }}
        .landing-title {{
            font-family: 'EB Garamond', serif !important;
            font-size: 3.5em;
            margin: 0;
            color: white !important;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }}
        .landing-subtitle {{
            font-family: 'Roboto', sans-serif;
            font-size: 1.2em;
            color: {SECONDARY_GOLD};
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 10px;
        }}

        div[data-testid="stMetricValue"] {{
            color: {PRIMARY_GREEN} !important;
            font-family: 'Roboto', sans-serif;
        }}

        .footer {{
            text-align: center;
            color: #888;
            font-size: 0.8rem;
            margin-top: 50px;
            padding: 20px;
            border-top: 1px solid #eee;
        }}
        </style>
    """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# API CLIENT HELPER
# -----------------------------------------------------------------------------
class ApiClient:
    """Helper to communicate with FastAPI backend"""

    @staticmethod
    def login(username, password):
        try:
            res = requests.post(
                f"{API_URL}/login", json={"username": username, "password": password}
            )
            return res.json()
        except Exception:
            return {
                "success": False,
                "message": "Server unavailable. Is backend running?",
            }

    @staticmethod
    def change_password(username, old_pass, new_pass):
        try:
            res = requests.post(
                f"{API_URL}/change-password",
                json={
                    "username": username,
                    "old_password": old_pass,
                    "new_password": new_pass,
                },
            )
            if res.status_code == 200:
                return True, res.json().get("message", "Success")
            else:
                return False, res.json().get("detail", "Failed")
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_stats():
        try:
            return requests.get(f"{API_URL}/stats").json()
        except Exception:
            return {}

    @staticmethod
    def get_transactions(student_id=None, status=None):
        params = {}
        if student_id:
            params["student_id"] = student_id
        if status:
            params["status"] = status
        try:
            return requests.get(f"{API_URL}/transactions", params=params).json()
        except Exception:
            return []

    @staticmethod
    def get_transaction_by_id(txn_id):
        try:
            res = requests.get(f"{API_URL}/transactions/{txn_id}")
            if res.status_code == 200:
                return res.json()
            return None
        except Exception:
            return None

    @staticmethod
    def create_transaction(data):
        try:
            res = requests.post(f"{API_URL}/transactions", json=data)
            return res.status_code == 200
        except Exception:
            return False

    @staticmethod
    def approve_transaction(txn_id, admin_username, action):
        try:
            data = {
                "txn_id": txn_id,
                "admin_username": admin_username,
                "action": action,
            }
            requests.put(f"{API_URL}/transactions/{txn_id}/approve", json=data)
            return True
        except Exception:
            return False

    @staticmethod
    def get_users():
        try:
            return requests.get(f"{API_URL}/users").json()
        except Exception:
            return []

    @staticmethod
    def create_user(data):
        try:
            res = requests.post(f"{API_URL}/users", json=data)
            return res.status_code == 200
        except Exception:
            return False

    @staticmethod
    def update_user(username, data):
        try:
            requests.put(f"{API_URL}/users/{username}", json=data)
            return True
        except Exception:
            return False


# -----------------------------------------------------------------------------
# PAGES
# -----------------------------------------------------------------------------


def login_page():
    st.markdown(
        """
        <div class="landing-header">
            <h1 class="landing-title">La Salle Academy</h1>
            <div class="landing-subtitle">Financial Transparency Portal</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([7, 5], gap="large")

    with c1:
        st.markdown(
            f"""
            <div style="padding: 20px;">
                <h2 style="color: {PRIMARY_GREEN}; font-size: 2em; margin-bottom: 20px;">
                    Integrity. Accountability. Excellence.
                </h2>
                <p style="font-size: 1.1em; line-height: 1.6; color: #555;">
                    Welcome to the official financial system of La Salle Academy. This platform leverages
                    secure, immutable ledger technology to provide real-time tracking of school fees
                    and operational expenses.
                </p>

                <div style="display: flex; gap: 20px; margin-top: 30px;">
                    <div class="css-card" style="flex: 1; text-align: center; border-top-color: {PRIMARY_GREEN};">
                        <div style="font-size: 2em;">🔒</div>
                        <h4 style="margin: 10px 0;">Secure</h4>
                        <p style="font-size: 0.9em;">Immutable audit trails</p>
                    </div>
                    <div class="css-card" style="flex: 1; text-align: center; border-top-color: {PRIMARY_GREEN};">
                        <div style="font-size: 2em;">📊</div>
                        <h4 style="margin: 10px 0;">Transparent</h4>
                        <p style="font-size: 0.9em;">Real-time reporting</p>
                    </div>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="css-card" style="border-top: 5px solid {SECONDARY_GOLD}; padding-top: 30px;">
                <h3 style="text-align: center; margin-bottom: 20px;">System Login</h3>
        """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            username = st.text_input(
                "Username / Student ID", placeholder="e.g. S-2024-001 or admin"
            )
            password = st.text_input("Password", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("Sign In", use_container_width=True)

        if submit:
            with st.spinner("Authenticating..."):
                resp = ApiClient.login(username, password)
                if resp.get("success"):
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = resp["role"]
                    st.session_state["username"] = username
                    st.session_state["name"] = resp["name"]
                    st.success("Success! Redirecting...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(resp.get("message", "Login failed"))

        st.markdown(
            """
                <div style="text-align: center; margin-top: 20px; font-size: 0.9em;">
                    <p style="color: #888;">For verification only?</p>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        if st.button("Guest Verification Tool", use_container_width=True):
            st.session_state["logged_in"] = True
            st.session_state["role"] = "guest"
            st.session_state["username"] = "Guest"
            st.session_state["name"] = "Guest User"
            st.rerun()

    st.markdown(
        """
        <div class="footer">
            &copy; 2025 La Salle Academy. All Rights Reserved. <br>
            Powered by Immudb Secure Ledger.
        </div>
    """,
        unsafe_allow_html=True,
    )


def dashboard_page():
    # Title adapts to role
    title = (
        "Transparency Board"
        if st.session_state["role"] == "student"
        else "Financial Dashboard"
    )
    st.markdown(f"<h2>📊 {title}</h2>", unsafe_allow_html=True)

    if st.session_state["role"] == "student":
        st.markdown(
            """
            <div class="css-card">
                <p><strong>Transparency Note:</strong> This board shows the aggregate financial status of the entire school.
                It allows you to see where collected funds are allocated (tuition, misc, orgs) vs expenses.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.write(f"Welcome back, **{st.session_state['name']}**")

    col_act, col_ref = st.columns([4, 1])
    with col_ref:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    stats = ApiClient.get_stats()
    if not stats:
        st.warning("Unable to fetch live statistics. Backend may be offline.")
        return

    # Metrics Row
    c1, c2, c3, c4 = st.columns(4)

    def metric_tile(col, label, value):
        with col:
            st.markdown(
                f"""
                <div class="css-card" style="padding: 15px; text-align: center; border-left: 5px solid {SECONDARY_GOLD}; border-top: none;">
                    <div style="font-size: 0.85em; color: #888; text-transform: uppercase; letter-spacing: 0.5px;">{label}</div>
                    <div style="font-size: 1.6em; color: {PRIMARY_GREEN}; font-weight: bold; margin: 5px 0;">{value}</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

    metric_tile(c1, "Total Tuition", f"₱{stats.get('total_tuition', 0):,.2f}")
    metric_tile(c2, "Miscellaneous", f"₱{stats.get('total_misc', 0):,.2f}")
    metric_tile(c3, "Org Funds", f"₱{stats.get('total_org', 0):,.2f}")

    # Hide Pending Counts for students to keep it clean, show for admins
    if st.session_state["role"] == "student":
        metric_tile(c4, "Total Expenses", f"₱{stats.get('total_expenses', 0):,.2f}")
    else:
        metric_tile(c4, "Pending Actions", stats.get("pending_count", 0))

    # Charts
    txns = ApiClient.get_transactions()
    if txns:
        df = pd.DataFrame(txns)

        c_left, c_right = st.columns(2)

        with c_left:
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            st.subheader("Revenue vs Expenses")
            if not df.empty:
                pie_data = df.groupby("txn_type")["amount"].sum().reset_index()
                fig1 = px.pie(
                    pie_data,
                    values="amount",
                    names="txn_type",
                    color_discrete_sequence=[
                        PRIMARY_GREEN,
                        SECONDARY_GOLD,
                        "#2E8B57",
                        "#DAA520",
                    ],
                )
                fig1.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig1, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c_right:
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            st.subheader("Collection by Strand")
            if not df.empty:
                bar_data = (
                    df[df["txn_type"] == "Collection"]
                    .groupby("strand")["amount"]
                    .sum()
                    .reset_index()
                )
                fig2 = px.bar(
                    bar_data,
                    x="strand",
                    y="amount",
                    color_discrete_sequence=[PRIMARY_GREEN],
                )
                fig2.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig2, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Data Table
        if st.session_state["role"] != "student":
            st.markdown('<div class="css-card">', unsafe_allow_html=True)
            st.subheader("Recent School Transactions")
            st.dataframe(
                df[
                    ["id", "created_at", "txn_type", "amount", "status", "recorded_by"]
                ].head(5),
                use_container_width=True,
            )

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Full CSV Report", csv, "financial_report.csv", "text/csv"
            )
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No transaction data available.")


def student_ledger_page():
    """Student Specific View"""
    st.markdown("<h2>📒 My Financial Ledger</h2>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="css-card">
            <h4>Student: {st.session_state["name"]}</h4>
            <p style="color: #666;">ID: {st.session_state["username"]}</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Fetch ONLY this student's transactions
    my_txns = ApiClient.get_transactions(student_id=st.session_state["username"])

    if my_txns:
        df = pd.DataFrame(my_txns)

        # Calculate totals
        total_paid = df[df["status"] == "Approved"]["amount"].sum()
        pending = df[df["status"] == "Pending"]["amount"].sum()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f"""
                <div class="css-card" style="border-left: 5px solid {PRIMARY_GREEN}; text-align: center;">
                    <div style="font-size: 0.9em; color: #888;">TOTAL PAID</div>
                    <div style="font-size: 1.8em; color: {PRIMARY_GREEN}; font-weight: bold;">₱{total_paid:,.2f}</div>
                </div>
            """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="css-card" style="border-left: 5px solid orange; text-align: center;">
                    <div style="font-size: 0.9em; color: #888;">PENDING VALIDATION</div>
                    <div style="font-size: 1.8em; color: orange; font-weight: bold;">₱{pending:,.2f}</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown('<div class="css-card">', unsafe_allow_html=True)
        st.subheader("Transaction History")

        # Display readable table
        display_df = df[
            [
                "created_at",
                "category",
                "description",
                "amount",
                "status",
                "proof_reference",
                "id",
            ]
        ]
        st.dataframe(display_df, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.info("No records found linked to your Student ID.")


def transaction_entry_page():
    st.markdown("<h2>📝 New Transaction</h2>", unsafe_allow_html=True)

    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    with st.form("entry_form"):
        c1, c2 = st.columns(2)
        txn_type = c1.selectbox("Transaction Type", ["Collection", "Disbursement"])
        strand = c2.selectbox("Strand", STRANDS)
        category = st.selectbox("Category", CATEGORIES[txn_type])
        student_id = st.text_input(
            "Student ID (Optional)", placeholder="e.g., S-2024-001"
        )
        desc = st.text_area("Description / Particulars")
        amount = st.number_input("Amount (PHP)", min_value=0.0, step=0.01)
        proof = st.text_input("Reference/Receipt #")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Submit to Ledger"):
            data = {
                "recorded_by": st.session_state["username"],
                "txn_type": txn_type,
                "strand": strand,
                "category": category,
                "description": desc,
                "amount": amount,
                "student_id": student_id,
                "proof_reference": proof,
            }
            if ApiClient.create_transaction(data):
                st.success(
                    "Transaction successfully recorded! It is now pending approval."
                )
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("Failed to record transaction.")
    st.markdown("</div>", unsafe_allow_html=True)


def audit_trail_page():
    st.markdown("<h2>📜 Immutable Audit Trail</h2>", unsafe_allow_html=True)

    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    search_student = c1.text_input("Search by Student ID")
    filter_status = c2.selectbox(
        "Filter Status", ["All", "Pending", "Approved", "Rejected"]
    )

    status_param = None if filter_status == "All" else filter_status
    txns = ApiClient.get_transactions(student_id=search_student, status=status_param)

    if txns:
        df = pd.DataFrame(txns)
        cols = [
            "id",
            "created_at",
            "status",
            "txn_type",
            "amount",
            "student_id",
            "recorded_by",
            "proof_reference",
        ]
        st.dataframe(df[cols], use_container_width=True)
    else:
        st.info("No records found matching filters.")
    st.markdown("</div>", unsafe_allow_html=True)


def verification_page():
    st.markdown("<h2>🔍 Verification Tool</h2>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="css-card">
            <h4 style="color:{TEXT_DARK} !important;">Verify a Receipt</h4>
            <p>Enter the unique Transaction ID to check its validity against the immutable ledger.</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 2])
    with c1:
        txn_id_input = st.number_input("Transaction ID", min_value=1, step=1)

    with c2:
        st.write("")  # Spacer
        st.write("")
        if st.button("Verify Now"):
            with st.spinner("Querying Ledger..."):
                txn = ApiClient.get_transaction_by_id(txn_id_input)
                if txn:
                    st.success("✅ Transaction Found & Verified")

                    st.markdown(
                        f"""
                        <div style="background-color: #fff; border: 2px solid {PRIMARY_GREEN}; padding: 30px; border-radius: 8px; margin-top: 20px;">
                            <div style="text-align: center; border-bottom: 1px solid #ddd; padding-bottom: 15px; margin-bottom: 15px;">
                                <h3 style="margin: 0;">OFFICIAL RECEIPT</h3>
                                <div style="color: #666; font-size: 0.9em;">La Salle Academy Finance</div>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 10px;">
                                <strong>ID:</strong> <span>{txn["id"]}</span>
                                <strong>Date:</strong> <span>{txn["created_at"]}</span>
                                <strong>Amount:</strong> <span style="font-size: 1.2em; font-weight: bold; color: {PRIMARY_GREEN};">₱{txn["amount"]:,.2f}</span>
                                <strong>Type:</strong> <span>{txn["txn_type"]} ({txn["category"]})</span>
                                <strong>Ref #:</strong> <span>{txn["proof_reference"]}</span>
                                <strong>Status:</strong> <span>{txn["status"]}</span>
                            </div>
                            <div style="margin-top: 20px; text-align: center; font-size: 0.8em; color: #888;">
                                Digital Signature Verified by Immudb
                            </div>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.error("❌ Transaction Not Found. Please check the ID.")


def pending_approvals_page():
    st.markdown("<h2>✅ Pending Approvals</h2>", unsafe_allow_html=True)
    txns = ApiClient.get_transactions(status="Pending")

    if not txns:
        st.info("No transactions waiting for approval.")
        return

    for txn in txns:
        with st.expander(
            f"#{txn['id']} - {txn['txn_type']} - ₱{txn['amount']:,.2f} ({txn['recorded_by']})"
        ):
            c1, c2 = st.columns(2)
            c1.write(f"**Desc:** {txn['description']}")
            c1.write(f"**Ref:** {txn['proof_reference']}")
            c2.write(f"**Cat:** {txn['category']}")
            c2.write(f"**Student:** {txn['student_id']}")

            b1, b2, b3 = st.columns([1, 1, 3])
            if b1.button("Approve", key=f"app_{txn['id']}"):
                if ApiClient.approve_transaction(
                    txn["id"], st.session_state["username"], "Approve"
                ):
                    st.success("Approved!")
                    time.sleep(0.5)
                    st.rerun()

            if b2.button("Reject", key=f"rej_{txn['id']}"):
                if ApiClient.approve_transaction(
                    txn["id"], st.session_state["username"], "Reject"
                ):
                    st.warning("Rejected.")
                    time.sleep(0.5)
                    st.rerun()


def user_management_page():
    st.markdown("<h2>👥 User Management</h2>", unsafe_allow_html=True)

    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["View Users", "Add New User"])

    with tab1:
        users = ApiClient.get_users()
        if users:
            df = pd.DataFrame(users)
            st.dataframe(df, use_container_width=True)

            st.markdown("#### Manage Access")
            c_sel, c_btn = st.columns([3, 1])
            target_user = c_sel.selectbox("Select User", [u["username"] for u in users])
            if c_btn.button("Toggle Status"):
                current_status = next(
                    (u["active"] for u in users if u["username"] == target_user), True
                )
                ApiClient.update_user(target_user, {"active": not current_status})
                st.success(f"Status for {target_user} toggled.")
                time.sleep(1)
                st.rerun()

    with tab2:
        with st.form("new_user_form"):
            new_user = st.text_input("Username")
            new_name = st.text_input("Full Name")
            new_pass = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ROLES.keys())

            if st.form_submit_button("Create User"):
                if new_user and new_pass:
                    data = {
                        "username": new_user,
                        "password": new_pass,
                        "name": new_name,
                        "role": new_role,
                        "active": True,
                    }
                    if ApiClient.create_user(data):
                        st.success("User created successfully!")
                    else:
                        st.error("Failed. Username might exist.")
    st.markdown("</div>", unsafe_allow_html=True)


def settings_page():
    st.markdown("<h2>⚙️ Settings</h2>", unsafe_allow_html=True)

    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.subheader("Security")
    with st.form("pwd_change"):
        old = st.text_input("Current Password", type="password")
        new = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")

        if st.form_submit_button("Update Password"):
            if new != confirm:
                st.error("New passwords do not match.")
            elif not old or not new:
                st.error("All fields are required.")
            else:
                success, msg = ApiClient.change_password(
                    st.session_state["username"], old, new
                )
                if success:
                    st.success("Password updated.")
                else:
                    st.error(f"Error: {msg}")
    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# MAIN APP LOOP
# -----------------------------------------------------------------------------


def main():
    st.set_page_config(
        page_title="LSA Financial Portal",
        layout="wide",
        page_icon="🏛️",
        initial_sidebar_state="expanded",
    )

    # Apply Custom CSS
    inject_custom_css()

    # Initialize Session
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # Routing
    if not st.session_state["logged_in"]:
        login_page()
    else:
        # Sidebar branding
        with st.sidebar:
            st.markdown(
                f"""
                <div style="text-align: center; margin-bottom: 20px; padding: 10px;">
                    <div style="font-size: 3em; line-height: 1;">🏛️</div>
                    <h2 style="color: {SECONDARY_GOLD} !important; margin: 10px 0;">La Salle Academy</h2>
                    <p style="color: #ccc; font-size: 0.9em; margin: 0;">Financial Portal</p>
                </div>
                <hr style="border-top: 1px solid rgba(255,255,255,0.2);">
            """,
                unsafe_allow_html=True,
            )

            st.caption(f"Logged in as: {st.session_state['name']}")

        role = st.session_state["role"]

        # Build Navigation based on Role
        options = []

        # Dashboard is "Transparency Board" for students
        if role == "student":
            options.append("Transparency Board")
            options.append("My Ledger")
        elif role != "guest":
            options.append("Dashboard")

        if role not in ["student", "guest"]:
            options.append("Audit Trail")

        # Only staff/admins add transactions
        if role in ["staff", "admin", "officer"]:
            options.insert(1, "New Transaction")

        if role == "admin":
            options.append("Pending Approvals")

        if role == "it":
            options.append("User Management")

        # Common Tools
        options.append("Verification")

        if role != "guest":
            options.append("Settings")

        options.append("Logout")

        choice = st.sidebar.radio("Main Menu", options)

        # Page Render
        if choice == "Dashboard" or choice == "Transparency Board":
            dashboard_page()
        elif choice == "My Ledger":
            student_ledger_page()
        elif choice == "New Transaction":
            transaction_entry_page()
        elif choice == "Pending Approvals":
            pending_approvals_page()
        elif choice == "Audit Trail":
            audit_trail_page()
        elif choice == "Verification":
            verification_page()
        elif choice == "User Management":
            user_management_page()
        elif choice == "Settings":
            settings_page()
        elif choice == "Logout":
            st.session_state["logged_in"] = False
            st.rerun()


if __name__ == "__main__":
    main()
