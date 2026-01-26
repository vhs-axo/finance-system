"""
Script to manually create bills and bill_assignments tables.
Run this if you get "table does not exist" errors for bills functionality.
"""
from app.database import get_db_client

def create_bills_tables():
    client = get_db_client()
    try:
        # Create bills table
        try:
            client.sqlQuery("SELECT id FROM bills LIMIT 1")
            print("✅ Bills table already exists")
        except Exception:
            client.sqlExec("""
                CREATE TABLE bills (
                    id INTEGER AUTO_INCREMENT,
                    created_at TIMESTAMP,
                    bill_type VARCHAR,
                    description VARCHAR,
                    total_amount INTEGER,
                    created_by VARCHAR,
                    PRIMARY KEY id
                )
            """)
            print("✅ Bills table created successfully")
        
        # Create bill_assignments table
        try:
            client.sqlQuery("SELECT id FROM bill_assignments LIMIT 1")
            print("✅ Bill assignments table already exists")
        except Exception:
            client.sqlExec("""
                CREATE TABLE bill_assignments (
                    id INTEGER AUTO_INCREMENT,
                    bill_id INTEGER,
                    student_id VARCHAR,
                    amount INTEGER,
                    paid_amount INTEGER,
                    status VARCHAR,
                    PRIMARY KEY id
                )
            """)
            print("✅ Bill assignments table created successfully")
        
        # Create index
        try:
            client.sqlExec("CREATE INDEX ON bill_assignments(student_id)")
            print("✅ Index created on bill_assignments(student_id)")
        except Exception:
            print("⚠️  Index might already exist (this is okay)")
        
        print("\n✅ All bills tables are ready!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    print("Creating bills tables...")
    create_bills_tables()
