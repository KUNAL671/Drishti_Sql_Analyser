"""
orchestrator.py — Agent Orchestrator
=======================================
This is the BRAIN of the application. It coordinates the entire
pipeline from user question to final answer:

1. Understand the question
2. Retrieve database schema
3. Generate SQL from the question
4. Validate the SQL for safety
5. Execute the SQL query
6. Validate the results
7. Retry/self-correct if needed (up to 3 attempts)
8. Select visualization type
9. Generate business explanation
10. Return everything to the UI

This implements a controlled agent workflow — no arbitrary
code execution by the LLM.
"""

from app.agent.schema_retriever import get_schema_for_llm
from app.agent.sql_generator import generate_sql
from app.agent.sql_validator import validate_sql
from app.agent.result_validator import validate_result
from app.agent.visualizer import select_visualization, create_chart
from app.agent.explainer import generate_explanation
from app.database.executor import execute_query
from app.config import MAX_RETRY_ATTEMPTS
import time


def process_question(question: str, status_callback=None,
                     conversation_context: str = None,
                     dataset_id: str = None) -> dict:
    """
    Process a natural-language question through the full agent pipeline.

    Args:
        question: The user's natural-language question
        status_callback: Optional function to update the UI with progress
                        Called as: status_callback(stage_name, details)

    Returns:
        dict with keys:
            - "success": bool
            - "question": str (original question)
            - "sql": str (the final SQL query)
            - "sql_explanation": str (what the SQL does)
            - "data": DataFrame (query results)
            - "row_count": int
            - "columns": list
            - "chart": plotly figure or None
            - "viz_meta": dict (visualization metadata)
            - "explanation": str (business explanation)
            - "attempts": int (number of SQL generation attempts)
            - "retry_history": list of attempt details
            - "error": str (if completely failed)
            - "needs_clarification": bool (if follow-up is ambiguous)
            - "clarification_question": str (what to ask the user)
            - "out_of_scope": bool (if question is outside database scope)
            - "out_of_scope_explanation": str (why it's out of scope)
    """

    def update_status(stage, details=""):
        """Helper to send status updates to the UI."""
        if status_callback:
            status_callback(stage, details)

    retry_history = []
    error_context = None

    # ================================================================
    # STAGE 1: Understand the question
    # ================================================================
    update_status("Understanding question", question)

    if not question or not question.strip():
        return _error_result(question, "Please enter a question.")

    # ================================================================
    # STAGE 2: Retrieve database schema
    # ================================================================
    update_status("Finding schema", "Retrieving database tables and columns...")

    try:
        schema_text = get_schema_for_llm(dataset_id=dataset_id)
    except Exception as e:
        return _error_result(question, f"Could not retrieve database schema: {str(e)}")

    # Build dataset context for uploaded datasets
    dataset_context = None
    target_schema = []
    if dataset_id is not None:
        try:
            from app.data.dataset_registry import get_dataset
            from app.data.schema_generator import generate_dataset_context
            ds_meta = get_dataset(dataset_id)
            if ds_meta:
                dataset_context = generate_dataset_context(ds_meta)
                target_schema = ds_meta.get("schema_metadata", [])
        except Exception:
            pass  # Fall through — SQL generator works without context
    else:
        # Default Taxi Dataset schema representation for the UI
        target_schema = [
            {"name": "pickup_location_id", "type": "SMALLINT"},
            {"name": "dropoff_location_id", "type": "SMALLINT"},
            {"name": "fare_amount", "type": "NUMERIC"},
            {"name": "trip_distance", "type": "DOUBLE PRECISION"},
            {"name": "pickup_datetime", "type": "TIMESTAMP"},
        ]

    # Initialize total timing
    total_start_time = time.time()

    # ================================================================
    # RETRY LOOP: Stages 3-6 can retry up to MAX_RETRY_ATTEMPTS times
    # ================================================================
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        attempt_detail = {}

        # ============================================================
        # STAGE 3: Generate SQL
        # ============================================================
        update_status(
            "Generating SQL",
            f"Attempt {attempt}/{MAX_RETRY_ATTEMPTS}" + (" (retrying...)" if attempt > 1 else ""),
        )

        t0 = time.time()
        gen_result = generate_sql(question, schema_text, error_context,
                                  conversation_context=conversation_context,
                                  dataset_context=dataset_context)
        sql_gen_time_ms = int((time.time() - t0) * 1000)
        attempt_detail["durations"] = {"sql_generation_ms": sql_gen_time_ms}

        # ---- Check for clarification or out-of-scope (follow-up only) ----
        if gen_result.get("needs_clarification"):
            update_status("Complete", "Clarification needed")
            return {
                "success": True,
                "question": question,
                "sql": "",
                "sql_explanation": "",
                "data": None,
                "row_count": 0,
                "columns": [],
                "chart": None,
                "viz_meta": {},
                "explanation": "",
                "attempts": 0,
                "retry_history": [],
                "error": None,
                "needs_clarification": True,
                "clarification_question": gen_result.get("clarification_question", ""),
                "out_of_scope": False,
                "out_of_scope_explanation": "",
                "execution_time_ms": int((time.time() - total_start_time) * 1000),
            }

        if gen_result.get("out_of_scope"):
            update_status("Complete", "Out of scope")
            return {
                "success": True,
                "question": question,
                "sql": "",
                "sql_explanation": "",
                "data": None,
                "row_count": 0,
                "columns": [],
                "chart": None,
                "viz_meta": {},
                "explanation": "",
                "attempts": 0,
                "retry_history": [],
                "error": None,
                "needs_clarification": False,
                "clarification_question": "",
                "out_of_scope": True,
                "out_of_scope_explanation": gen_result.get("out_of_scope_explanation", ""),
                "target_schema": target_schema,
                "execution_time_ms": int((time.time() - total_start_time) * 1000),
            }

        if not gen_result["success"]:
            attempt_detail.update({
                "attempt": attempt,
                "stage": "SQL Generation",
                "error": gen_result["error"],
            })
            retry_history.append(attempt_detail)
            error_context = gen_result["error"]
            continue

        sql = gen_result["sql"]
        sql_explanation = gen_result["explanation"]
        attempt_detail["sql"] = sql
        attempt_detail["stage"] = "SQL Generated"

        # ============================================================
        # STAGE 4: Validate SQL
        # ============================================================
        update_status("Validating SQL", "Checking safety and correctness...")

        t1 = time.time()
        validation = validate_sql(sql)
        sql_val_time_ms = int((time.time() - t1) * 1000)
        attempt_detail["durations"]["sql_validation_ms"] = sql_val_time_ms

        if not validation["valid"]:
            error_msg = "SQL Validation Errors:\n" + "\n".join(validation["errors"])
            attempt_detail.update({
                "attempt": attempt,
                "stage": "SQL Validation Failed",
                "error": error_msg,
            })
            retry_history.append(attempt_detail)
            error_context = error_msg
            continue

        # ============================================================
        # STAGE 5: Execute SQL
        # ============================================================
        update_status("Executing query", "Running SQL against the database...")

        t2 = time.time()
        exec_result = execute_query(sql)
        db_exec_time_ms = int((time.time() - t2) * 1000)
        attempt_detail["durations"]["db_execution_ms"] = db_exec_time_ms

        if not exec_result["success"]:
            error_msg = f"Query Execution Error: {exec_result['error']}"
            attempt_detail.update({
                "attempt": attempt,
                "stage": "SQL Execution Failed",
                "error": error_msg,
            })
            retry_history.append(attempt_detail)
            error_context = error_msg
            continue

        # ============================================================
        # STAGE 6: Validate results
        # ============================================================
        update_status("Validating result", "Checking result quality...")

        t3 = time.time()
        result_validation = validate_result(exec_result, question, sql)
        res_val_time_ms = int((time.time() - t3) * 1000)
        attempt_detail["durations"]["result_validation_ms"] = res_val_time_ms

        if not result_validation["valid"]:
            error_msg = "Result Validation Errors:\n" + "\n".join(result_validation["errors"])
            attempt_detail.update({
                "attempt": attempt,
                "stage": "Result Validation Failed",
                "error": error_msg,
            })
            retry_history.append(attempt_detail)
            error_context = error_msg
            continue

        # ============================================================
        # SUCCESS: We have valid results!
        # ============================================================
        df = exec_result["data"]

        # Log any warnings
        if result_validation["warnings"] or validation.get("warnings"):
            all_warnings = validation.get("warnings", []) + result_validation.get("warnings", [])
            attempt_detail["warnings"] = all_warnings

        attempt_detail.update({
            "attempt": attempt,
            "stage": "Success",
            "row_count": len(df),
        })
        retry_history.append(attempt_detail)

        # ============================================================
        # STAGE 7: Select visualization
        # ============================================================
        update_status("Generating visualization", "Choosing the best chart type...")

        if len(df) > 0:
            viz_meta = select_visualization(question, sql, df)
            chart = create_chart(df, viz_meta)
        else:
            viz_meta = {}
            chart = None

        # Extract metric metadata for explainer and UI
        metric_metadata = {
            "metric_name": gen_result.get("metric_name", ""),
            "metric_definition": gen_result.get("metric_definition", ""),
            "numerator": gen_result.get("numerator", ""),
            "denominator": gen_result.get("denominator", ""),
            "zero_denominator_policy": gen_result.get("zero_denominator_policy", ""),
        }

        # ============================================================
        # STAGE 8: Generate explanation
        # ============================================================
        update_status("Writing explanation", "Creating a business-friendly summary...")

        explanation = generate_explanation(question, sql, df,
                                            result_validation.get("status", "SUCCESS"),
                                            conversation_context=conversation_context,
                                            metric_metadata=metric_metadata,
                                            dataset_context=dataset_context)

        update_status("Complete", "Done!")

        return {
            "success": True,
            "status": result_validation.get("status", "SUCCESS"),
            "question": question,
            "sql": sql,
            "sql_explanation": sql_explanation,
            "data": df,
            "row_count": len(df),
            "columns": list(df.columns) if df is not None and not df.empty else [],
            "chart": chart,
            "viz_meta": viz_meta,
            "explanation": explanation,
            "metric_metadata": metric_metadata,
            "attempts": attempt,
            "retry_history": retry_history,
            "error": None,
            "needs_clarification": False,
            "clarification_question": "",
            "out_of_scope": False,
            "out_of_scope_explanation": "",
            "target_schema": target_schema,
            "execution_time_ms": int((time.time() - total_start_time) * 1000),
        }

    # ================================================================
    # ALL ATTEMPTS EXHAUSTED
    # ================================================================
    update_status("Failed", f"Could not generate a valid query after {MAX_RETRY_ATTEMPTS} attempts.")

    return {
        "success": False,
        "question": question,
        "sql": "",
        "sql_explanation": "",
        "data": None,
        "row_count": 0,
        "columns": [],
        "chart": None,
        "viz_meta": {},
        "explanation": "",
        "attempts": MAX_RETRY_ATTEMPTS,
        "retry_history": retry_history,
        "error": (
            f"Failed after {MAX_RETRY_ATTEMPTS} attempts. "
            f"Last error: {error_context}"
        ),
        "target_schema": target_schema,
        "execution_time_ms": int((time.time() - total_start_time) * 1000),
    }


def _error_result(question: str, error: str) -> dict:
    """Helper to create a standardized error result."""
    return {
        "success": False,
        "question": question,
        "sql": "",
        "sql_explanation": "",
        "data": None,
        "row_count": 0,
        "columns": [],
        "chart": None,
        "viz_meta": {},
        "explanation": "",
        "attempts": 0,
        "retry_history": [],
        "error": error,
        "needs_clarification": False,
        "clarification_question": "",
        "out_of_scope": False,
        "out_of_scope_explanation": "",
    }
