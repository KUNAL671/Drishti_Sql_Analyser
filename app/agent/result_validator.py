"""
result_validator.py — Query Result Validator
==============================================
Validates the results returned by SQL execution to catch:
  1. Empty results
  2. Unexpected row counts
  3. Null-heavy results
  4. Obviously invalid numerical values
  5. Semantic mismatches with the user's question

If validation fails, it provides a clear description of the problem
so the SQL generator can fix the query.
"""

import pandas as pd


def validate_result(result: dict, question: str, sql: str) -> dict:
    """
    Validate the result of a SQL query.

    Args:
        result: The result dict from executor.execute_query()
        question: The user's original question
        sql: The SQL query that was executed

    Returns:
        dict with keys:
            - "valid": bool
            - "errors": list of error messages
            - "warnings": list of warning messages
    """
    errors = []
    warnings = []

    # ---- Check 0: Query execution failed ----
    if not result["success"]:
        errors.append(f"Query execution failed: {result['error']}")
        return {"valid": False, "errors": errors, "warnings": warnings}

    df = result["data"]

    status = "SUCCESS"

    # ---- Check 1: Empty results ----
    if df is None or len(df) == 0:
        q_lower = question.lower()
        sql_lower = sql.lower()
        
        # Classification heuristics
        if any(w in q_lower for w in ["both", "highest", "lowest", "same", "simultaneously", "which one satisfies"]):
            status = "VALID_NO_MATCH"
        elif any(w in q_lower for w in ["are there", "is there", "did anyone", " any trips "]):
            status = "VALID_EMPTY_RESULT"
        else:
            status = "INVALID_EMPTY_RESULT"
            
        if status == "INVALID_EMPTY_RESULT":
            errors.append(
                "Query returned no results. The query might be too restrictive, "
                "or the filter conditions might not match any data. "
                "Check date ranges, location IDs, or other filter values."
            )
            return {"valid": False, "status": status, "errors": errors, "warnings": warnings}
        else:
            # Valid empty result
            return {"valid": True, "status": status, "errors": errors, "warnings": warnings}

    # ---- Check 2: Unexpected row counts ----
    question_lower = question.lower()

    # If user asks for "top 5" but we got more or fewer rows
    top_n_match = _extract_top_n(question_lower)
    if top_n_match is not None:
        if len(df) > top_n_match:
            warnings.append(
                f"User asked for top {top_n_match} but query returned {len(df)} rows. "
                f"Consider adding LIMIT {top_n_match}."
            )
        elif len(df) < top_n_match:
            warnings.append(
                f"User asked for top {top_n_match} but only {len(df)} rows returned. "
                f"This might be correct if fewer results exist."
            )

    # If user asks for a single value but we got many rows
    single_value_keywords = ["what is the", "what's the", "how much", "how many", "what was the total", "what is the average"]
    if any(kw in question_lower for kw in single_value_keywords):
        if len(df) > 20:
            warnings.append(
                f"Question seems to ask for a single value/summary, but "
                f"query returned {len(df)} rows. Consider adding aggregation."
            )

    # ---- Check 3: Null-heavy results ----
    total_cells = df.size
    if total_cells > 0:
        null_count = df.isnull().sum().sum()
        null_pct = (null_count / total_cells) * 100
        if null_pct > 50:
            warnings.append(
                f"Result contains {null_pct:.1f}% NULL values. "
                f"The result may need COALESCE or WHERE IS NOT NULL filters."
            )

    # ---- Check 4: Invalid numerical values ----
    numeric_cols = df.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        col_lower = col.lower()

        # Check for negative values in columns that should be positive
        positive_cols = ["trip_count", "total_trips", "num_trips", "count", "avg_distance", "avg_fare"]
        if any(pc in col_lower for pc in positive_cols):
            neg_count = (df[col] < 0).sum()
            if neg_count > 0:
                warnings.append(
                    f"Column '{col}' has {neg_count} negative values, "
                    f"but this column should likely be positive."
                )

        # Check for extremely large values
        if df[col].max() > 1_000_000 and "id" not in col_lower:
            warnings.append(
                f"Column '{col}' has very large values (max: {df[col].max():,.2f}). "
                f"This might indicate an aggregation error."
            )

    # ---- Check 5: All values are the same ----
    if len(df) > 1:
        for col in df.columns:
            if df[col].nunique() == 1 and len(df) > 5:
                warnings.append(
                    f"Column '{col}' has the same value in all {len(df)} rows. "
                    f"This might indicate incorrect grouping."
                )

    # ---- Check 6: Hour distribution anomaly ----
    # If there's an hour column and a count/sum column, check if one hour dominates (>90%)
    hour_cols = [c for c in df.columns if "hour" in c.lower()]
    count_cols = [c for c in df.columns if any(x in c.lower() for x in ["count", "trips", "num"])]
    if hour_cols and count_cols and len(df) > 1:
        hour_col = hour_cols[0]
        count_col = count_cols[0]
        if pd.api.types.is_numeric_dtype(df[count_col]):
            total = df[count_col].sum()
            if total > 0:
                max_val = df[count_col].max()
                max_hour = df.loc[df[count_col].idxmax(), hour_col]
                pct = (max_val / total) * 100
                if pct > 90:
                    status = "ANOMALY_TIMESTAMP"
                    warnings.append(
                        f"Hour {max_hour} contains {pct:.1f}% of all records. "
                        f"This suggests a timestamp data-quality or sampling issue."
                    )

    # Warnings alone don't make the result invalid
    return {
        "valid": len(errors) == 0,
        "status": status,
        "errors": errors,
        "warnings": warnings,
    }


def _extract_top_n(question: str) -> int | None:
    """
    Extract the N from questions like "top 5", "first 10", "bottom 3", etc.

    Args:
        question: The lowercase question text

    Returns:
        int or None: The number N, or None if not found
    """
    import re

    patterns = [
        r'top\s+(\d+)',
        r'first\s+(\d+)',
        r'bottom\s+(\d+)',
        r'(\d+)\s+most',
        r'(\d+)\s+least',
        r'(\d+)\s+best',
        r'(\d+)\s+worst',
        r'(\d+)\s+highest',
        r'(\d+)\s+lowest',
        r'(\d+)\s+busiest',
    ]

    for pattern in patterns:
        match = re.search(pattern, question)
        if match:
            return int(match.group(1))

    return None
