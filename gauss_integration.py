"""
gauss_integration.py – Connect GAUSS statistical models to Unknown Verdict for legal compliance.

This module reads a GAUSS model specification, sends it to Unknown Verdict's EU AI Act
compliance endpoint, and returns a structured assessment report.
"""

import json
import logging
import httpx
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GaussModelDescription:
    """A simplified representation of a GAUSS model."""
    name: str
    description: str
    algorithm_type: str      # e.g., "linear_regression", "neural_network", "decision_tree"
    features: List[str]
    target_variable: str
    data_source: str
    intended_use: str
    potential_risks: Optional[List[str]] = None


class UnknownVerdictClient:
    """Client for Unknown Verdict API."""
    
    def __init__(self, base_url: str = "https://upamnyu12-lex.hf.space"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=120.0)  # Allow time for LLM processing
    
    def close(self):
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def assess_eu_ai_act(self, model_description: GaussModelDescription) -> Dict[str, Any]:
        """
        Send a GAUSS model description to Unknown Verdict's EU AI Act compliance endpoint.
        
        Args:
            model_description: A structured description of the GAUSS model.
        
        Returns:
            A compliance assessment dictionary.
        """
        # Build the prompt for Unknown Verdict
        prompt = (
            f"Perform an EU AI Act conformity assessment for the following AI model:\n"
            f"Name: {model_description.name}\n"
            f"Description: {model_description.description}\n"
            f"Algorithm type: {model_description.algorithm_type}\n"
            f"Features: {', '.join(model_description.features)}\n"
            f"Target variable: {model_description.target_variable}\n"
            f"Data source: {model_description.data_source}\n"
            f"Intended use: {model_description.intended_use}\n"
            f"Potential risks: {', '.join(model_description.potential_risks or ['Not specified'])}\n\n"
            "Provide a complete conformity assessment covering:\n"
            "- Risk classification (unacceptable/high/limited/minimal)\n"
            "- Legal requirements (data governance, transparency, human oversight, etc.)\n"
            "- Technical robustness and accuracy\n"
            "- Ethical alignment (bias, fairness, explainability)\n"
            "- Recommendations for compliance"
        )
        
        # Call Unknown Verdict's /chat or /compliance/eu-ai-act endpoint
        # Using /compliance/eu-ai-act (which we added earlier)
        response = self.client.post(
            f"{self.base_url}/compliance/eu-ai-act",
            json={"message": prompt},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        return result
    
    def assess_model_card(self, model_description: GaussModelDescription) -> Dict[str, Any]:
        """
        Generate a comprehensive model card (similar to capAI's external scorecard).
        """
        prompt = (
            f"Generate a detailed model card / external scorecard for the following GAUSS model:\n"
            f"Name: {model_description.name}\n"
            f"Description: {model_description.description}\n"
            f"Algorithm: {model_description.algorithm_type}\n"
            f"Intended use: {model_description.intended_use}\n\n"
            "Include sections: Purpose, Data, Governance, Bias and Fairness, Performance, Limitations, and Recommendations."
        )
        response = self.client.post(
            f"{self.base_url}/chat",
            json={"message": prompt}
        )
        response.raise_for_status()
        return response.json()


# Convenience function
def assess_gauss_model(model_spec_path: str, api_base: str = "https://upamnyu12-lex.hf.space") -> Dict[str, Any]:
    """
    Load a GAUSS model specification from a JSON file and assess it.
    
    Args:
        model_spec_path: Path to a JSON file containing the model description.
        api_base: Base URL of Unknown Verdict.
    
    Returns:
        The assessment result.
    """
    with open(model_spec_path, 'r') as f:
        spec = json.load(f)
    
    # Convert to GaussModelDescription
    model_desc = GaussModelDescription(
        name=spec.get('name', 'Unnamed Model'),
        description=spec.get('description', ''),
        algorithm_type=spec.get('algorithm_type', 'unknown'),
        features=spec.get('features', []),
        target_variable=spec.get('target_variable', 'unknown'),
        data_source=spec.get('data_source', 'unknown'),
        intended_use=spec.get('intended_use', ''),
        potential_risks=spec.get('potential_risks', [])
    )
    
    with UnknownVerdictClient(api_base) as client:
        # First, get EU AI Act compliance
        compliance = client.assess_eu_ai_act(model_desc)
        # Also get a model card
        model_card = client.assess_model_card(model_desc)
    
    return {
        "model_name": model_desc.name,
        "eu_ai_act_compliance": compliance,
        "model_card": model_card
    }


if __name__ == "__main__":
    # Quick test: use a sample model spec
    import sys
    if len(sys.argv) > 1:
        result = assess_gauss_model(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python gauss_integration.py <model_spec.json>")  