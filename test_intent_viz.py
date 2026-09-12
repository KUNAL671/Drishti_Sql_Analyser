import sys
import os

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.agent.orchestrator import process_question
from app.agent.sql_generator import generate_sql
from app.agent.visualizer import select_visualization
import pandas as pd
from app.config import SQL_DIR

with open(SQL_DIR / "schema.sql", "r", encoding="utf-8") as f:
    schema_text = f.read()

tests = [
    {
        "name": "TEST 1",
        "question": "How many total taxi trips are in the database?",
        "expected_kpi": True,
        "expected_date_filter": False
    },
    {
        "name": "TEST 2",
        "question": "How many taxi trips were recorded in January 2026?",
        "expected_kpi": True,
        "expected_date_filter": True
    },
    {
        "name": "TEST 3",
        "question": "What is the average trip distance?",
        "expected_kpi": True,
        "expected_date_filter": False
    },
    {
        "name": "TEST 4",
        "question": "How many trips were recorded for each borough?",
        "expected_bar": True
    },
    {
        "name": "TEST 5",
        "question": "Show total trips per day in January 2026.",
        "expected_line": True
    }
]

def run_tests():
    print("="*50)
    print("RUNNING INTENT & VIZ TESTS")
    print("="*50)
    
    for t in tests:
        print(f"\n[{t['name']}] Question: {t['question']}")
        
        # Test SQL Generation Intent
        sql_res = generate_sql(t['question'], schema_text)
        sql = sql_res['sql']
        print(f"SQL: {sql.strip().replace(chr(10), ' ')}")
        
        has_date_filter = "2026-01-01" in sql or "2026-02-01" in sql
        if 'expected_date_filter' in t:
            if has_date_filter == t['expected_date_filter']:
                print("✅ Date filter intent: PASS")
            else:
                print(f"❌ Date filter intent: FAIL (expected {t['expected_date_filter']}, got {has_date_filter})")
        
        # Test Visualization Selection using Orchestrator which executes the query
        print("Running full pipeline to test visualizer...")
        res = process_question(t['question'])
        
        if not res['success']:
            print(f"❌ Pipeline failed: {res.get('error', 'Unknown error')}")
            continue
            
        viz_meta = res.get('viz_meta', {})
        chart_type = viz_meta.get('chart_type')
        print(f"Chart Type Selected: {chart_type}")
        
        if t.get('expected_kpi') and chart_type == 'kpi':
            print("✅ Visualization: PASS (KPI)")
        elif t.get('expected_bar') and chart_type == 'bar':
            print("✅ Visualization: PASS (Bar)")
        elif t.get('expected_line') and chart_type == 'line':
            print("✅ Visualization: PASS (Line)")
        else:
            print(f"❌ Visualization: FAIL (Got {chart_type})")
            print(f"Data shape was: {res.get('data').shape}")
            print(f"Columns: {res.get('data').columns.tolist()}")
            
        # Print Explanation to check dataset status
        print(f"Explanation Preview: {res.get('explanation', '')[:150]}...")

if __name__ == "__main__":
    run_tests()
