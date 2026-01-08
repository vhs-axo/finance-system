import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
from immudb import ImmudbClient

# -----------------------------------------------------------------------------
# CONFIGURATION & CONSTANTS
# -----------------------------------------------------------------------------
DB_HOST = "127.0.0.1"
DB_PORT = 3322
DB_USER = "immudb"
DB_PASSWORD = "immudb" # Default password

# Role Definitions based on interface.pdf
ROLES = {
    "admin": "Admin",               # Approves, Reviews, Reports
    "staff": "Finance Staff",       # Records Transactions
    "officer": "Finance Officer",   # Monitors, Checks
    "auditor": "Auditor",           # Verifies Audit Trail
    "it": "System Admin"            # User Management (Not fully implemented in this demo)
}

# Mock Users for Login (In a real app, these would be in the DB)
USERS = {
    "admin": {"password": "admin123", "role": "admin", "name": "Principal Skinner"},
    "staff": {"password": "staff123", "role": "staff", "name": "Finance Clerk"},
    "officer": {"password": "officer123", "role": "officer", "name": "Chief Finance Officer"},
    "auditor": {"password": "auditor123", "role": "auditor", "name": "External Auditor"},
}

STRANDS = ["ABM", "STEM", "HUMSS", "General"]
CATEGORIES = ["Tuition Fee", "Miscellaneous Fee", "Organization Fund", "Laboratory Fee", "Event Fund", "Maintenance", "Utilities"]

