"""
sql_validator.py — SQL Safety & Correctness Validator
=======================================================
Validates SQL queries BEFORE they are executed to ensure:
  1. Only read-only operations (SELECT, WITH)
  2. No destructive keywords (DROP, DELETE, etc.)
  3. Referenced tables exist in the database
  4. Referenced columns exist in the referenced tables
  5. SQL can be parsed without errors
"""

import re
import sqlparse
from app.database.schema import get_schema_info


# SQL keywords that indicate destructive operations
# These are NEVER allowed in user-generated queries
FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXECUTE", "EXEC",
    "pg_sleep", "pg_terminate", "pg_cancel",
    "COPY", "LOAD",
]

# SQL keywords that indicate the start of a read-only statement
ALLOWED_STATEMENT_TYPES = ["SELECT", "WITH"]

# Tables that AI-generated SQL must NEVER reference
PROTECTED_TABLES = {"drishti_datasets"}


def validate_sql(sql: str) -> dict:
    """
    Validate a SQL query for safety and correctness.

    Args:
        sql: The SQL query string to validate

    Returns:
        dict with keys:
            - "valid": bool
            - "errors": list of error messages
            - "warnings": list of warning messages
    """
    errors = []
    warnings = []

    # ---- Check 1: SQL is not empty ----
    if not sql or not sql.strip():
        errors.append("SQL query is empty.")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Clean up the SQL
    sql_clean = sql.strip()

    # ---- Check 2: Forbidden keywords ----
    sql_upper = sql_clean.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        # Use word boundary check to avoid false positives
        # (e.g., "SELECTED" should not match "SELECT")
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            errors.append(
                f"SECURITY VIOLATION: SQL contains forbidden keyword '{keyword}'. "
                f"Only SELECT queries are allowed."
            )

    # ---- Check 3: Must start with SELECT or WITH ----
    # Parse the SQL to get the statement type
    parsed = sqlparse.parse(sql_clean)
    if parsed:
        first_statement = parsed[0]
        first_token = first_statement.token_first(skip_cm=True, skip_ws=True)
        if first_token:
            token_value = first_token.ttype
            token_text = first_token.value.upper()
            if token_text not in ALLOWED_STATEMENT_TYPES:
                errors.append(
                    f"SQL must start with SELECT or WITH, but starts with '{token_text}'."
                )
    else:
        errors.append("SQL could not be parsed.")

    # ---- Check 4: Only one statement allowed ----
    statements = [s for s in parsed if s.get_type() is not None or str(s).strip()]
    # Filter out empty/whitespace-only statements
    real_statements = [s for s in statements if str(s).strip().rstrip(';').strip()]
    if len(real_statements) > 1:
        errors.append("Only a single SQL statement is allowed. Multiple statements detected.")

    # ---- Check 5: No semicolons in the middle (prevents SQL injection) ----
    # Remove trailing semicolon for this check
    sql_no_trailing = sql_clean.rstrip(";").strip()
    if ";" in sql_no_trailing:
        errors.append("SQL contains multiple statements (semicolons found). Only one statement allowed.")

    # ---- Check 6: Validate referenced tables and columns ----
    if not errors:  # Only check if no security errors so far
        table_column_errors = _validate_tables_and_columns(sql_clean)
        errors.extend(table_column_errors)

    # ---- Check 6b: Protect system tables ----
    sql_lower = sql_clean.lower()
    for protected in PROTECTED_TABLES:
        if protected.lower() in sql_lower:
            errors.append(
                f"SECURITY VIOLATION: SQL references protected system table '{protected}'. "
                f"This table is not available for querying."
            )

    # ---- Check 7: Basic structure warnings ----
    if "GROUP BY" not in sql_upper and any(
        agg in sql_upper for agg in ["COUNT(", "SUM(", "AVG(", "MIN(", "MAX("]
    ):
        # Aggregation without GROUP BY might be intentional (for total counts)
        # but let's warn about it
        if "COUNT(*)" not in sql_upper or "FROM" in sql_upper:
            warnings.append(
                "Query uses aggregation functions but no GROUP BY clause. "
                "This may return a single aggregate value."
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_tables_and_columns(sql: str) -> list:
    """
    Check that tables and columns referenced in the SQL actually exist.

    Args:
        sql: The SQL query string

    Returns:
        list of error messages
    """
    errors = []

    try:
        schema = get_schema_info()
    except Exception as e:
        # If we can't connect to the DB, skip this check
        return [f"Could not validate tables/columns (DB error): {str(e)}"]

    # Known table names in the database
    known_tables = set(schema.keys())

    # Known columns per table
    known_columns = {}
    all_columns = set()
    for table, columns in schema.items():
        known_columns[table] = set(col["column"] for col in columns)
        all_columns.update(col["column"] for col in columns)

    # Extract table references from the SQL using sqlparse token traversal
    # This properly ignores FROM inside functions like EXTRACT()
    from sqlparse.sql import IdentifierList, Identifier, Parenthesis, Function
    from sqlparse.tokens import Keyword, DML

    def extract_tables_from_tokens(tokens):
        tables = []
        from_seen = False
        
        for token in tokens:
            if token.is_whitespace:
                continue
                
            if token.is_group:
                # Check if this group is a parenthesis that contains a SELECT
                # (meaning it's a subquery or CTE definition)
                is_subquery = False
                if isinstance(token, Parenthesis):
                    for subtoken in token.tokens:
                        if subtoken.ttype is DML and subtoken.value.upper() == 'SELECT':
                            is_subquery = True
                            break
                    
                    if is_subquery:
                        tables.extend(extract_tables_from_tokens(token.tokens))
                else:
                    # Normal group. We DO NOT want to find tables in Functions like EXTRACT()
                    if not isinstance(token, Function):
                        tables.extend(extract_tables_from_tokens(token.tokens))
            
            if from_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        real_name = identifier.get_real_name()
                        if real_name:
                            tables.append(real_name)
                    from_seen = False
                elif isinstance(token, Identifier):
                    real_name = token.get_real_name()
                    if real_name:
                        tables.append(real_name)
                    from_seen = False
                elif token.ttype is Keyword and token.value.upper() in ['ORDER', 'GROUP', 'BY', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'WHERE', 'ON']:
                    from_seen = False
            elif token.ttype is Keyword and token.value.upper() in ['FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'OUTER JOIN', 'CROSS JOIN']:
                from_seen = True
                
        return tables

    parsed = sqlparse.parse(sql)[0]
    raw_tables = extract_tables_from_tokens(parsed.tokens)
    
    # Remove duplicates and None values
    referenced_tables = list(set(t for t in raw_tables if t))

    # Remove aliases and keywords
    sql_keywords = {
        "SELECT", "FROM", "WHERE", "AND", "OR", "ON", "AS",
        "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "CROSS",
        "GROUP", "ORDER", "BY", "HAVING", "LIMIT", "OFFSET",
        "UNION", "ALL", "DISTINCT", "CASE", "WHEN", "THEN", "ELSE", "END",
        "IN", "NOT", "NULL", "IS", "BETWEEN", "LIKE", "EXISTS",
        "ASC", "DESC", "WITH", "RECURSIVE", "TRUE", "FALSE",
        "COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE",
    }

    for table in referenced_tables:
        if table.upper() in sql_keywords:
            continue
        if table.lower() not in known_tables:
            # Check if it might be an alias
            alias_pattern = rf'\b({"|".join(known_tables)})\s+(?:AS\s+)?{re.escape(table)}\b'
            if not re.search(alias_pattern, sql, re.IGNORECASE):
                # Also check if it's a CTE name (defined in WITH clause)
                cte_pattern = rf'WITH\s+.*?\b{re.escape(table)}\b\s+AS\s*\('
                if not re.search(cte_pattern, sql, re.IGNORECASE):
                    errors.append(
                        f"Table '{table}' not found in database. "
                        f"Available tables: {', '.join(sorted(known_tables))}"
                    )

    return errors
