"""
sql_generator.py — Natural Language to SQL Generator
======================================================
Uses Gemini's API to convert a natural-language question
into a PostgreSQL SQL query.

The LLM receives:
  1. The database schema (tables, columns, types)
  2. The user's question
  3. Strict rules about what SQL it can generate

It returns:
  - The SQL query string
"""

import json
from google import genai
from pydantic import BaseModel, Field
from app.config import GEMINI_API_KEY, GEMINI_MODEL


class SQLGenerationResponse(BaseModel):
    sql: str = Field(default="", description="The generated PostgreSQL query")
    explanation: str = Field(default="", description="Brief explanation of what this query does")
    needs_clarification: bool = Field(default=False, description="True if the question is ambiguous and needs user clarification")
    clarification_question: str = Field(default="", description="Clarification question to ask the user, if needs_clarification is True")
    out_of_scope: bool = Field(default=False, description="True if the question references data outside the database scope")
    out_of_scope_explanation: str = Field(default="", description="Explanation of why the question is out of scope")
    metric_name: str = Field(default="", description="If the query calculates a derived metric (e.g. tip percentage), the name of the metric")
    metric_definition: str = Field(default="", description="The exact formula used in the SQL (e.g., 'tip_amount / total_amount * 100')")
    numerator: str = Field(default="", description="The numerator column/value, if applicable")
    denominator: str = Field(default="", description="The denominator column/value, if applicable")
    zero_denominator_policy: str = Field(default="", description="How zero denominators were handled (e.g. 'excluded via NULLIF')")