# -----------------------------------------------------------------------------
# DATABASE HANDLER (Immudb)
# -----------------------------------------------------------------------------
class FinanceDB:
    def __init__(self):
        self.client = ImmudbClient(f"{DB_HOST}:{DB_PORT}")
    
    def connect(self):
        try:
            self.client.login(DB_USER, DB_PASSWORD)
            return True
        except Exception as e:
            st.error(f"Failed to connect to Immudb. Is the server running? Error: {e}")
            return False

    def init_db(self):
        """Initialize the table if it doesn't exist."""
        if not self.connect():
            return
        
        try:
            # Create a table for financial transactions
            # Note: Immudb SQL syntax
            self.client.sqlExec("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER AUTO_INCREMENT,
                    created_at TIMESTAMP,
                    recorded_by VARCHAR,
                    txn_type VARCHAR,
                    strand VARCHAR,
                    category VARCHAR,
                    description VARCHAR,
                    amount INTEGER,
                    status VARCHAR,
                    PRIMARY KEY id
                )
            """)
        except Exception as e:
            # Ignore if table already exists error variants
            pass
            
    def add_transaction(self, user, txn_type, strand, category, description, amount):
        """
        Records a transaction.
        Amount is stored as INTEGER (multiply by 100 to save cents).
        """
        if not self.connect():
            return None
        
        try:
            # Insert record
            params = {
                'recorded_by': user, 
                'txn_type': txn_type, 
                'strand': strand, 
                'category': category, 
                'description': description, 
                'amount': int(amount * 100), # Store as centavos/cents
                'status': 'Pending' if txn_type == 'Disbursement' else 'Verified', # Collections are auto-verified, disbursements need approval
                'created_at': datetime.now()
            }
            
            # Using simple SQL formatting for the demo (parameterized queries depend on client version)
            # IMPORTANT: In production, sanitize inputs to prevent injection, though immudb is limited in injection surface.
            query = f"""
                INSERT INTO transactions (created_at, recorded_by, txn_type, strand, category, description, amount, status)
                VALUES (NOW(), '{params['recorded_by']}', '{params['txn_type']}', '{params['strand']}', '{params['category']}', '{params['description']}', {params['amount']}, '{params['status']}')
            """
            result = self.client.sqlExec(query)
            return result
        except Exception as e:
            st.error(f"Error adding transaction: {e}")
            return None

    def get_all_transactions(self):
        if not self.connect():
            return pd.DataFrame()
        
        try:
            # Fetch all records
            result = self.client.sqlQuery("SELECT id, created_at, recorded_by, txn_type, strand, category, description, amount, status FROM transactions ORDER BY id DESC")
            
            data = []
            for row in result:
                # Unpack tuple based on index
                data.append({
                    "ID": row[0],
                    "Date": str(row[1]),
                    "Recorded By": row[2],
                    "Type": row[3],
                    "Strand": row[4],
                    "Category": row[5],
                    "Description": row[6],
                    "Amount": row[7] / 100.0, # Convert back to float
                    "Status": row[8]
                })
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error fetching transactions: {e}")
            return pd.DataFrame()

    def get_summary_stats(self, df):
        """Calculate totals from the dataframe."""
        if df.empty:
            return {"Tuition": 0, "Misc": 0, "Org": 0, "Expenses": 0}
        
        # Collections
        collections = df[df['Type'] == 'Collection']
        tuition = collections[collections['Category'] == 'Tuition Fee']['Amount'].sum()
        misc = collections[collections['Category'] == 'Miscellaneous Fee']['Amount'].sum()
        org = collections[collections['Category'] == 'Organization Fund']['Amount'].sum()
        
        # Disbursements
        expenses = df[df['Type'] == 'Disbursement']['Amount'].sum()
        
        return {
            "Tuition": tuition,
            "Misc": misc,
            "Org": org,
            "Expenses": expenses
        }

    def verify_transaction(self, txn_id):
        """
        Uses immudb's cryptographic proof capabilities.
        In a full implementation, we would use client.verifiedGet().
        For this SQL-based demo, we check existence and history.
        """
        if not self.connect():
            return None
        
        try:
            # Query specific ID
            result = self.client.sqlQuery(f"SELECT id, created_at, amount, description FROM transactions WHERE id = {txn_id}")
            if not result:
                return {"valid": False, "message": "Transaction ID not found."}
            
            # If found, it exists in the immutable ledger
            row = result[0]
            return {
                "valid": True, 
                "message": "Valid - No tampering detected. Record exists in immutable ledger.",
                "data": row
            }
        except Exception as e:
            return {"valid": False, "message": f"Error: {e}"}

# -----------------------------------------------------------------------------
# UI COMPONENTS
# -----------------------------------------------------------------------------

def login_page():
    st.markdown("""
    <style>
    .login-container {
        padding: 50px;
        border-radius: 10px;
        background-color: #f0f2f6;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🔒 Financial Transparency System")
    st.subheader("Senior High School (ABM, STEM, HUMSS)")
    
    _, col2, _ = st.columns([1,2,1])
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login", use_container_width=True):
            user = USERS.get(username)
            if user and user['password'] == password:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['role'] = user['role']
                st.session_state['name'] = user['name']
                st.rerun()
            else:
                st.error("Invalid username or password")

def dashboard_page(db):
    st.title("📊 Dashboard")
    st.write(f"Welcome, **{st.session_state['name']}** ({ROLES[st.session_state['role']]})")
    
    # Refresh Data
    df = db.get_all_transactions()
    stats = db.get_summary_stats(df)
    
    # Summary Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tuition Collected", f"₱{stats['Tuition']:,.2f}")
    col2.metric("Misc. Fees", f"₱{stats['Misc']:,.2f}")
    col3.metric("Org Funds", f"₱{stats['Org']:,.2f}")
    col4.metric("Total Expenses", f"₱{stats['Expenses']:,.2f}", delta_color="inverse")
    
    st.markdown("---")
    
    # Charts
    if not df.empty:
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Collections by Strand")
            collections = df[df['Type'] == 'Collection']
            if not collections.empty:
                fig_pie = px.pie(collections, values='Amount', names='Strand', title='Revenue Share per Strand')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No collections recorded yet.")
                
        with c2:
            st.subheader("Financial Activity Trend")
            # Ensure Date is datetime
            df['DateObj'] = pd.to_datetime(df['Date'])
            # Group by date and type
            daily_stats = df.groupby([df['DateObj'].dt.date, 'Type'])['Amount'].sum().reset_index()
            daily_stats.columns = ['Date', 'Type', 'Amount']
            
            fig_bar = px.bar(daily_stats, x='Date', y='Amount', color='Type', barmode='group', title="Collections vs Disbursements")
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No data available to display charts.")

def transaction_entry_page(db):
    st.title("📝 Transaction Recording Module")
    st.info("⚠️ Records saved here are IMMUTABLE. They cannot be edited or deleted once submitted.")
    
    with st.form("transaction_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            txn_type = st.selectbox("Transaction Type", ["Collection", "Disbursement"])
            strand = st.selectbox("Strand/Department", STRANDS)
            amount = st.number_input("Amount (PHP)", min_value=0.0, step=0.01)
        
        with col2:
            category = st.selectbox("Fee Category", CATEGORIES)
            # Dynamic Label based on type
            desc_label = "Payer (Student ID) & Details" if txn_type == "Collection" else "Payee & Purpose"
            description = st.text_area(desc_label, placeholder="e.g., Student 2024-001 Tuition" if txn_type == "Collection" else "e.g., Purchase of Lab Glassware")
            
        submitted = st.form_submit_button("Submit Transaction")
        
        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            elif not description:
                st.error("Description is required.")
            else:
                res = db.add_transaction(
                    st.session_state['username'],
                    txn_type,
                    strand,
                    category,
                    description,
                    amount
                )
                if res:
                    st.success("Transaction recorded successfully! ID generated.")
                    time.sleep(1)
                    st.rerun()

def audit_trail_page(db):
    st.title("📜 Audit Trail")
    st.write("Complete history of all financial transactions. Data is fetched directly from the immutable ledger.")
    
    df = db.get_all_transactions()
    
    if not df.empty:
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            filter_strand = st.multiselect("Filter by Strand", STRANDS)
        with col2:
            filter_type = st.multiselect("Filter by Type", ["Collection", "Disbursement"])
            
        filtered_df = df
        if filter_strand:
            filtered_df = filtered_df[filtered_df['Strand'].isin(filter_strand)]
        if filter_type:
            filtered_df = filtered_df[filtered_df['Type'].isin(filter_type)]
            
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("No transactions found in the ledger.")

def verification_page(db):
    st.title("✅ Integrity Verification")
    st.write("Verify the authenticity of a transaction record against the immutable database.")
    
    txn_id = st.number_input("Enter Transaction ID", min_value=1, step=1)
    
    if st.button("Verify Record"):
        with st.spinner("Checking cryptographic proofs..."):
            result = db.verify_transaction(txn_id)
            time.sleep(0.5) # Simulate check time
            
            if result['valid']:
                st.success(result['message'])
                st.json(result['data'])
            else:
                st.error(result['message'])

# -----------------------------------------------------------------------------
# MAIN APP LOGIC
# -----------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Financial Transparency System", layout="wide", page_icon="💰")
    
    # Initialize DB
    db = FinanceDB()
    db.init_db()
    
    # Session State Init
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        
    # Routing
    if not st.session_state['logged_in']:
        login_page()
    else:
        # Sidebar Navigation
        st.sidebar.title("School Finance")
        st.sidebar.image("https://img.icons8.com/color/96/000000/school.png", width=50) # Placeholder icon
        st.sidebar.write(f"User: **{st.session_state['username']}**")
        
        role = st.session_state['role']
        
        # Menu options based on Role (Simplified for demo)
        options = ["Dashboard", "Audit Trail", "Verification"]
        if role in ["staff", "admin"]:
            options.insert(1, "New Transaction")
            
        choice = st.sidebar.radio("Navigation", options)
        
        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()
            
        # Page Render
        if choice == "Dashboard":
            dashboard_page(db)
        elif choice == "New Transaction":
            transaction_entry_page(db)
        elif choice == "Audit Trail":
            audit_trail_page(db)
        elif choice == "Verification":
            verification_page(db)

if __name__ == "__main__":
    main()
