import os
import time
from typing import Any, Dict, List, Optional
from smolagents.default_tools import Tool

from rdkit import Chem
from smolagents import LiteLLMModel
from smolagents.models import ChatMessage, MessageRole


class SmilesTool(Tool):
    """Tool to verify a SMILES expression using RDKit."""

    name = "smiles_verify_expert"
    description = ("Verify whether a given SMILES chemical expression is valid. "
                   "If valid, return 'True'. If invalid, return 'False'.")
    inputs = {
        "smiles": {
            "type": "string",
            "description": "The SMILES chemical expression to verify."
        },
    }
    output_type = "string"  # return "True"/"False"

    def __init__(self, worker_agent=None, smiles_tool_model: str = "openai/gemini-2.5-pro"):
        super().__init__()
        self.worker_agent = worker_agent

    def forward(self, smiles: str) -> str:  # type: ignore[override]
        """
        Verify SMILES using RDKit. Return 'True' if valid, otherwise 'False'.
        """
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                return "True"
            else:
                return "False"
        except Exception as e:
            return f"Error verifying SMILES: {str(e)}"