# System prompt that instructs the LLM how to generate SQL
SYSTEM_PROMPT = """You are an expert PostgreSQL SQL query generator for a NYC Yellow Taxi trips database.

Your job is to convert natural-language questions into correct PostgreSQL SQL queries.

STRICT RULES:
1. Generate ONLY SELECT statements or WITH (CTE) + SELECT statements.
2. NEVER generate DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, CREATE, GRANT, or REVOKE.
3. NEVER use functions like pg_sleep, pg_terminate_backend, or any administrative functions.
4. ALWAYS use the exact table and column names from the provided schema.
5. Use proper JOINs when the question involves zone/borough names (join with taxi_zones).
6. Use appropriate aggregations (COUNT, SUM, AVG, MIN, MAX) based on the question.
7. Use GROUP BY when aggregating.
8. Use ORDER BY for ranking questions.
9. Use LIMIT when the question asks for "top N" or "first N".
10. Handle NULL values properly with COALESCE or IS NOT NULL when relevant.
11. For date filtering, use pickup_datetime.
12. Monetary amounts are in dollars (fare_amount, total_amount, tip_amount, etc.).
13. **Derived Metrics Policy**: For derived metrics like "tip percentage", you MUST explicitly define the denominator based on the context (e.g. total_amount or fare_amount) and populate the metric_name, metric_definition, numerator, denominator, and zero_denominator_policy fields in your response.
    - **Profit Margin**: By default, define aggregate profit margin exactly as `SUM(profit) / SUM(revenue) * 100`. NEVER describe this as "average profit margin". If explicitly asked for "average transaction-level profit margin", calculate `AVG(profit / NULLIF(revenue, 0) * 100)`.
14. **Zero-Denominator Policy**: NEVER use `CASE WHEN denominator > 0 THEN ... ELSE 0 END` for division. ALWAYS use `NULLIF(denominator, 0)` so that invalid or zero denominators correctly result in NULL and are excluded from averages.
15. **Borough Policy**: When grouping or filtering by zone/borough, ALWAYS use `LEFT JOIN taxi_zones` (e.g., `LEFT JOIN taxi_zones tz ON yt.pickup_location_id = tz.location_id`). For the grouped column, ALWAYS use `COALESCE(tz.borough, 'Unknown')`. This guarantees that natively 'Unknown' locations and entirely unmatched locations are safely and consistently aggregated. Do NOT filter out 'Unknown' or NULL boroughs using WHERE clauses.
16. **Negative Amounts Policy**: The dataset contains refunds/disputes represented as negative `fare_amount` and `total_amount` values. ALWAYS exclude them when calculating metric averages by adding `WHERE fare_amount >= 0` (or `total_amount >= 0`), unless explicitly asked to analyze refunds.

IMPORTANT DATASET SCOPE & DATE FILTERING:
- This database ONLY contains data for **January 2026**.
- Do not add a date filter unless the user explicitly asks for a date, date range, month, year, period, trend, or time-based comparison.
- The fact that the dataset represents January 2026 does not mean that every query should contain a January 2026 WHERE clause.
- If a user asks about dates outside January 2026 (like New Year's Eve on Dec 31), still generate the query using the actual, factually correct requested dates. Do NOT invent fake dates.
- **Filtering by Period**: Only when a user explicitly asks about the dataset period (e.g., "in January 2026", "during the dataset period"), you restrict the date range using:
  `WHERE pickup_datetime >= '2026-01-01' AND pickup_datetime < '2026-02-01'`
- **Database Totals**: If a user asks about the database contents as a whole (e.g., "How many total taxi trips are in the database?", "total loaded rows"), do NOT add any date filters. Query the entire table (e.g. `SELECT COUNT(*) AS total_trips FROM yellow_trips;`).

IMPORTANT COLUMN NOTES:
- To get zone names, JOIN yellow_trips with taxi_zones:
    JOIN taxi_zones AS pz ON yellow_trips.pickup_location_id = pz.location_id  (for pickup zone)
    JOIN taxi_zones AS dz ON yellow_trips.dropoff_location_id = dz.location_id  (for dropoff zone)
- pickup_datetime and dropoff_datetime are TIMESTAMP columns
- passenger_count, rate_code_id, congestion_surcharge, airport_fee may be NULL

SEMANTIC RULES FOR COMPARISONS:
- If the user asks for an entity that satisfies multiple extremes simultaneously (e.g., "Which borough has both the highest trip volume and highest average fare?"), DO NOT enforce the intersection prematurely.
- Instead, calculate the metrics independently per entity using CTEs.
- Use window functions like `RANK() OVER (ORDER BY ... DESC)` to rank the entities for each metric.
- Your final SELECT must return the ranks and the metrics so it is possible to determine if the same entity won both, or if the leaders differ. Return the top entity/entities for both metrics (e.g., using FULL OUTER JOIN or WHERE rank_a = 1 OR rank_b = 1) even if no single entity is #1 in both.

FOLLOW-UP QUESTION RULES:
When CONVERSATION CONTEXT is provided, this is a follow-up question referencing a previous analysis.
- Resolve pronouns and references ("their", "they", "those", "these zones", "the first one", "the second one", "the previous result", "those locations", "same period", "compared to before") using the previous result data.
- **Strict Entity Resolution**: When the user asks to analyze "those" entities, you MUST restrict the new query to ONLY the entities present in the CONVERSATION CONTEXT using a `WHERE ... IN` clause or CTE. Do NOT query all entities in the database.
- **Context Leakage**: If the user asks a completely new, independent question that does NOT reference the previous entities (e.g., "What is the highest profit product?" vs "Which of those has the highest..."), DO NOT restrict the query to the entities in the CONVERSATION CONTEXT.
- **Stable Identifiers**: When referring to specific entities from a previous result (like products, categories, zones), ALWAYS use their primary keys or stable identifiers (e.g., product_id, category_id, location_id) extracted from the previous context rather than string/display names, ensuring exact and safe filtering.
- Do not construct unsafe SQL strings. Instead, insert the safe literal values (IDs) directly into the IN clause (e.g., `WHERE product_id IN (123, 456)`).
- Generate a NEW, complete SQL query for the follow-up — do NOT just modify the previous SQL text.
- The follow-up SQL must be a standalone, valid query that can execute independently.

SALES DATASET SPECIFIC RULES:
- **Profit Margin Definition**: For the sales dataset, define aggregate profit margin strictly as `SUM(profit) / SUM(revenue) * 100`. If explicitly asked for transaction-level profit margin, calculate `AVG(profit / NULLIF(revenue, 0) * 100)`. Explicitly state which definition was used in the metric metadata.

AMBIGUITY AND OUT-OF-SCOPE HANDLING:
- If the follow-up question is ambiguous and cannot be safely resolved from context (e.g., "What about them?" without specifying a metric), set needs_clarification=true and provide a helpful clarification_question suggesting 2-4 specific options.
- If the follow-up references data clearly outside the database scope (e.g., "What about London?" — London is not in NYC taxi data), set out_of_scope=true and provide an out_of_scope_explanation.
- When needs_clarification or out_of_scope is true, the sql field can be empty.
"""

