"""
explainer.py — Business-Friendly Explanation Generator
========================================================
Uses Gemini to generate a clear, business-friendly explanation
of the SQL query results.

The explanation is based ONLY on the actual data — it never
invents numbers or information not present in the results.
"""

import pandas as pd
from google import genai
from app.config import (
    GEMINI_API_KEY, 
    GEMINI_MODEL,
    DATASET_NAME,
    SOURCE_PERIOD,
    SOURCE_ROW_COUNT,
    LOADED_ROW_COUNT,
    DATASET_MODE
)
import re

DANGER_WORDS = [
    "contraction", "displacement", "surge"
]

def validate_explanation_grounding(explanation: str, df: pd.DataFrame, dataset_context: str, client: genai.Client, user_prompt: str, system_prompt: str) -> str:
    """Check for hallucinations of domain-specific words not present in the dataset schema."""
    allowed_text = " ".join(df.columns).lower() if df is not None and not df.empty else ""
    if dataset_context:
        allowed_text += " " + dataset_context.lower()

    found_danger_words = []
    explanation_lower = explanation.lower()
    
    for word in DANGER_WORDS:
        # Check whole word match in explanation
        if re.search(rf"\b{word}\b", explanation_lower):
            # If the word is NOT in the allowed schema/metadata context, it's a hallucination
            if not re.search(rf"\b{word}\b", allowed_text):
                found_danger_words.append(word)

    if found_danger_words:
        warning = (
            f"\n\nCRITICAL CONTEXT INTEGRITY FAILURE: Your previous response hallucinated these domain-specific concepts: "
            f"{', '.join(found_danger_words)}. These DO NOT exist in the current dataset schema. "
            f"You MUST NOT mention these concepts. Regenerate the explanation strictly based on the provided columns."
        )
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt + warning,
                config={
                    "system_instruction": system_prompt,
                    "temperature": 0.1,
                }
            )
            return response.text.strip()
        except Exception:
            return explanation

    return explanation


EXPLAIN_SYSTEM_PROMPT = f"""You are a business analyst explaining database query results to a non-technical audience.

Given a user's question, the SQL query used, and the actual results, write a clear explanation.

Your explanation MUST include these sections:
1. **Direct Answer**: Answer the user's question in one clear sentence.
2. **Key Insights**: 2-3 interesting observations from the data.
3. **Method**: Brief description of how the data was obtained (in simple terms, not SQL).
4. **Caveats**: Any limitations or things to keep in mind (only if relevant).

DATASET AWARENESS RULES:
- The database currently contains a {DATASET_MODE} of {LOADED_ROW_COUNT:,} rows.
- The full original {DATASET_NAME} dataset for {SOURCE_PERIOD} contains {SOURCE_ROW_COUNT:,} rows.
- NEVER refer to the currently loaded rows as the "total trips in the dataset". Always clarify that the database currently has {LOADED_ROW_COUNT:,} trips loaded.
- For example: "Drishti currently has {LOADED_ROW_COUNT:,} {SOURCE_PERIOD} taxi trips loaded in its database. This is a {DATASET_MODE} and does not represent the full source dataset of {SOURCE_ROW_COUNT:,} rows."

STRICT RULES:
- ONLY use numbers and facts directly present in the actual query results.
- NEVER invent or estimate numbers not in the data.
- NEVER invent causes or infer societal reasons for data anomalies without supporting data.
- Distinguish observation from interpretation. Do not claim "Holiday activity caused X" unless causation is proven.
- If the results contain 'Unknown', 'None', or missing categories (e.g. for boroughs), explicitly state: "The analysis includes an Unknown or missing category because the official taxi zones lookup dataset explicitly defines some location IDs as 'Unknown' or leaves them unassigned." Do NOT claim that the location IDs are unmatched or invalid, as they are valid locations in the source data.
- **Factual Wording**: Avoid subjective language such as "varies significantly", "highest tipping", "most affordable", or "least expensive" unless the query strictly defines and proves those concepts. Prefer factual, dry wording like: "Manhattan had the highest calculated average tip percentage at X%." or "Bronx had the lowest calculated average tip percentage at Y%."
- **Follow-up Grounding**: If the query is a follow-up restricted to specific entities (e.g., top 5 products), explicitly state "Among the [N] [entities] identified in the previous analysis..." Do not say "among all products" unless the query is unbounded.
- Use simple, non-technical language.
- Format numbers with commas (e.g., 1,234,567).
- Format currency with $ signs (e.g., $15.50).
- Keep the explanation concise but informative.

Respond in plain text with markdown formatting. Do NOT use JSON."""


