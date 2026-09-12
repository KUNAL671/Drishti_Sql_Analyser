"""
schema_generator.py — LLM Schema & Question Generator
========================================================
Generates the schema text that the LLM receives for uploaded
datasets, and generates suggested starter questions based on
the column types and names.
"""


def generate_schema_for_llm(dataset_metadata: dict) -> str:
    """
    Generate a human-readable schema description for the LLM,
    matching the format used by the existing taxi schema.

    Args:
        dataset_metadata: Dict from dataset_registry.get_dataset()

    Returns:
        str: Schema description string
    """
    table_name = dataset_metadata["table_name"]
    schema_meta = dataset_metadata["schema_metadata"]
    dataset_name = dataset_metadata["dataset_name"]
    row_count = dataset_metadata["row_count"]
    date_range = dataset_metadata.get("date_range", "N/A")

    lines = []
    lines.append("DATABASE SCHEMA")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"TABLE: {table_name}")
    lines.append("-" * 40)

    for col in schema_meta:
        db_name = col["db_name"]
        pg_type = col["pg_type"]
        nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
        original = col.get("original_name", db_name)

        # Format like the existing taxi schema
        line = f"  {db_name:<30} {pg_type:<20} {nullable}"
        lines.append(line)

    lines.append("")
    lines.append("NOTES:")
    lines.append("-" * 40)
    lines.append(f"  - This is an uploaded dataset called '{dataset_name}'.")
    lines.append(f"  - The table contains {row_count:,} rows.")
    if date_range and date_range != "N/A":
        lines.append(f"  - Date range: {date_range}")

    # Add column name mapping notes
    mapping_notes = []
    for col in schema_meta:
        if col["db_name"] != col.get("original_name", "").strip().lower().replace(" ", "_"):
            mapping_notes.append(
                f"  - Column '{col['db_name']}' corresponds to original field '{col['original_name']}'"
            )

    if mapping_notes:
        lines.append("  - Column name mappings (original -> database):")
        lines.extend(mapping_notes[:10])  # Limit to 10 mappings
        if len(mapping_notes) > 10:
            lines.append(f"  - ... and {len(mapping_notes) - 10} more mappings")

    # Identify column types for hints
    date_cols = [c for c in schema_meta if c["col_type"] == "date"]
    numeric_cols = [c for c in schema_meta if c["col_type"] in ("integer", "numeric")]
    categorical_cols = [c for c in schema_meta if c["col_type"] == "categorical"]

    if date_cols:
        lines.append(f"  - Date/time columns: {', '.join(c['db_name'] for c in date_cols)}")
    if numeric_cols:
        lines.append(f"  - Numeric columns: {', '.join(c['db_name'] for c in numeric_cols)}")
    if categorical_cols:
        lines.append(f"  - Categorical columns: {', '.join(c['db_name'] for c in categorical_cols)}")

    lines.append("")
    lines.append("IMPORTANT:")
    lines.append(f"  - Only query the table '{table_name}'.")
    lines.append("  - Do NOT reference any other tables in the database.")
    lines.append("  - Use the exact column names listed above.")

    return "\n".join(lines)


def generate_dataset_context(dataset_metadata: dict) -> str:
    """
    Generate a context string for the SQL generator's system prompt
    to describe the active uploaded dataset.

    Args:
        dataset_metadata: Dict from dataset_registry.get_dataset()

    Returns:
        str: Context string
    """
    name = dataset_metadata["dataset_name"]
    row_count = dataset_metadata["row_count"]
    date_range = dataset_metadata.get("date_range")

    parts = []
    parts.append(f"ACTIVE DATASET: {name}")
    parts.append(f"Total rows: {row_count:,}")
    if date_range and date_range != "N/A":
        parts.append(f"Date range: {date_range}")
    parts.append(
        "This is a user-uploaded dataset. Do NOT apply dataset-specific rules "
        "from other datasets (e.g., date filtering, borough policies, zone joins). "
        "Generate generic analytical SQL appropriate for the schema provided."
    )

    return "\n".join(parts)


def generate_suggested_questions(dataset_metadata: dict) -> list:
    """
    Generate 4-6 suggested starter questions based on the dataset's schema.

    Args:
        dataset_metadata: Dict from dataset_registry.get_dataset()

    Returns:
        list of str: Suggested questions
    """
    schema_meta = dataset_metadata["schema_metadata"]
    questions = []

    date_cols = [c for c in schema_meta if c["col_type"] == "date"]
    numeric_cols = [c for c in schema_meta if c["col_type"] in ("integer", "numeric")]
    categorical_cols = [c for c in schema_meta if c["col_type"] == "categorical"]
    text_cols = [c for c in schema_meta if c["col_type"] == "text"]

    # 1. Total row count
    questions.append(f"How many records are in the dataset?")

    # 2. Date + numeric → trend
    if date_cols and numeric_cols:
        date_col = date_cols[0]["original_name"]
        num_col = numeric_cols[0]["original_name"]
        questions.append(f"What is the trend of {num_col} over time?")

    # 3. Categorical + numeric → group by
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]["original_name"]
        num_col = numeric_cols[0]["original_name"]
        questions.append(f"What is the average {num_col} by {cat_col}?")

    # 4. Categorical ranking
    if categorical_cols and numeric_cols and len(numeric_cols) > 0:
        cat_col = categorical_cols[0]["original_name"]
        num_col = numeric_cols[-1]["original_name"]
        questions.append(f"Which {cat_col} has the highest total {num_col}?")

    # 5. Top N
    if categorical_cols:
        cat_col = categorical_cols[0]["original_name"]
        questions.append(f"What are the top 5 most common {cat_col} values?")

    # 6. Distribution
    if numeric_cols and len(numeric_cols) >= 2:
        num_col = numeric_cols[1]["original_name"]
        questions.append(f"What is the distribution of {num_col}?")

    # Ensure we have at least 4 questions
    if len(questions) < 4:
        questions.append("Show me a summary of all columns.")

    return questions[:6]