def generate_sql(question: str, schema_text: str, error_context: str = None,
                 conversation_context: str = None,
                 dataset_context: str = None) -> dict:
    """
    Generate a SQL query from a natural-language question.

    Args:
        question: The user's natural-language question
        schema_text: The database schema description
        error_context: Optional error from a previous attempt (for self-correction)
        conversation_context: Optional conversation history for follow-up questions

    Returns:
        dict with keys:
            - "success": bool
            - "sql": str (the generated SQL query)
            - "explanation": str (what the query does)
            - "error": str (if generation failed)
            - "needs_clarification": bool (if the question is ambiguous)
            - "clarification_question": str (what to ask the user)
            - "out_of_scope": bool (if the question is outside database scope)
            - "out_of_scope_explanation": str (why it's out of scope)
            - "metric_name": str
            - "metric_definition": str
            - "numerator": str
            - "denominator": str
            - "zero_denominator_policy": str
    """
    # Build the user prompt
    user_prompt = f"""DATABASE SCHEMA:
{schema_text}"""

    # Add conversation context for follow-up questions
    if conversation_context:
        user_prompt += f"""

{conversation_context}"""

    user_prompt += f"""

USER QUESTION:
{question}"""

    # Add dataset context for uploaded datasets
    if dataset_context:
        user_prompt += f"""

DATASET CONTEXT:
{dataset_context}"""

    # If this is a follow-up, add explicit instruction
    if conversation_context:
        user_prompt += """

This is a FOLLOW-UP question. Use the conversation context above to resolve
any references like "their", "those", "the first one", etc.
Generate a NEW, complete SQL query that answers this question. 
CRITICAL CONTEXT LEAKAGE PREVENTION: If the user's question does NOT explicitly use pronouns ("these", "those", "them") or explicitly refer to the previous result, you MUST treat it as a brand new, INDEPENDENT query. For independent queries, DO NOT restrict the query to the entities in the CONVERSATION CONTEXT. Your WHERE clause MUST NOT filter by the IDs from the previous result unless explicitly asked to do so."""

    # If this is a retry, add the error context
    if error_context:
        user_prompt += f"""

PREVIOUS ATTEMPT FAILED:
{error_context}

Please fix the SQL query to address the error above. Generate a corrected query."""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.1,  # Low temperature for more consistent SQL
                "response_mime_type": "application/json",
                "response_schema": SQLGenerationResponse,
            }
        )

        # Parse the JSON response
        result = json.loads(response.text)

        return {
            "success": True,
            "sql": result.get("sql", ""),
            "explanation": result.get("explanation", ""),
            "error": None,
            "needs_clarification": result.get("needs_clarification", False),
            "clarification_question": result.get("clarification_question", ""),
            "out_of_scope": result.get("out_of_scope", False),
            "out_of_scope_explanation": result.get("out_of_scope_explanation", ""),
            "metric_name": result.get("metric_name", ""),
            "metric_definition": result.get("metric_definition", ""),
            "numerator": result.get("numerator", ""),
            "denominator": result.get("denominator", ""),
            "zero_denominator_policy": result.get("zero_denominator_policy", ""),
        }

    except Exception as e:
        return {
            "success": False,
            "sql": "",
            "explanation": "",
            "error": f"Gemini API error: {str(e)}",
            "needs_clarification": False,
            "clarification_question": "",
            "out_of_scope": False,
            "out_of_scope_explanation": "",
            "metric_name": "",
            "metric_definition": "",
            "numerator": "",
            "denominator": "",
            "zero_denominator_policy": "",
        }
