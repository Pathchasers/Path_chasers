import oracledb
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Read DSN and schema connection details from environment variables
DSN = os.getenv('DSN')

schemas = {
    "nexus_dw": {
        "user": os.getenv('NEXUS_DW_USER'),
        "password": os.getenv('NEXUS_DW_PASSWORD')
    },
    "nexus_core": {
        "user": os.getenv('NEXUS_CORE_USER'),
        "password": os.getenv('NEXUS_CORE_PASSWORD')
    },
    "nexus_analytics": {
        "user": os.getenv('NEXUS_ANALYTICS_USER'),
        "password": os.getenv('NEXUS_ANALYTICS_PASSWORD')
    }
}

# Unique delimiter for sample data rows
DATA_DELIMITER = '|~|'

# Icons for status messages
ICON_SUCCESS = "✅"
ICON_ERROR = "❌"
ICON_INFO = "ℹ️"

def get_table_names(connection):
    """Retrieve all tables for the current schema."""
    query = "SELECT table_name FROM user_tables"
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            tables = [row[0] for row in cursor.fetchall()]
            print(f"{ICON_SUCCESS} Retrieved {len(tables)} tables")
            return tables
    except Exception as e:
        print(f"{ICON_ERROR} Error retrieving table names: {e}")
        return []

def get_columns(connection, table_name):
    """Retrieve columns and their details for the given table."""
    query = """
        SELECT column_name, data_type, nullable, data_length, data_precision, data_scale
        FROM user_tab_columns
        WHERE table_name = :tbl
        ORDER BY column_id
    """
    columns = []
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, tbl=table_name)
            for row in cursor.fetchall():
                col_name, data_type, nullable, data_length, data_precision, data_scale = row
                constraint_info = "NOT NULL" if nullable == 'N' else "NULLABLE"
                # For NUMBER types, include precision/scale if available.
                if data_type.upper() == "NUMBER":
                    details = f"{data_type}"
                    if data_precision:
                        details += f"({data_precision}"
                        if data_scale is not None:
                            details += f",{data_scale}"
                        details += ")"
                    else:
                        details += f"({data_length})"
                else:
                    details = f"{data_type}({data_length})"
                col_def = f"{col_name}: {details} | {constraint_info}"
                columns.append(col_def)
            print(f"{ICON_SUCCESS} Retrieved columns for table {table_name}")
    except Exception as e:
        print(f"{ICON_ERROR} Error retrieving columns for table {table_name}: {e}")
    return columns

def get_constraints(connection, table_name):
    """Retrieve primary key and foreign key constraints for the given table."""
    constraints = {"primaryKey": [], "foreignKeys": []}

    # Primary Key
    pk_query = """
        SELECT acc.column_name
        FROM user_constraints ac
        JOIN user_cons_columns acc ON ac.constraint_name = acc.constraint_name
        WHERE ac.table_name = :tbl AND ac.constraint_type = 'P'
        ORDER BY acc.position
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(pk_query, tbl=table_name)
            constraints["primaryKey"] = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"{ICON_ERROR} Error retrieving primary keys for table {table_name}: {e}")

    # Foreign Keys
    fk_query = """
        SELECT acc.column_name, ac.r_constraint_name
        FROM user_constraints ac
        JOIN user_cons_columns acc ON ac.constraint_name = acc.constraint_name
        WHERE ac.table_name = :tbl AND ac.constraint_type = 'R'
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(fk_query, tbl=table_name)
            fk_list = []
            for col_name, r_constraint_name in cursor.fetchall():
                # Retrieve the referenced table and column details from the parent constraint
                parent_query = """
                    SELECT table_name, column_name
                    FROM user_cons_columns
                    WHERE constraint_name = :rcons
                    ORDER BY position
                """
                cursor.execute(parent_query, rcons=r_constraint_name)
                parent_info = cursor.fetchone()
                if parent_info:
                    parent_table, parent_column = parent_info
                    fk_list.append(f"{col_name} -> {parent_table}.{parent_column}")
            constraints["foreignKeys"] = fk_list
    except Exception as e:
        print(f"{ICON_ERROR} Error retrieving foreign keys for table {table_name}: {e}")
    
    print(f"{ICON_SUCCESS} Retrieved constraints for table {table_name}")
    return constraints

def get_sample_data(connection, table_name, limit=10):
    """Retrieve sample data rows using the unique delimiter to separate values."""
    query = f"SELECT * FROM {table_name} FETCH FIRST {limit} ROWS ONLY"
    sample_rows = []
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            col_names = [desc[0] for desc in cursor.description]
            sample_rows.append(DATA_DELIMITER.join(col_names))
            for row in cursor.fetchall():
                row_str = DATA_DELIMITER.join([str(item) if item is not None else 'NULL' for item in row])
                sample_rows.append(row_str)
        print(f"{ICON_SUCCESS} Retrieved sample data for table {table_name}")
    except Exception as e:
        print(f"{ICON_ERROR} Error retrieving sample data for table {table_name}: {e}")
    return sample_rows

def write_table_definition(file_handle, table_name, columns, constraints, sample_data):
    """Append a single table definition to the file in a structured text format."""
    try:
        file_handle.write("--- TABLE DEFINITION START ---\n")
        file_handle.write(f"Table Name: {table_name}\n")
        file_handle.write("Description: [Add description if needed]\n\n")
        
        file_handle.write("Columns:\n")
        for col in columns:
            file_handle.write(f"  - {col}\n")
        
        file_handle.write("\nConstraints:\n")
        pk = ", ".join(constraints["primaryKey"]) if constraints["primaryKey"] else "None"
        file_handle.write(f"  - Primary Key: {pk}\n")
        if constraints["foreignKeys"]:
            file_handle.write("  - Foreign Keys:\n")
            for fk in constraints["foreignKeys"]:
                file_handle.write(f"      * {fk}\n")
        else:
            file_handle.write("  - Foreign Keys: None\n")
        
        file_handle.write("\nSample Data (Columns separated by '" + DATA_DELIMITER + "'):\n")
        for row in sample_data:
            file_handle.write(f"  {row}\n")
        
        file_handle.write("--- TABLE DEFINITION END ---\n\n")
        print(f"{ICON_INFO} Appended definition for table {table_name}")
    except Exception as e:
        print(f"{ICON_ERROR} Error writing table definition for {table_name}: {e}")

def process_schema(schema_name, credentials):
    """Connect to a specific schema, extract metadata and sample data, and append to an output file."""
    print(f"{ICON_INFO} Processing schema: {schema_name}")
    connection = None
    output_file = f"{schema_name}_tables.txt"
    try:
        connection = oracledb.connect(user=credentials["user"],
                                      password=credentials["password"],
                                      dsn=DSN)
        tables = get_table_names(connection)
        # Open the file in append mode
        with open(output_file, 'a', encoding='utf-8') as f:
            for table in tables:
                print(f"{ICON_INFO} Processing table: {table}")
                columns = get_columns(connection, table)
                constraints = get_constraints(connection, table)
                sample_data = get_sample_data(connection, table, limit=10)
                write_table_definition(f, table, columns, constraints, sample_data)
    except oracledb.Error as e:
        print(f"{ICON_ERROR} Error processing schema {schema_name}: {e}")
    finally:
        if connection:
            connection.close()
            print(f"{ICON_INFO} Closed connection for schema {schema_name}")

def main():
    for schema, creds in schemas.items():
        process_schema(schema, creds)
    print(f"{ICON_SUCCESS} All schemas processed.")

if __name__ == '__main__':
    main()