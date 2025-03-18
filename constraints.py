def get_table_constraints(cursor, table_name):
    """Fetches all constraints for a table."""
    constraints_query = """
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

    cursor.execute(constraints_query, {"table_name": table_name})
    constraints = []
    
    for row in cursor.fetchall():
        constraints.append({
            "constraint_name": row[0],
            "type": row[1],
            "column": row[2],
            "referenced_table": row[4] if row[1] == 'R' else None,  # FK
            "referenced_column": row[5] if row[1] == 'R' else None  # FK
        })
    
    return constraints