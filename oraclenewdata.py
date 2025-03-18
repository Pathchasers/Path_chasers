import oracledb
from dotenv import load_dotenv
import os
import json
import base64
from datetime import datetime
from decimal import Decimal

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

# Function to convert non-serializable data types
def serialize_data(value):
    """Handles serialization of datetime, LOB, decimal, and other types"""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")  # Convert datetime to string
    elif isinstance(value, Decimal):
        return float(value)  # Convert Decimal to float
    elif isinstance(value, oracledb.LOB):
        lob_value = value.read()  # Read LOB content
        if isinstance(lob_value, bytes):  # Handle BLOB (binary)
            return base64.b64encode(lob_value).decode("utf-8")  # Convert to Base64 string
        return lob_value  # Handle CLOB (text)
    elif value is None:
        return None  # Convert NULL to None (JSON compatible)
    return value  # Return other data types as-is

# Function to fetch DDL
def get_table_ddl(table_name):
    try:
        cursor.execute(f"SELECT DBMS_METADATA.GET_DDL('TABLE', '{table_name}') FROM DUAL")
        return cursor.fetchone()[0].read()
    except oracledb.DatabaseError as e:
        print(f"⚠️ Error fetching DDL for {table_name}: {e}")
        return None

# Function to fetch sample data with type handling
def get_sample_data(table_name):
    try:
        cursor.execute(f"SELECT * FROM {table_name} FETCH FIRST 10 ROWS ONLY")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        # Apply `serialize_data` for each value
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

# JSON file path
json_file_path = "oracle_schema_data.json"

# Start writing JSON file incrementally
with open(json_file_path, "w") as f:
    f.write("{\n")  # Start JSON object
    for index, table in enumerate(tables):
        table_name = table.upper()  # Ensure uppercase table names
        print(f"📌 Processing table: {table_name}")

        table_data = {
            "DDL": get_table_ddl(table_name),
            "Sample Data": get_sample_data(table_name),
            "Constraints": get_table_constraints(table_name),
        }

        # Skip empty tables
        if not any(table_data.values()):
            print(f"⚠️ Skipping {table_name}: No data retrieved.")
            continue

        # Write JSON data for this table
        json.dump({table_name: table_data}, f, indent=4)

        # Add a comma unless it's the last table
        if index < len(tables) - 1:
            f.write(",\n")

    f.write("\n}")  # End JSON object

print("✅ Schema data extracted and saved successfully!")

# Close the connection
cursor.close()
conn.close()
print("✅ Connection closed.")