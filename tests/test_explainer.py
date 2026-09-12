import pytest
from app.agent.explainer import EXPLAIN_SYSTEM_PROMPT

def test_explanation_prompt_grounding_rules():
    """Verify that the explainer prompt enforces strict factual grounding and prevents hallucinations."""
    
    # The prompt should contain strict rules about not inventing numbers
    assert "NEVER invent or estimate numbers" in EXPLAIN_SYSTEM_PROMPT
    
    # The prompt should explicitly ask to distinguish observation from interpretation
    assert "Distinguish observation from interpretation" in EXPLAIN_SYSTEM_PROMPT
    
    # The prompt should make the LLM aware of the limited dataset scope (now dynamic)
    assert "DATASET AWARENESS RULES" in EXPLAIN_SYSTEM_PROMPT
    assert "NEVER refer to the currently loaded rows as the \"total trips in the dataset\"" in EXPLAIN_SYSTEM_PROMPT

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
