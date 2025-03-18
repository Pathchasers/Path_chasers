import cx_Oracle
import json

# Database connection
dsn = cx_Oracle.makedsn("your_host", "your_port", service_name="your_service_name")
conn = cx_Oracle.connect(user="your_user", password="your_password", dsn=dsn)
cursor = conn.cursor()

# Function to fetch DDL
def get_table_ddl(table_name):
    ddl_query = f"SELECT DBMS_METADATA.GET_DDL('TABLE', '{table_name}') FROM DUAL"
    cursor.execute(ddl_query)
    return cursor.fetchone()[0].read()

# Function to fetch sample data
def get_sample_data(table_name):
    query = f"SELECT * FROM {table_name} FETCH FIRST 10 ROWS ONLY"
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]

# Function to fetch constraints
def get_table_constraints(table_name):
    query = f"""
        SELECT constraint_name, constraint_type, search_condition
        FROM user_constraints 
        WHERE table_name = '{table_name}'
    """
    cursor.execute(query)
    return [dict(zip(["constraint_name", "constraint_type", "search_condition"], row)) for row in cursor.fetchall()]

# Fetch all tables
cursor.execute("SELECT table_name FROM user_tables")
tables = [row[0] for row in cursor.fetchall()]

# Generate data for all tables
data = {}
for table in tables:
    data[table] = {
        "DDL": get_table_ddl(table),
        "Sample Data": get_sample_data(table),
        "Constraints": get_table_constraints(table),
    }

# Save as JSON
with open("oracle_schema_data.json", "w") as f:
    json.dump(data, f, indent=4)

print("Schema data extracted successfully!")

# Close the connection
cursor.close()
conn.close()