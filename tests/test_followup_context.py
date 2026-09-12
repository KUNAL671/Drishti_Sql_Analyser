import pytest
from app.agent.sql_generator import generate_sql


MOCK_SALES_SCHEMA = """
Table: sales
Columns:
- transaction_id (integer)
- product_id (integer)
- product_name (text)
- category_id (integer)
- category_name (text)
- region_id (integer)
- region_name (text)
- revenue (numeric)
- profit (numeric)
"""

CONTEXT_PRODUCTS_5 = """CONVERSATION CONTEXT (previous analyses in this session):
============================================================

--- Turn 1 ---
User question: Which 5 products generated the highest revenue?
SQL used:
SELECT product_id, product_name, SUM(revenue) as total_revenue
FROM sales
GROUP BY product_id, product_name
ORDER BY total_revenue DESC
LIMIT 5
Result columns: product_id, product_name, total_revenue
Result (5 rows):
 product_id product_name  total_revenue
          1        Jeans        50000.0
          2       Shirts        45000.0
          3        Shoes        40000.0
          4         Hats        35000.0
          5        Socks        30000.0
============================================================"""

CONTEXT_REGIONS_5 = """CONVERSATION CONTEXT (previous analyses in this session):
============================================================

--- Turn 1 ---
User question: Which 5 regions generated the most revenue?
SQL used:
SELECT region_id, region_name, SUM(revenue) as total_revenue
FROM sales
GROUP BY region_id, region_name
ORDER BY total_revenue DESC
LIMIT 5
Result columns: region_id, region_name, total_revenue
Result (5 rows):
 region_id region_name  total_revenue
        10       North        50000.0
        20       South        45000.0
        30        East        40000.0
        40        West        35000.0
        50     Central        30000.0
============================================================"""

CONTEXT_PRODUCT_1 = """CONVERSATION CONTEXT (previous analyses in this session):
============================================================

--- Turn 1 ---
User question: Which product generated the highest revenue?
SQL used:
SELECT product_id, product_name, SUM(revenue) as total_revenue
FROM sales
GROUP BY product_id, product_name
ORDER BY total_revenue DESC
LIMIT 1
Result columns: product_id, product_name, total_revenue
Result (1 rows):
 product_id product_name  total_revenue
          1        Jeans        50000.0
============================================================"""

CONTEXT_CATEGORIES = """CONVERSATION CONTEXT (previous analyses in this session):
============================================================

--- Turn 1 ---
User question: Which categories generated the most revenue?
SQL used:
SELECT category_id, category_name, SUM(revenue) as total_revenue
FROM sales
GROUP BY category_id, category_name
ORDER BY total_revenue DESC
LIMIT 3
Result columns: category_id, category_name, total_revenue
Result (3 rows):
 category_id category_name  total_revenue
         100       Apparel        50000.0
         200      Footwear        45000.0
         300   Accessories        40000.0
============================================================"""


class TestFollowupContext:
    def test_test1_products_5(self):
        """TEST 1: Which 5 products generated the highest revenue? -> Which of those had the highest profit margin?"""
        result = generate_sql(
            "Which of those had the highest profit margin?",
            MOCK_SALES_SCHEMA,
            conversation_context=CONTEXT_PRODUCTS_5
        )
        assert result["success"] is True
        sql = result["sql"].lower()
        
        # Must filter by the exact 5 products using IN clause with IDs
        assert "in" in sql
        assert "1" in sql and "2" in sql and "3" in sql and "4" in sql and "5" in sql
        assert "product_id" in sql
        
        # Must calculate aggregate profit margin correctly
        assert "sum(profit)" in sql
        assert "sum(revenue)" in sql

    def test_test2_regions_5(self):
        """TEST 2: Which 5 regions generated the most revenue? -> Which of those had the highest average profit?"""
        result = generate_sql(
            "Which of those had the highest average profit?",
            MOCK_SALES_SCHEMA,
            conversation_context=CONTEXT_REGIONS_5
        )
        assert result["success"] is True
        sql = result["sql"].lower()
        
        # Must filter by the exact 5 regions using IN clause with IDs
        assert "in" in sql
        assert "10" in sql and "20" in sql and "30" in sql and "40" in sql and "50" in sql
        assert "region_id" in sql

    def test_test3_product_1(self):
        """TEST 3: Which product generated the highest revenue? -> What was its profit margin?"""
        result = generate_sql(
            "What was its profit margin?",
            MOCK_SALES_SCHEMA,
            conversation_context=CONTEXT_PRODUCT_1
        )
        assert result["success"] is True
        sql = result["sql"].lower()
        
        # Must filter by the exact 1 product using ID
        assert "product_id" in sql
        assert "= 1" in sql or "in (1)" in sql or "in ( 1 )" in sql

    def test_test4_categories(self):
        """TEST 4: Which categories generated the most revenue? -> Which of them had the highest profit margin?"""
        result = generate_sql(
            "Which of them had the highest profit margin?",
            MOCK_SALES_SCHEMA,
            conversation_context=CONTEXT_CATEGORIES
        )
        assert result["success"] is True
        sql = result["sql"].lower()
        
        # Must filter by the exact 3 categories using IDs
        assert "in" in sql
        assert "100" in sql and "200" in sql and "300" in sql
        assert "category_id" in sql

    def test_test5_independent_question(self):
        """TEST 5: Start a new independent question: Which product has the highest profit margin?"""
        result = generate_sql(
            "Which product has the highest profit margin?",
            MOCK_SALES_SCHEMA
        )
        assert result["success"] is True
        sql = result["sql"].lower()
        
        # Must NOT filter by any specific products (no IN clause for product_id 1,2,3,4,5)
        # Should be a general query
        assert "in (1" not in sql
        assert "in(1" not in sql
        assert "product_id = 1" not in sql
        
        # Must calculate aggregate profit margin correctly
        assert "sum(profit)" in sql
        assert "sum(revenue)" in sql

    def test_context_leakage(self):
        """TEST 7: Context Leakage check. Provide context but ask an independent question."""
        result = generate_sql(
            "What is the highest profit margin product?",
            MOCK_SALES_SCHEMA,
            conversation_context=CONTEXT_PRODUCTS_5
        )
        assert result["success"] is True
        sql = result["sql"].lower()
        
        # The question does not use "those" or "them", so it's an independent question.
        # However, the context is provided (as if the user just asked a new question in the same session).
        # We must make sure it doesn't arbitrarily restrict to the 5 products.
        
        # Wait, the rule says "When the user asks to analyze 'those' entities, you MUST restrict..."
        # So if the user asks a general question, it shouldn't restrict.
        assert "in (1" not in sql
        assert "in(1" not in sql
