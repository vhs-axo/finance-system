import time
from io import BytesIO

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIGURATION & THEME
# -----------------------------------------------------------------------------
API_URL = "http://127.0.0.1:8000"

# La Salle Academy Theme Colors
PRIMARY_GREEN = "#006241"  # La Salle Green
SECONDARY_GOLD = "#FFC72C"  # School Gold
ACCENT_GREEN = "#004d33"   # Darker Green for hover/active states
BG_LIGHT = "#F9FAFB"       # Very light gray for background
TEXT_DARK = "#1F2937"      # Dark charcoal for text
WHITE = "#FFFFFF"

ROLES = {
    "admin": "Admin / Principal",
    "staff": "Finance Staff",
    "officer": "Finance Officer",
    "auditor": "Auditor",
    "it": "System Administrator",
    "student": "Student",
    "guest": "Guest"
}

STRANDS = ["ABM", "STEM", "HUMSS", "General"]
CATEGORIES = {
    "Collection": ["Tuition Fee", "Miscellaneous Fee", "Organization Fund", "Donation", "Other"],
    "Disbursement": [
        "Utility Bill",
        "Teacher Salary",
        "Event Expense",
        "Maintenance",
        "Refund",
        "Other"
    ],
}


# -----------------------------------------------------------------------------
# CSS STYLING (La Salle Theme)
# -----------------------------------------------------------------------------
def inject_custom_css():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600;700&family=Roboto:wght@300;400;500;700&display=swap');
        
        /* FORCE LIGHT THEME BACKGROUND */
        .stApp {{
            background-color: {BG_LIGHT};
        }}
        
        /* --- TEXT VISIBILITY FIXES --- */
        /* Force specific elements to use dark text to prevent White-on-White issues */
        
        /* General Text, Paragraphs, Lists */
        .stMarkdown p, .stMarkdown li, .stText, p {{
            color: {TEXT_DARK} !important;
            font-family: 'Roboto', sans-serif;
        }}
        
        /* Labels for Inputs */
        .stTextInput label, .stNumberInput label, .stSelectbox label, .stTextArea label, .stFileUploader label {{
            color: {TEXT_DARK} !important;
            font-weight: 500;
        }}

        /* Input Fields - Text Color inside boxes */
        .stTextInput input, .stNumberInput input, .stTextArea textarea {{
            color: {TEXT_DARK} !important;
            -webkit-text-fill-color: {TEXT_DARK} !important;
            caret-color: {TEXT_DARK} !important;
        }}
        
        /* Selectbox Text */
        div[data-baseweb="select"] div {{
            color: {TEXT_DARK} !important;
        }}

        /* --- HEADERS --- */
        h1, h2, h3, h4, .stHeading, h1 span, h2 span, h3 span {{
            font-family: 'EB Garamond', serif !important;
            color: {PRIMARY_GREEN} !important;
            font-weight: 700 !important;
        }}
        
        /* --- BUTTONS --- */
        .stButton > button {{
            background-color: {PRIMARY_GREEN} !important;
            color: {WHITE} !important;
            border-radius: 6px !important;
            border: 1px solid {PRIMARY_GREEN} !important;
            padding: 0.6rem 1.2rem !important;
            font-family: 'Roboto', sans-serif !important;
            font-weight: 500 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        }}
        
        /* Ensure text inside button is white */
        .stButton > button p {{
            color: {WHITE} !important;
        }}
        
        .stButton > button:hover {{
            background-color: {ACCENT_GREEN} !important;
            border-color: {SECONDARY_GOLD} !important;
            color: {SECONDARY_GOLD} !important;
        }}
        
        /* --- TABLES --- */
        /* Header Background */
        thead tr th {{
            background-color: {PRIMARY_GREEN} !important;
        }}
        /* Header Text */
        thead tr th span {{
            color: {WHITE} !important;
        }}
        /* Body Text */
        tbody tr td {{
            color: {TEXT_DARK} !important;
        }}
        
        /* --- SIDEBAR --- */
        section[data-testid="stSidebar"] {{
            background-color: {WHITE};
            border-right: 1px solid #E5E7EB;
        }}
        section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span {{
            color: {TEXT_DARK} !important;
        }}
        
        /* --- METRIC CARDS --- */
        .metric-card {{
            background-color: {WHITE};
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 6px solid {SECONDARY_GOLD};
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        .metric-label {{
            font-size: 0.85rem;
            color: #6B7280 !important; /* Slightly lighter gray for label */
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
            font-family: 'Roboto', sans-serif;
            font-weight: 600;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: {PRIMARY_GREEN} !important;
            font-family: 'EB Garamond', serif !important;
        }}
        
        /* ALERTS */
        .stAlert {{
            background-color: #F0FDF4;
            border: 1px solid {PRIMARY_GREEN};
            color: {TEXT_DARK} !important;
        }}
        
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# UTILITIES
# -----------------------------------------------------------------------------
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()


# -----------------------------------------------------------------------------
# PAGES
# -----------------------------------------------------------------------------

def login_page():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown(
            f"""
            <div style='text-align: center; margin-bottom: 2rem; padding-top: 4rem;'>
                <div style='width: 90px; height: 90px; background-color: {PRIMARY_GREEN}; border-radius: 50%; margin: 0 auto 1.5rem; display: flex; align-items: center; justify-content: center; color: white; font-size: 2.2rem; font-family: "EB Garamond", serif; border: 4px solid {SECONDARY_GOLD}; box-shadow: 0 4px 10px rgba(0,0,0,0.1);'>
                    LA
                </div>
                <h1 style='color: {PRIMARY_GREEN} !important; margin-bottom: 0.2rem; font-size: 2.5rem;'>La Salle Academy</h1>
                <h3 style='color: #4B5563 !important; font-family: Roboto; font-weight: 300; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 1px;'>Financial Transparency System</h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        with st.form("login_form"):
            st.markdown("<div style='margin-bottom: 1.5rem; text-align: center; color: #666 !important; font-size: 0.95rem;'>Please sign in to access the portal</div>", unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Enter your ID/Username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("SIGN IN", use_container_width=True)

            if submitted:
                try:
                    res = requests.post(
                        f"{API_URL}/login",
                        json={"username": username, "password": password},
                    )
                    data = res.json()
                    if data.get("success"):
                        st.session_state["logged_in"] = True
                        st.session_state["role"] = data.get("role")
                        st.session_state["username"] = username
                        st.session_state["name"] = data.get("name")
                        st.success(f"Welcome back, {data.get('name')}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(data.get("message", "Login failed"))
                except Exception as e:
                    st.error(f"Connection Error: {e}")

        # Guest access
        st.markdown(
            """
            <div style='text-align: center; margin-top: 1.5rem;'>
                <span style='color: #9CA3AF !important; font-size: 0.85rem;'>Public Access? </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("View Transparency Board (Guest)", use_container_width=True):
            st.session_state["logged_in"] = True
            st.session_state["role"] = "guest"
            st.session_state["name"] = "Guest Visitor"
            st.rerun()


def dashboard_page():
    st.title("📊 Financial Dashboard")
    st.markdown(f"Overview of **Senior High School** financial activities.")
    st.markdown("---")
    
    # 1. Fetch Statistics
    try:
        stats_res = requests.get(f"{API_URL}/stats")
        stats = stats_res.json() if stats_res.status_code == 200 else {}
    except:
        stats = {}

    # Display Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""<div class='metric-card'>
            <div class='metric-label'>Tuition Fees</div>
            <div class='metric-value'>₱{stats.get('total_tuition', 0):,.2f}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""<div class='metric-card'>
            <div class='metric-label'>Misc. Fees</div>
            <div class='metric-value'>₱{stats.get('total_misc', 0):,.2f}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""<div class='metric-card'>
            <div class='metric-label'>Org. Funds</div>
            <div class='metric-value'>₱{stats.get('total_org', 0):,.2f}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""<div class='metric-card'>
            <div class='metric-label'>Expenses</div>
            <div class='metric-value' style='color: #B91C1C !important;'>₱{stats.get('total_expenses', 0):,.2f}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Financial Breakdown by Strand")
        try:
            # Fetch all transactions for visualization
            res = requests.get(f"{API_URL}/transactions")
            if res.status_code == 200:
                txns = res.json()
                if txns:
                    df = pd.DataFrame(txns)
                    df = df[df['status'] != 'Rejected']
                    
                    # Colors: Green for Collection, Red/Gold for Disbursement
                    color_map = {"Collection": PRIMARY_GREEN, "Disbursement": "#B91C1C"}
                    
                    fig_bar = px.bar(
                        df, x="strand", y="amount", color="txn_type", 
                        barmode="group", 
                        color_discrete_map=color_map,
                        labels={"amount": "Amount (PHP)", "strand": "Strand"}
                    )
                    fig_bar.update_layout(
                        plot_bgcolor="white",
                        font_family="Roboto",
                        paper_bgcolor="white",
                        font=dict(color=TEXT_DARK)
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("No transaction data available.")
        except Exception as e:
            st.error(f"Error loading charts: {e}")

    with col2:
        st.subheader("Fund Distribution")
        if 'df' in locals() and not df.empty:
            st.download_button(
                label="📥 Export Report (Excel)",
                data=convert_df_to_excel(df),
                file_name='financial_report.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True
            )
            
            fig_pie = px.pie(
                df, names="category", values="amount", 
                color_discrete_sequence=px.colors.sequential.Greens_r
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(font_family="Roboto", font=dict(color=TEXT_DARK))
            st.plotly_chart(fig_pie, use_container_width=True)


def transaction_entry_page():
    st.title("📝 Transaction Management")
    st.markdown("Record and view recent transactions.")
    st.markdown("---")

    # Split View: Left (Form) | Right (List)
    col_form, col_list = st.columns([1, 1.5], gap="large")

    # --- LEFT SIDE: INPUT FORM ---
    with col_form:
        st.markdown(f"#### New Entry")
        st.caption("All fields are required.")
        
        with st.form("txn_form", clear_on_submit=True):
            txn_type = st.selectbox("Transaction Type", ["Collection", "Disbursement"])
            
            c1, c2 = st.columns(2)
            with c1:
                strand = st.selectbox("Strand", STRANDS)
            with c2:
                # Dynamic categories logic could be improved with JS, but pure python reload is needed
                cat_options = CATEGORIES.get(txn_type, [])
                category = st.selectbox("Category", cat_options)
            
            amount = st.number_input("Amount (PHP)", min_value=0.0, step=0.01)
            student_id = st.text_input("Student ID (If applicable)")
            description = st.text_area("Description / Purpose")

            uploaded_file = st.file_uploader("Attach Proof (Receipt/Slip)", type=['png', 'jpg', 'jpeg', 'pdf'])
            
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Submit Record", use_container_width=True)
            
            if submitted:
                proof_ref = None
                
                # File Upload Handler
                if uploaded_file is not None:
                    with st.spinner("Uploading proof..."):
                        try:
                            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                            upload_res = requests.post(f"{API_URL}/files/upload", files=files)
                            if upload_res.status_code == 200:
                                proof_ref = upload_res.json().get("path")
                            else:
                                st.error("Failed to upload receipt.")
                                st.stop()
                        except Exception as e:
                            st.error(f"Upload error: {e}")
                            st.stop()

                payload = {
                    "recorded_by": st.session_state.get("username", "unknown"),
                    "txn_type": txn_type,
                    "strand": strand,
                    "category": category,
                    "description": description,
                    "amount": amount,
                    "student_id": student_id,
                    "proof_reference": proof_ref
                }
                
                try:
                    res = requests.post(f"{API_URL}/transactions", json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        status = data.get("status", "Unknown")
                        
                        st.success(f"✅ Recorded Successfully! Status: {status}")
                        if status == "Approved":
                             st.info("Collection recorded and verified automatically.")
                        else:
                             st.info("Disbursement request submitted for approval.")
                    else:
                        st.error(f"Error: {res.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")

    # --- RIGHT SIDE: RECENT LIST ---
    with col_list:
        st.markdown(f"#### Recent Records")
        st.caption("Most recent transactions.")
        
        try:
            res = requests.get(f"{API_URL}/transactions?limit=10")
            if res.status_code == 200:
                txns = res.json()
                if txns:
                    df = pd.DataFrame(txns)
                    # Simplified table for sidebar view
                    display_df = df[['created_at', 'category', 'amount', 'status']]
                    display_df.columns = ['Date', 'Category', 'Amount', 'Status']
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No records found.")
        except:
            st.error("Could not load recent records.")


def pending_approvals_page():
    st.title("⏳ Pending Approvals")
    st.markdown("Review and approve transaction requests.")
    st.markdown("---")
    
    try:
        res = requests.get(f"{API_URL}/transactions?status=Pending")
        pending = res.json() if res.status_code == 200 else []
            
        if not pending:
            st.info("✅ All caught up! No pending transactions.")
            return

        for txn in pending:
            with st.container():
                st.markdown(f"##### {txn['category']} - ₱{txn['amount']:,.2f}")
                
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.caption(f"Recorded by: {txn['recorded_by']} | Date: {txn['created_at']}")
                    st.text(f"Note: {txn['description']}")
                    if txn.get('proof_reference'):
                        st.markdown(f"📎 [View Attachment]({API_URL}/{txn['proof_reference']})")
                
                with c2:
                    if st.button("Approve", key=f"app_{txn['id']}", use_container_width=True):
                        payload = {"admin_username": st.session_state["username"], "action": "Approve"}
                        r = requests.put(f"{API_URL}/transactions/{txn['id']}/approve", json=payload)
                        if r.status_code == 200:
                            st.success("Approved!")
                            time.sleep(0.5)
                            st.rerun()
                with c3:
                    if st.button("Reject", key=f"rej_{txn['id']}", use_container_width=True):
                        payload = {"admin_username": st.session_state["username"], "action": "Reject"}
                        r = requests.put(f"{API_URL}/transactions/{txn['id']}/approve", json=payload)
                        if r.status_code == 200:
                            st.warning("Rejected.")
                            time.sleep(0.5)
                            st.rerun()
                st.divider()

    except Exception as e:
        st.error(f"Connection Error: {e}")


def audit_trail_page():
    st.title("🔍 Audit Trail")
    st.markdown("Immutable record of all transactions secured by **Immudb**.")
    st.markdown("---")

    try:
        res = requests.get(f"{API_URL}/transactions")
        if res.status_code == 200:
            data = res.json()
            if data:
                df = pd.DataFrame(data)
                
                # Show hash prominently
                st.markdown("##### 🧾 Complete Ledger")
                st.dataframe(
                    df[["id", "created_at", "txn_type", "amount", "status", "tx_hash"]], 
                    use_container_width=True
                )

                st.download_button(
                    label="📥 Download Official Audit Log",
                    data=convert_df_to_excel(df),
                    file_name='audit_trail_log.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
            else:
                st.info("No records found.")
        else:
            st.error("Failed to fetch audit trail.")
    except Exception as e:
        st.error(f"Connection error: {e}")


def student_ledger_page():
    st.title("📖 My Ledger")
    st.markdown("Check your personal transaction history.")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        sid = st.text_input("Enter Student ID:", placeholder="e.g., 2023-0001")
    
    if sid:
        try:
            res = requests.get(f"{API_URL}/transactions?student_id={sid}")
            if res.status_code == 200:
                data = res.json()
                if data:
                    df = pd.DataFrame(data)
                    st.success(f"Found {len(data)} records.")
                    st.table(df[["created_at", "category", "description", "amount", "status"]])
                else:
                    st.warning("No records found for this Student ID.")
            else:
                st.error("Search failed.")
        except Exception as e:
            st.error(f"Error: {e}")


def verification_page():
    st.title("✅ Verification")
    st.markdown("Cryptographically verify data integrity against the immutable ledger.")
    st.markdown("---")
    
    txn_id = st.text_input("Enter Transaction ID:", placeholder="e.g., 105")
    
    if st.button("Verify Integrity", type="primary"):
        if not txn_id:
            st.warning("Please enter an ID.")
            return
            
        try:
            with st.spinner("Querying Immudb Verification Proof..."):
                res = requests.get(f"{API_URL}/verify/{txn_id}")
                
                if res.status_code == 200:
                    data = res.json()
                    st.success("✅ INTEGRITY CONFIRMED")
                    
                    st.markdown("### Proof Details")
                    st.json(data)
                    st.success("The cryptographic proof returned by the database matches the local Merkle Root. This record has NOT been tampered with.")
                else:
                    st.error("❌ VERIFICATION FAILED")
                    st.error("The record does not match the cryptographic proof. Potential tampering detected.")
        except Exception as e:
            st.error(f"Connection Error: {e}")


def settings_page():
    st.title("⚙️ Settings")
    st.markdown(f"Manage account for **{st.session_state.get('name')}**")
    st.markdown("---")
    
    with st.form("change_pass"):
        st.subheader("Change Password")
        new_pass = st.text_input("New Password", type="password")
        confirm_pass = st.text_input("Confirm New Password", type="password")
        
        if st.form_submit_button("Update Password"):
            if new_pass == confirm_pass:
                payload = {"password": new_pass}
                username = st.session_state["username"]
                try:
                    res = requests.put(f"{API_URL}/users/{username}", json=payload)
                    if res.status_code == 200:
                        st.success("Password updated successfully.")
                    else:
                        st.error("Update failed.")
                except:
                    st.error("Connection failed.")
            else:
                st.error("Passwords do not match.")


def user_management_page():
    st.title("👥 User Management")
    st.markdown("Manage system access and roles.")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("System Users")
        try:
            res = requests.get(f"{API_URL}/users")
            if res.status_code == 200:
                users = res.json()
                if users:
                    df = pd.DataFrame(users)
                    st.dataframe(df[['username', 'name', 'role', 'active']], use_container_width=True)
        except:
            st.error("Could not fetch users.")

    with col2:
        st.subheader("Add User")
        with st.form("new_user"):
            new_user = st.text_input("Username")
            new_pass = st.text_input("Password", type="password")
            new_name = st.text_input("Full Name")
            new_role = st.selectbox("Role", list(ROLES.keys()))
            
            if st.form_submit_button("Create User", use_container_width=True):
                payload = {
                    "username": new_user, "password": new_pass,
                    "name": new_name, "role": new_role, "active": True
                }
                try:
                    res = requests.post(f"{API_URL}/users", json=payload)
                    if res.status_code == 200:
                        st.success("User created!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Failed: {res.text}")
                except:
                    st.error("Connection failed.")


# -----------------------------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Financial Transparency System",
        page_icon="🏫",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    inject_custom_css()

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["role"] = None

    if not st.session_state["logged_in"]:
        login_page()
    else:
        role = st.session_state.get("role")
        
        # Sidebar with custom styling
        st.sidebar.markdown(f"<div style='text-align: center; color: {PRIMARY_GREEN}; font-family: serif; font-size: 1.2rem; font-weight: bold;'>La Salle Academy</div>", unsafe_allow_html=True)
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"👤 **{st.session_state.get('name', 'User')}**")
        st.sidebar.caption(f"Role: {ROLES.get(role, role)}")
        st.sidebar.markdown("---")

        options = []
        if role == "guest":
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

        # Radio button navigation
        choice = st.sidebar.radio("Navigation", options, label_visibility="collapsed")

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
