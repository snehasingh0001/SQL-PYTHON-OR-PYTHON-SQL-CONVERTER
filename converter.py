import ast
import re

def sql_to_python(sql_code):
    sql_str = sql_code.strip()
    sql_upper = sql_str.upper()

    # Cover all SQL cases
    if re.search(r"INSERT\s+INTO|UPDATE|DROP\s+TABLE|TRUNCATE\s+TABLE", sql_upper):
        comment = "# Python code for INSERT/UPDATE/DROP/TRUNCATE"
    elif re.search(r"SELECT\s+\*|WHERE|HAVING|LIMIT|IN|BETWEEN|LIKE", sql_upper):
        comment = "# Python code for complex SELECT query"
    elif re.search(r"LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|FULL\s+OUTER\s+JOIN", sql_upper):
        comment = "# Python code for JOIN query"
    elif sql_upper.count("SELECT") > 1:
        comment = "# Python code for subquery (might require manual adjustments)"
    else:
        return "# Unsupported or unknown SQL command."

    return (
        f"{comment}\n"
        f"cursor.execute('''{sql_str}''')\n"
        "rows = cursor.fetchall()\n"
        "for row in rows:\n"
        "    print(row)"
    )

def python_to_sql(python_code):
    # Detect parameterized or multiline query
    pattern = r"cursor\.execute\(\s*['\"]{3}(?P<sql>.*?)[\"']{3}\s*(?:,\s*(?P<params>.*?))?\)"
    match = re.search(pattern, python_code, re.DOTALL)
    if match:
        return match.group('sql').strip()

    # Detect pandas patterns
    if "df.groupby" in python_code:
        return "-- Detected pandas df.groupby(): consider translating to SQL GROUP BY"
    if "df.query" in python_code:
        return "-- Detected pandas df.query(): this is a WHERE filter"

    return "Error: No valid SQL query found inside Python code."

def optimize_sql(sql_code):
    sql = sql_code
    sql = re.sub(r"SELECT\s+\*", "SELECT id, name", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s+WHERE\s+1\s*=\s*1", "", sql, flags=re.IGNORECASE)
    return sql

def optimize_python(python_code):
    try:
        tree = ast.parse(python_code)
        return ast.unparse(tree)
    except Exception:
        return python_code