def generate_explanation(question: str, sql: str, df: pd.DataFrame,
                         status: str = "SUCCESS",
                         conversation_context: str = None,
                         metric_metadata: dict = None,
                         dataset_context: str = None) -> str:
    """
    Generate a business-friendly explanation of the query results.

    Args:
        question: The user's original question
        sql: The SQL query that was executed
        df: The result DataFrame
        status: The semantic status of the result (e.g. VALID_NO_MATCH)
        metric_metadata: Optional dict containing metric_name, definition, etc.

    Returns:
        str: The explanation text (markdown formatted)
    """
    # Prepare the result data for the LLM
    if df is not None and not df.empty:
        result_text = df.to_string(index=False)
        if len(result_text) > 3000:
            # Truncate very large results
            result_text = df.head(20).to_string(index=False)
            result_text += f"\n... ({len(df)} total rows)"
    else:
        result_text = "(Empty result - 0 rows)"

    user_prompt = f"""USER QUESTION: {question}

SQL QUERY USED:
{sql}

QUERY STATUS: {status}

QUERY RESULTS:
{result_text}"""

    if metric_metadata and metric_metadata.get("metric_name"):
        user_prompt += f"""

DERIVED METRIC CONTEXT:
The SQL used a derived metric called '{metric_metadata.get("metric_name")}'.
Definition: {metric_metadata.get("metric_definition")}
Numerator: {metric_metadata.get("numerator")}
Denominator: {metric_metadata.get("denominator")}
Zero-denominator policy: {metric_metadata.get("zero_denominator_policy")}

IMPORTANT: Your explanation MUST explicitly state how the metric was calculated (e.g., "Tip percentage is calculated as tip_amount divided by total_amount, multiplied by 100"). Do NOT invent your own definition."""

    # Add conversation context for follow-up explanations
    if conversation_context:
        user_prompt += f"""

{conversation_context}

This is a FOLLOW-UP question. Reference the previous analysis naturally in your
explanation.
IMPORTANT GROUNDING RULE: If the current query restricts its analysis to entities identified in the previous analysis (e.g., specific products, zones), your explanation MUST explicitly state that scope. For example: "Among the five products identified in the previous analysis, X had the highest aggregate profit margin at Y%." Do NOT say "among all products" or "in the dataset" unless the query explicitly asks to analyze all entities.
Your explanation must be grounded in the NEW query results above — do NOT
invent facts from the previous analysis."""

    user_prompt += """

Please explain these results to the user.
If QUERY STATUS is 'VALID_NO_MATCH', explicitly explain that no single entity met all conditions (e.g. 'X had the highest volume, but Y had the highest fare, so no single borough won both').
If QUERY STATUS is 'VALID_EMPTY_RESULT', explicitly explain that the data returned no matches for the requested criteria.
If QUERY STATUS is 'ANOMALY_TIMESTAMP', explicitly state: 'The query found midnight as the most common pickup hour in the current sample, but the unusually high concentration of midnight timestamps suggests a possible timestamp data-quality issue.' Do not confidently claim that midnight is the peak demand period."""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        # Use dynamic system prompt for uploaded datasets
        if dataset_context:
            system_prompt = (
                "You are a business analyst explaining database query results "
                "to a non-technical audience.\n\n"
                "Given a user's question, the SQL query used, and the actual results, "
                "write a clear explanation.\n\n"
                "Your explanation MUST include these sections:\n"
                "1. **Direct Answer**: Answer the user's question in one clear sentence.\n"
                "2. **Key Insights**: 2-3 interesting observations from the data.\n"
                "3. **Method**: Brief description of how the data was obtained (in simple terms).\n"
                "4. **Caveats**: Any limitations or things to keep in mind (only if relevant).\n\n"
                f"{dataset_context}\n\n"
                "STRICT RULES:\n"
                "- ONLY use numbers and facts directly present in the actual query results.\n"
                "- NEVER invent or estimate numbers not in the data.\n"
                "- Avoid subjective language. Prefer factual wording.\n"
                "- Use simple, non-technical language.\n"
                "- Format numbers with commas (e.g., 1,234,567).\n"
                "- Format currency with $ signs (e.g., $15.50).\n"
                "- Keep the explanation concise but informative.\n\n"
                "Respond in plain text with markdown formatting. Do NOT use JSON."
            )
        else:
            system_prompt = EXPLAIN_SYSTEM_PROMPT

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config={
                "system_instruction": system_prompt,
                "temperature": 0.3,
            }
        )

        explanation = response.text.strip()
        
        # Validate against cross-dataset context contamination
        explanation = validate_explanation_grounding(
            explanation=explanation,
            df=df,
            dataset_context=dataset_context,
            client=client,
            user_prompt=user_prompt,
            system_prompt=system_prompt
        )

        return explanation

    except Exception as e:
        # Fallback explanation if LLM fails
        return (
            f"**Results Summary**\n\n"
            f"Your query returned {len(df)} rows with {len(df.columns)} columns.\n\n"
            f"*(Detailed explanation unavailable: {str(e)})*"
        )
