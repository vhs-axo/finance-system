import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import time

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
API_URL = "http://127.0.0.1:8000"

ROLES = {
    "admin": "Admin",
    "staff": "Finance Staff",
    "officer": "Finance Officer",
    "auditor": "Auditor",
    "it": "System Admin",
}

STRANDS = ["ABM", "STEM", "HUMSS", "General"]
CATEGORIES = {
    "Collection": ["Tuition Fee", "Miscellaneous Fee", "Organization Fund", "Donation"],
    "Disbursement": ["Utility Bill", "Teacher Salary", "Event Expense", "Maintenance", "Refund"]
}

# -----------------------------------------------------------------------------
# API CLIENT HELPER
# -----------------------------------------------------------------------------
class ApiClient:
    """Helper to communicate with FastAPI backend"""
    
    @staticmethod
    def login(username, password):
        try:
            res = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
            return res.json()
        except:
            return {"success": False, "message": "Server unavailable"}

    @staticmethod
    def get_stats():
        try:
            return requests.get(f"{API_URL}/stats").json()
        except:
            return {}

    @staticmethod
    def get_transactions(student_id=None, status=None):
        params = {}
        if student_id: params['student_id'] = student_id
        if status: params['status'] = status
        try:
            return requests.get(f"{API_URL}/transactions", params=params).json()
        except:
            return []

    @staticmethod
    def create_transaction(data):
        try:
            res = requests.post(f"{API_URL}/transactions", json=data)
            return res.status_code == 200
        except:
            return False

    @staticmethod
    def approve_transaction(txn_id, admin_username, action):
        try:
            data = {"txn_id": txn_id, "admin_username": admin_username, "action": action}
            requests.put(f"{API_URL}/transactions/{txn_id}/approve", json=data)
            return True
        except:
            return False

    # User Management APIs
    @staticmethod
    def get_users():
        try:
            return requests.get(f"{API_URL}/users").json()
        except:
            return []

    @staticmethod
    def create_user(data):
        try:
            res = requests.post(f"{API_URL}/users", json=data)
            return res.status_code == 200
        except:
            return False

    @staticmethod
    def update_user(username, data):
        try:
            requests.put(f"{API_URL}/users/{username}", json=data)
            return True
        except:
            return False

# -----------------------------------------------------------------------------
# PAGES
# -----------------------------------------------------------------------------

def login_page():
    st.markdown("## 🏫 SHS Financial Transparency System")
    st.info("Please login with your credentials.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/2666/2666505.png", width=150)
    
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            with st.spinner("Authenticating..."):
                resp = ApiClient.login(username, password)
                if resp.get("success"):
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = resp["role"]
                    st.session_state["username"] = username
                    st.session_state["name"] = resp["name"]
                    st.success("Welcome!")
                    st.rerun()
                else:
                    st.error(resp.get("message", "Login failed"))

def dashboard_page():
    st.title("📊 Financial Dashboard")
    st.write("Real-time financial overview.")
    
    # Refresh Button
    if st.button("Refresh Data"):
        st.rerun()

    stats = ApiClient.get_stats()
    if not stats:
        st.error("Could not load statistics.")
        return

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tuition", f"₱{stats.get('total_tuition', 0):,.2f}")
    c2.metric("Total Misc", f"₱{stats.get('total_misc', 0):,.2f}")
    c3.metric("Org Funds", f"₱{stats.get('total_org', 0):,.2f}")
    c4.metric("Pending Txns", stats.get('pending_count', 0), delta_color="inverse")

    # Charting (Mocking logic for display since endpoint returns aggregates)
    # Ideally, we'd fetch raw data for charts, let's fetch last 100 txns
    txns = ApiClient.get_transactions()
    if txns:
        df = pd.DataFrame(txns)
        
        # Pie Chart: Income vs Expense
        st.subheader("Income vs Expenses")
        if not df.empty:
            pie_data = df.groupby("txn_type")["amount"].sum().reset_index()
            fig1 = px.pie(pie_data, values="amount", names="txn_type", title="Transaction Distribution")
            st.plotly_chart(fig1)

            # Bar Chart: By Strand
            st.subheader("Collections by Strand")
            bar_data = df[df["txn_type"] == "Collection"].groupby("strand")["amount"].sum().reset_index()
            fig2 = px.bar(bar_data, x="strand", y="amount", color="strand", title="Revenue by Strand")
            st.plotly_chart(fig2)

            # Missing Feature #5: Reporting/Export
            st.subheader("📄 Reporting")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Report (CSV)",
                csv,
                "financial_report.csv",
                "text/csv",
                key='download-csv'
            )
    else:
        st.info("No transaction data available for charts.")


def transaction_entry_page():
    st.title("📝 New Transaction")
    
    with st.form("entry_form"):
        c1, c2 = st.columns(2)
        txn_type = c1.selectbox("Transaction Type", ["Collection", "Disbursement"])
        strand = c2.selectbox("Strand", STRANDS)
        
        category = st.selectbox("Category", CATEGORIES[txn_type])
        
        # Missing Feature #3: Student Link (Enhanced)
        student_id = st.text_input("Student ID (Optional)", placeholder="e.g., S-2024-001")
        
        desc = st.text_area("Description / Particulars")
        amount = st.number_input("Amount (PHP)", min_value=0.0, step=0.01)
        
        # Missing Feature #4: Evidence Reference
        proof = st.text_input("Reference/Receipt # (Proof of Transaction)")

        if st.form_submit_button("Submit Transaction"):
            data = {
                "recorded_by": st.session_state["username"],
                "txn_type": txn_type,
                "strand": strand,
                "category": category,
                "description": desc,
                "amount": amount,
                "student_id": student_id,
                "proof_reference": proof
            }
            if ApiClient.create_transaction(data):
                st.success("Transaction recorded! Status: Pending Approval.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Failed to record transaction.")

