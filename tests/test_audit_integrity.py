import pytest
from unittest.mock import patch
from app.agent.orchestrator import process_question

@pytest.fixture
def mock_dataset_registry():
    taxi_schema = [
        {"name": "pickup_location_id", "type": "SMALLINT"},
        {"name": "fare_amount", "type": "NUMERIC"}
    ]
    sales_schema = [
        {"name": "order_id", "type": "VARCHAR"},
        {"name": "revenue", "type": "NUMERIC"}
    ]
    
    def get_dataset(dataset_id):
        if dataset_id == "taxi-data":
            return {"dataset_id": "taxi-data", "schema_metadata": taxi_schema}
        elif dataset_id == "sales-data":
            return {"dataset_id": "sales-data", "schema_metadata": sales_schema}
        return None

    def generate_dataset_context(meta):
        return f"Dataset context for {meta['dataset_id']}"

    with patch('app.agent.orchestrator.get_schema_for_llm', return_value="mock_schema"), \
         patch('app.data.dataset_registry.get_dataset', side_effect=get_dataset), \
         patch('app.data.schema_generator.generate_dataset_context', side_effect=generate_dataset_context):
        yield


@pytest.fixture
def mock_agent_pipeline():
    with patch('app.agent.orchestrator.generate_sql') as mock_gen, \
         patch('app.agent.orchestrator.validate_sql') as mock_val, \
         patch('app.agent.orchestrator.execute_query') as mock_exec, \
         patch('app.agent.orchestrator.validate_result') as mock_res_val, \
         patch('app.agent.orchestrator.select_visualization') as mock_viz, \
         patch('app.agent.orchestrator.create_chart') as mock_chart, \
         patch('app.agent.orchestrator.generate_explanation', return_value="Explanation"):
        
        mock_val.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_exec.return_value = {"success": True, "data": type('mock_df', (), {'empty': False, '__len__': lambda s: 5, 'columns': ['col1']})(), "error": None}
        mock_res_val.return_value = {"valid": True, "errors": [], "warnings": [], "status": "SUCCESS"}
        mock_viz.return_value = {}
        mock_chart.return_value = None
        
        yield {
            "gen": mock_gen,
            "val": mock_val,
            "exec": mock_exec,
            "res_val": mock_res_val
        }


def test_taxi_dataset_schema_integrity(mock_dataset_registry, mock_agent_pipeline):
    """TEST 1: Taxi dataset query returns taxi schema fields in the audit."""
    mock_agent_pipeline["gen"].return_value = {
        "success": True, "sql": "SELECT * FROM taxi", "explanation": "Taxi query"
    }
    
    result = process_question("Which 5 pickup zones had the most trips?", dataset_id="taxi-data")
    
    assert result["success"] is True
    # The target_schema should contain taxi fields ONLY
    assert len(result["target_schema"]) == 2
    schema_names = [col["name"] for col in result["target_schema"]]
    assert "pickup_location_id" in schema_names
    assert "fare_amount" in schema_names
    assert "revenue" not in schema_names


def test_sales_dataset_schema_integrity(mock_dataset_registry, mock_agent_pipeline):
    """TEST 2: Sales dataset query returns sales schema fields in the audit."""
    mock_agent_pipeline["gen"].return_value = {
        "success": True, "sql": "SELECT * FROM sales", "explanation": "Sales query"
    }
    
    result = process_question("What was the total revenue?", dataset_id="sales-data")
    
    assert result["success"] is True
    assert len(result["target_schema"]) == 2
    schema_names = [col["name"] for col in result["target_schema"]]
    assert "order_id" in schema_names
    assert "revenue" in schema_names
    assert "pickup_location_id" not in schema_names


def test_dataset_switch_no_contamination(mock_dataset_registry, mock_agent_pipeline):
    """TEST 3: Verify no cross-contamination when switching between datasets."""
    # Run taxi
    mock_agent_pipeline["gen"].return_value = {
        "success": True, "sql": "SELECT * FROM taxi", "explanation": "Taxi query"
    }
    taxi_res = process_question("taxi question", dataset_id="taxi-data")
    
    # Run sales
    mock_agent_pipeline["gen"].return_value = {
        "success": True, "sql": "SELECT * FROM sales", "explanation": "Sales query"
    }
    sales_res = process_question("sales question", dataset_id="sales-data")
    
    taxi_schema = [col["name"] for col in taxi_res["target_schema"]]
    sales_schema = [col["name"] for col in sales_res["target_schema"]]
    
    assert "pickup_location_id" in taxi_schema
    assert "revenue" not in taxi_schema
    assert "revenue" in sales_schema
    assert "pickup_location_id" not in sales_schema


def test_failed_validation_audit_log(mock_dataset_registry, mock_agent_pipeline):
    """TEST 4: Failed validation generates audit log showing attempt 1 failed and retries."""
    
    # Make it fail the first time, then succeed
    def mock_val_side_effect(sql):
        if sql == "BAD SQL":
            return {"valid": False, "errors": ["Syntax Error"], "warnings": []}
        return {"valid": True, "errors": [], "warnings": []}
        
    mock_agent_pipeline["val"].side_effect = mock_val_side_effect
    
    # Make gen return bad SQL on attempt 1, good SQL on attempt 2
    mock_agent_pipeline["gen"].side_effect = [
        {"success": True, "sql": "BAD SQL", "explanation": "Bad query"},
        {"success": True, "sql": "GOOD SQL", "explanation": "Good query"}
    ]
    
    result = process_question("Test failure", dataset_id="taxi-data")
    
    assert result["success"] is True
    assert result["attempts"] == 2
    
    # Check retry history audit log
    history = result["retry_history"]
    assert len(history) == 2
    
    assert history[0]["attempt"] == 1
    assert history[0]["stage"] == "SQL Validation Failed"
    assert "Syntax Error" in history[0]["error"]
    
    assert history[1]["attempt"] == 2
    assert history[1]["stage"] == "Success"
