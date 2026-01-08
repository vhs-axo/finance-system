import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
API_URL = "http://127.0.0.1:8000"  # Address of your FastAPI backend

STRANDS = ["ABM", "STEM", "HUMSS", "General"]
CATEGORIES = ["Tuition Fee", "Miscellaneous Fee", "Organization Fund", "Laboratory Fee", "Event Fund", "Maintenance", "Utilities"]

# -----------------------------------------------------------------------------
# API WRAPPER
# -----------------------------------------------------------------------------
class FinanceAPI:
    """Helper class to handle API requests"""
    
    @staticmethod
    def login(username, password):
        try:
            resp = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
            return resp.json()
        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to the Backend API. Is it running?")
            return None

    @staticmethod
    def get_stats():
        try:
            resp = requests.get(f"{API_URL}/stats")
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}

    @staticmethod
    def get_transactions():
        try:
            resp = requests.get(f"{API_URL}/transactions")
            if resp.status_code == 200:
                return pd.DataFrame(resp.json())
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def create_transaction(data):
        try:
            resp = requests.post(f"{API_URL}/transactions", json=data)
            return resp.status_code == 201
        except Exception:
            return False

    @staticmethod
    def verify(txn_id):
        try:
            resp = requests.get(f"{API_URL}/verify/{txn_id}")
            if resp.status_code == 200:
                return resp.json()
            return {"valid": False, "message": resp.json().get('detail', 'Verification failed')}
        except Exception:
            return {"valid": False, "message": "Connection Error"}

# -----------------------------------------------------------------------------
# UI PAGES
# -----------------------------------------------------------------------------

def login_page():
    st.markdown("## 🔒 Financial System Login")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.info("Default Credentials (seeded on first run):\n- **admin** / admin123\n- **staff** / staff123")
    
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login", use_container_width=True):
            res = FinanceAPI.login(username, password)
            if res and res.get("success"):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['role'] = res.get('role')
                st.session_state['name'] = res.get('name')
                st.success("Login Successful!")
                time.sleep(0.5)
                st.rerun()
            elif res:
                st.error(res.get("message"))

def dashboard_page():
    st.title("📊 Dashboard")
    st.caption(f"Logged in as: {st.session_state['name']}")
    
    stats = FinanceAPI.get_stats()
    
    if stats:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tuition Collected", f"₱{stats.get('total_tuition', 0):,.2f}")
        c2.metric("Misc. Fees", f"₱{stats.get('total_misc', 0):,.2f}")
        c3.metric("Org Funds", f"₱{stats.get('total_org', 0):,.2f}")
        c4.metric("Expenses", f"₱{stats.get('total_expenses', 0):,.2f}", delta_color="inverse")
    
    st.markdown("---")
    
    df = FinanceAPI.get_transactions()
    if not df.empty:
        # Convert date string to datetime for plotting
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Transactions by Strand")
            fig = px.pie(df, names='strand', values='amount', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("Recent Activity")
            st.dataframe(df[['created_at', 'txn_type', 'amount', 'recorded_by']].head(10), use_container_width=True)

def input_page():
    st.title("📝 New Transaction")
    
    with st.form("entry_form"):
        c1, c2 = st.columns(2)
        with c1:
            txn_type = st.selectbox("Type", ["Collection", "Disbursement"])
            strand = st.selectbox("Strand", STRANDS)
            amount = st.number_input("Amount", min_value=1.0, step=0.01)
        with c2:
            category = st.selectbox("Category", CATEGORIES)
            desc = st.text_area("Description")
            
        if st.form_submit_button("Submit Record"):
            payload = {
                "recorded_by": st.session_state['username'],
                "txn_type": txn_type,
                "strand": strand,
                "category": category,
                "description": desc,
                "amount": amount
            }
            if FinanceAPI.create_transaction(payload):
                st.success("Transaction recorded successfully!")
                time.sleep(1)
            else:
                st.error("Failed to record transaction.")

def audit_page():
    st.title("📜 Audit Trail")
    
    df = FinanceAPI.get_transactions()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "audit_trail.csv", "text/csv")
    else:
        st.info("No records found.")

def verify_page():
    st.title("✅ Verification")
    
    tid = st.number_input("Transaction ID", min_value=1, step=1)
    if st.button("Check Integrity"):
        res = FinanceAPI.verify(tid)
        if res['valid']:
            st.success(res['message'])
            st.json(res['data'])
        else:
            st.error(res['message'])

# -----------------------------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Finance System", layout="wide")
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_page()
    else:
        # Sidebar
        with st.sidebar:
            st.title("Navigation")
            menu = st.radio("Go to", ["Dashboard", "New Transaction", "Audit Trail", "Verify"])
            st.markdown("---")
            if st.button("Logout"):
                st.session_state['logged_in'] = False
                st.rerun()

        # Page Routing
        if menu == "Dashboard":
            dashboard_page()
        elif menu == "New Transaction":
            input_page()
        elif menu == "Audit Trail":
            audit_page()
        elif menu == "Verify":
            verify_page()

if __name__ == "__main__":
    main()
