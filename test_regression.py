import sys
import pandas as pd
from app.agent.orchestrator import process_question
from app.agent.visualizer import select_visualization
from app.agent.sql_generator import generate_sql
from pathlib import Path
from app.agent.schema_retriever import get_schema_for_llm

SQL_DIR = Path("sql")

def run_tests():
    print("=" * 50)
    print("RUNNING REGRESSION TESTS FOR INTENT & VIZ")
    print("=" * 50)
    
    schema_text = get_schema_for_llm()
        
    tests = [
        {
            "id": 1,
            "question": "How many total taxi trips are in the database?",
            "expect_date_filter": False,
            "expect_viz": "kpi",
            "expect_result": 5000,
        },
        {
            "id": 2,
            "question": "How many taxi trips were recorded in January 2026?",
            "expect_date_filter": True,
            "expect_viz": "kpi",
            "expect_result": 4995,
        },
        {
            "id": 3,
            "question": "How many trips were recorded on January 1, 2026?",
            "expect_date_filter": True,
            "expect_viz": "kpi",
            "expect_result": None, # Skip specific result check
        },
        {
            "id": 4,
            "question": "What is the average trip distance?",
            "expect_date_filter": False,
            "expect_viz": "kpi",
            "expect_result": None,
        },
        {
            "id": 5,
            "question": "How many trips were recorded for each borough?",
            "expect_date_filter": False,
            "expect_viz": "bar",
            "expect_result": None,
        }
    ]
    
    all_passed = True
    
    for t in tests:
        print(f"\n[TEST {t['id']}] Question: {t['question']}")
        
        # Test just the SQL generation first to isolate it
        sql_res = generate_sql(t['question'], schema_text)
        sql = sql_res['sql']
        
        # Print SQL inline, replacing newlines for compactness
        print(f"SQL: {sql.strip().replace(chr(10), ' ')}")
        
        has_date_filter = "2026-01-01" in sql or "2026-02-01" in sql or "pickup_datetime >=" in sql.upper() or "PICKUP_DATETIME >=" in sql.upper() or "WHERE pickup_datetime" in sql.lower() or "WHERE DATE(" in sql.upper()
        if t['expect_date_filter'] and not has_date_filter:
            print("❌ Date filter intent: FAILED (Expected date filter, got none)")
            all_passed = False
        elif not t['expect_date_filter'] and has_date_filter:
            print("❌ Date filter intent: FAILED (Expected NO date filter, but found one)")
            all_passed = False
        else:
            print("✅ Date filter intent: PASS")
            
        print("Running full pipeline to test visualizer...")
        res = process_question(t['question'])
        
        if not res["success"]:
            print(f"❌ Pipeline failed: {res.get('error')}")
            all_passed = False
            continue
            
        viz_meta = res.get("viz_meta", {})
        chart_type = viz_meta.get("chart_type", "table")
        print(f"Chart Type Selected: {chart_type}")
        
        if chart_type != t['expect_viz']:
            print(f"❌ Visualization: FAILED (Expected {t['expect_viz']}, got {chart_type})")
            all_passed = False
        else:
            print(f"✅ Visualization: PASS ({t['expect_viz'].upper()})")
            
        if t['expect_result'] is not None:
            val = res['data'].iloc[0, 0]
            if val != t['expect_result']:
                print(f"❌ Result check: FAILED (Expected {t['expect_result']}, got {val})")
                all_passed = False
            else:
                print(f"✅ Result check: PASS")
                
        # Optional: Print explanation to verify it's working
        print(f"Explanation Preview: {res['explanation'][:100]}...")

    if all_passed:
        print("\n🏆 ALL TESTS PASSED! The regression is fixed.")
        sys.exit(0)
    else:
        print("\n💀 SOME TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