def audit_trail_page():
    st.title("📜 Immutable Audit Trail")
    
    # Missing Feature #3: Student View / Filters
    st.subheader("Filter & Search")
    c1, c2 = st.columns(2)
    search_student = c1.text_input("Search by Student ID")
    filter_status = c2.selectbox("Filter Status", ["All", "Pending", "Approved", "Rejected"])
    
    status_param = None if filter_status == "All" else filter_status
    txns = ApiClient.get_transactions(student_id=search_student, status=status_param)
    
    if txns:
        df = pd.DataFrame(txns)
        # Reorder columns for readability
        cols = ["id", "created_at", "status", "txn_type", "amount", "student_id", "recorded_by", "approved_by", "proof_reference"]
        st.dataframe(df[cols], use_container_width=True)
    else:
        st.info("No records found matching filters.")

def pending_approvals_page():
    """Missing Feature #2: Approval Workflow UI"""
    st.title("✅ Pending Approvals")
    st.info("Review transactions requiring authorization.")
    
    txns = ApiClient.get_transactions(status="Pending")
    
    if not txns:
        st.write("No pending transactions.")
        return

    for txn in txns:
        with st.expander(f"#{txn['id']} - {txn['txn_type']} - ₱{txn['amount']:,.2f} ({txn['recorded_by']})"):
            c1, c2 = st.columns(2)
            c1.write(f"**Description:** {txn['description']}")
            c1.write(f"**Category:** {txn['category']}")
            c2.write(f"**Student:** {txn['student_id'] or 'N/A'}")
            c2.write(f"**Proof Ref:** {txn['proof_reference'] or 'N/A'}")
            
            col_a, col_b = st.columns([1,1])
            if col_a.button("Approve", key=f"app_{txn['id']}"):
                if ApiClient.approve_transaction(txn['id'], st.session_state["username"], "Approve"):
                    st.success("Approved!")
                    time.sleep(0.5)
                    st.rerun()
            
            if col_b.button("Reject", key=f"rej_{txn['id']}"):
                if ApiClient.approve_transaction(txn['id'], st.session_state["username"], "Reject"):
                    st.warning("Rejected.")
                    time.sleep(0.5)
                    st.rerun()

def user_management_page():
    """Missing Feature #1: User Management UI"""
    st.title("👥 User Management")
    
    tab1, tab2 = st.tabs(["User List", "Create User"])
    
    with tab1:
        users = ApiClient.get_users()
        if users:
            df = pd.DataFrame(users)
            st.dataframe(df, use_container_width=True)
            
            # Simple Deactivation Form
            st.subheader("Manage Status")
            target_user = st.selectbox("Select User", [u['username'] for u in users])
            if st.button("Toggle Active Status"):
                current_status = next((u['active'] for u in users if u['username'] == target_user), True)
                ApiClient.update_user(target_user, {"active": not current_status})
                st.success("Status updated.")
                st.rerun()
    
    with tab2:
        st.subheader("Register New User")
        new_user = st.text_input("Username")
        new_name = st.text_input("Full Name")
        new_pass = st.text_input("Password", type="password")
        new_role = st.selectbox("Role", ROLES.keys())
        
        if st.button("Create User"):
            if new_user and new_pass:
                data = {
                    "username": new_user, "password": new_pass, 
                    "name": new_name, "role": new_role, "active": True
                }
                if ApiClient.create_user(data):
                    st.success("User created successfully!")
                else:
                    st.error("Failed to create user (might already exist).")
            else:
                st.error("Missing fields.")

# -----------------------------------------------------------------------------
# MAIN APP LOOP
# -----------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Financial Transparency System", layout="wide", page_icon="💰"
    )

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_page()
    else:
        # Sidebar
        st.sidebar.title("School Finance")
        st.sidebar.write(f"Logged in as: **{st.session_state['name']}**")
        st.sidebar.write(f"Role: *{ROLES.get(st.session_state['role'], 'User')}*")
        
        role = st.session_state["role"]
        
        options = ["Dashboard", "Audit Trail"]
        
        if role in ["staff", "admin", "officer"]:
            options.insert(1, "New Transaction")
        
        if role == "admin":
            options.insert(2, "Pending Approvals")
            
        if role == "it":
            options.append("User Management")

        options.append("Logout")
        
        choice = st.sidebar.radio("Navigation", options)
        
        if choice == "Dashboard":
            dashboard_page()
        elif choice == "New Transaction":
            transaction_entry_page()
        elif choice == "Pending Approvals":
            pending_approvals_page()
        elif choice == "Audit Trail":
            audit_trail_page()
        elif choice == "User Management":
            user_management_page()
        elif choice == "Logout":
            st.session_state["logged_in"] = False
            st.rerun()

if __name__ == "__main__":
    main()
