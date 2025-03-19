import json
import base64
import oracledb
import os
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Connect to Oracle
conn = oracledb.connect(
    user=os.getenv("ORACLE_USER"),
    password=os.getenv("ORACLE_PASSWORD"),
    dsn=os.getenv("ORACLE_DSN")
)
cursor = conn.cursor()

# Function to handle different data types
def serialize_data(value):
    """Handles serialization of datetime, BLOB, CLOB, and other data types."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, bytes):  # Handle BLOB
        return base64.b64encode(value).decode("utf-8")
    elif isinstance(value, oracledb.LOB):  # Handle CLOB
        lob_value = value.read()
        return base64.b64encode(lob_value).decode("utf-8") if isinstance(lob_value, bytes) else lob_value
    return value

# Function to get table DDL
def get_table_ddl(cursor, table_name, schema_name="MY_SCHEMA"):
    """Extracts DDL (CREATE TABLE statement) for a table."""
    query = f"SELECT DBMS_METADATA.GET_DDL('TABLE', '{table_name}', '{schema_name}') FROM DUAL"
    try:
        cursor.execute(query)
        ddl = cursor.fetchone()[0]
        return ddl.read() if isinstance(ddl, oracledb.LOB) else ddl
    except:
        return "Error fetching DDL"

# Function to get table constraints
def get_table_constraints(cursor, table_name):
    """Fetches all constraints for a table."""
    query = """
    SELECT
        c.constraint_name,
        c.constraint_type,
        cc.column_name,
        c.r_constraint_name,
        r.table_name AS referenced_table,
        r.column_name AS referenced_column
    FROM all_constraints c
    JOIN all_cons_columns cc ON c.constraint_name = cc.constraint_name
    LEFT JOIN all_constraints rc ON c.r_constraint_name = rc.constraint_name
    LEFT JOIN all_cons_columns r ON rc.constraint_name = r.constraint_name
    WHERE c.table_name = :table_name
    """
    try:
        cursor.execute(query, {"table_name": table_name})
        constraints = []
        for row in cursor.fetchall():
            constraints.append({
                "constraint_name": row[0],
                "type": row[1],
                "column": row[2],
                "referenced_table": row[4] if row[1] == 'R' else None,
                "referenced_column": row[5] if row[1] == 'R' else None
            })
        return constraints
    except:
        return "Error fetching constraints"

# Get all tables in the schema
cursor.execute("SELECT table_name FROM all_tables WHERE owner = 'MY_SCHEMA'")
tables = [row[0] for row in cursor.fetchall()]

# Open JSONL file
with open("database_schema.jsonl", "w", encoding="utf-8") as jsonl_file:
    for table in tables:
        print(f"📌 Processing table: {table}")

        # Fetch table information
        ddl = get_table_ddl(cursor, table)
        constraints = get_table_constraints(cursor, table)

        # Fetch sample data
        try:
            cursor.execute(f"SELECT * FROM {table} FETCH FIRST 10 ROWS ONLY")
            columns = [col[0] for col in cursor.description]
            data = [dict(zip(columns, map(serialize_data, row))) for row in cursor.fetchall()]
        except:
            data = "Error fetching data"

        # Create JSONL entry
        jsonl_entry = {
            "rawContent": table,
            "enhancedContext": {
                "table_name": table,
                "ddl": ddl,
                "constraints": constraints,
                "sample_data": data
            }
        }

        # Write to JSONL file
        jsonl_file.write(json.dumps(jsonl_entry, ensure_ascii=False) + "\n")

print("✅ JSONL file created: database_schema.jsonl")

# Close connection
cursor.close()
conn.close()