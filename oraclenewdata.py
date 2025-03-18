import oracledb
from dotenv import load_dotenv
import os
import json
from datetime import datetime

# Load environment variables
load_dotenv("config/.env")

# Fetch credentials
username = os.getenv("ORACLE_USER")
password = os.getenv("ORACLE_PASSWORD")
dsn = os.getenv("ORACLE_DSN")

try:
    # Connect to Oracle
    conn = oracledb.connect(user=username, password=password, dsn=dsn)
    cursor = conn.cursor()
    print("✅ Connected to Oracle successfully!")
except oracledb.DatabaseError as e:
    print(f"❌ Connection failed: {e}")
    exit(1)

# Function to convert datetime objects to string
def serialize_data(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")  # Convert datetime to string
    return value

# Function to fetch DDL
def get_table_ddl(table_name):
    try:
        cursor.execute(f"SELECT DBMS_METADATA.GET_DDL('TABLE', '{table_name}') FROM DUAL")
        return cursor.fetchone()[0].read()
    except oracledb.DatabaseError as e:
        print(f"⚠️ Error fetching DDL for {table_name}: {e}")
        return None

# Function to fetch sample data (handling datetime fields)
def get_sample_data(table_name):
    try:
        cursor.execute(f"SELECT * FROM {table_name} FETCH FIRST 10 ROWS ONLY")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, [serialize_data(value) for value in row])) for row in rows]
    except oracledb.DatabaseError as e:
        print(f"⚠️ Error fetching sample data for {table_name}: {e}")
        return []

# Function to fetch constraints
def get_table_constraints(table_name):
    try:
        cursor.execute(f"""
            SELECT constraint_name, constraint_type, search_condition
            FROM user_constraints 
            WHERE table_name = '{table_name}'
        """)
        return [dict(zip(["constraint_name", "constraint_type", "search_condition"], row)) for row in cursor.fetchall()]
    except oracledb.DatabaseError as e:
        print(f"⚠️ Error fetching constraints for {table_name}: {e}")
        return []

# Fetch all tables
try:
    cursor.execute("SELECT table_name FROM user_tables")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"🔍 Found {len(tables)} tables in the database.")
except oracledb.DatabaseError as e:
    print(f"❌ Error fetching table list: {e}")
    exit(1)

# Generate data for all tables
data = {}
for table in tables:
    table_name = table.upper()  # Ensure uppercase table names

    print(f"📌 Processing table: {table_name}")
    table_data = {
        "DDL": get_table_ddl(table_name),
        "Sample Data": get_sample_data(table_name),
        "Constraints": get_table_constraints(table_name),
    }

    # Only include non-empty tables
    if any(table_data.values()):
        data[table_name] = table_data
    else:
        print(f"⚠️ Skipping {table_name}: No data retrieved.")

# Save JSON file with datetime conversion
try:
    with open("oracle_schema_data.json", "w") as f:
        json.dump(data, f, indent=4)
    print("✅ Schema data extracted and saved successfully!")
except Exception as e:
    print(f"❌ Error saving JSON file: {e}")

# Close the connection
cursor.close()
conn.close()
print("✅ Connection closed.")