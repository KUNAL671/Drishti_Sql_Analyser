"""
benchmark_questions.py — 20 Benchmark Questions
==================================================
A set of natural-language questions with expected SQL behavior
and result characteristics, used for testing and demonstration.

These questions cover different query patterns:
  - Ranking (top N)
  - Aggregation (COUNT, AVG, SUM)
  - Time series (trends over time)
  - Joins (zone/borough lookups)
  - Filtering (specific conditions)
  - Distribution analysis
  - Single metrics (KPI)
"""

BENCHMARK_QUESTIONS = [
    # ---- 1. Ranking / Top-N ----
    {
        "question": "Which five pickup zones had the most taxi trips?",
        "expected_type": "ranking",
        "expected_viz": "bar",
        "expected_columns": ["zone", "trip_count"],
        "expected_rows": 5,
        "requires_join": True,
        "description": "Top 5 pickup zones by trip count — requires JOIN with taxi_zones",
    },
    {
        "question": "What are the top 10 busiest dropoff locations by number of trips?",
        "expected_type": "ranking",
        "expected_viz": "bar",
        "expected_columns": ["zone", "trip_count"],
        "expected_rows": 10,
        "requires_join": True,
        "description": "Top 10 dropoff zones — similar to Q1 but for dropoffs",
    },
    {
        "question": "Which 5 pickup-dropoff zone pairs are most common?",
        "expected_type": "ranking",
        "expected_viz": "table",
        "expected_columns": ["pickup_zone", "dropoff_zone", "trip_count"],
        "expected_rows": 5,
        "requires_join": True,
        "description": "Top 5 route pairs — requires double JOIN",
    },

    # ---- 2. Aggregation ----
    {
        "question": "What is the average fare amount by payment type?",
        "expected_type": "aggregation",
        "expected_viz": "bar",
        "expected_columns": ["payment_type", "avg_fare"],
        "expected_rows": "4-5",
        "requires_join": False,
        "description": "Average fare grouped by payment type",
    },
    {
        "question": "What is the average tip percentage by borough for pickup zones?",
        "expected_type": "aggregation",
        "expected_viz": "bar",
        "expected_columns": ["borough", "avg_tip_pct"],
        "expected_rows": "5-7",
        "requires_join": True,
        "description": "Tip percentage by borough — requires calculation and JOIN",
    },
    {
        "question": "What is the total revenue (total_amount) by borough?",
        "expected_type": "aggregation",
        "expected_viz": "bar",
        "expected_columns": ["borough", "total_revenue"],
        "expected_rows": "5-7",
        "requires_join": True,
        "description": "Revenue aggregation with JOIN",
    },

    # ---- 3. Time Series ----
    {
        "question": "How many trips were there per day in January 2026?",
        "expected_type": "time_series",
        "expected_viz": "line",
        "expected_columns": ["day", "trip_count"],
        "expected_rows": 31,
        "requires_join": False,
        "description": "Daily trip count — time series",
    },
    {
        "question": "Show the busiest hours of the day for taxi pickups",
        "expected_type": "time_series",
        "expected_viz": "bar",
        "expected_columns": ["hour", "trip_count"],
        "expected_rows": 24,
        "requires_join": False,
        "description": "Hourly distribution of pickups",
    },
    {
        "question": "What is the average fare by day of the week?",
        "expected_type": "time_series",
        "expected_viz": "bar",
        "expected_columns": ["day_of_week", "avg_fare"],
        "expected_rows": 7,
        "requires_join": False,
        "description": "Fare by weekday — EXTRACT(DOW FROM pickup_datetime)",
    },
    {
        "question": "How did the average trip distance change per week in January?",
        "expected_type": "time_series",
        "expected_viz": "line",
        "expected_columns": ["week", "avg_distance"],
        "expected_rows": "4-5",
        "requires_join": False,
        "description": "Weekly trend of average distance",
    },

    # ---- 4. Single Metric / KPI ----
    {
        "question": "How many total taxi trips were there in January 2026?",
        "expected_type": "kpi",
        "expected_viz": "kpi",
        "expected_columns": ["total_trips"],
        "expected_rows": 1,
        "requires_join": False,
        "description": "Single count — KPI display",
    },
    {
        "question": "What is the average trip distance?",
        "expected_type": "kpi",
        "expected_viz": "kpi",
        "expected_columns": ["avg_distance"],
        "expected_rows": 1,
        "requires_join": False,
        "description": "Single average — KPI display",
    },
    {
        "question": "What was the longest trip distance recorded?",
        "expected_type": "kpi",
        "expected_viz": "kpi",
        "expected_columns": ["max_distance"],
        "expected_rows": 1,
        "requires_join": False,
        "description": "Single MAX — KPI display",
    },

    # ---- 5. Distribution ----
    {
        "question": "What is the distribution of trip distances?",
        "expected_type": "distribution",
        "expected_viz": "histogram",
        "expected_columns": ["trip_distance"],
        "expected_rows": ">100",
        "requires_join": False,
        "description": "Trip distance distribution — histogram",
    },
    {
        "question": "Show the distribution of fare amounts for trips under $100",
        "expected_type": "distribution",
        "expected_viz": "histogram",
        "expected_columns": ["fare_amount"],
        "expected_rows": ">100",
        "requires_join": False,
        "description": "Filtered fare distribution",
    },

    # ---- 6. Filtering ----
    {
        "question": "What are the average fare and tip for trips to JFK Airport?",
        "expected_type": "filtered",
        "expected_viz": "kpi",
        "expected_columns": ["avg_fare", "avg_tip"],
        "expected_rows": 1,
        "requires_join": True,
        "description": "Filter by specific zone (JFK) — requires JOIN",
    },
    {
        "question": "How many trips had more than 4 passengers?",
        "expected_type": "filtered",
        "expected_viz": "kpi",
        "expected_columns": ["trip_count"],
        "expected_rows": 1,
        "requires_join": False,
        "description": "Count with WHERE filter",
    },
    {
        "question": "Which borough has the highest average tip amount?",
        "expected_type": "ranking",
        "expected_viz": "bar",
        "expected_columns": ["borough", "avg_tip"],
        "expected_rows": "5-7",
        "requires_join": True,
        "description": "Ranking by aggregated metric with JOIN",
    },

    # ---- 7. Relationship / Scatter ----
    {
        "question": "What is the relationship between trip distance and fare amount for the top 200 trips?",
        "expected_type": "relationship",
        "expected_viz": "scatter",
        "expected_columns": ["trip_distance", "fare_amount"],
        "expected_rows": 200,
        "requires_join": False,
        "description": "Scatter plot of distance vs fare",
    },

    # ---- 8. Complex ----
    {
        "question": "Show me the average fare, average tip, and trip count for each borough, sorted by trip count",
        "expected_type": "complex",
        "expected_viz": "table",
        "expected_columns": ["borough", "avg_fare", "avg_tip", "trip_count"],
        "expected_rows": "5-7",
        "requires_join": True,
        "description": "Multiple aggregations with JOIN",
    },
]
