# rag_tool.py
import os
import json
import time
from typing import Any, Dict
from smolagents.default_tools import Tool

from .rag_system import CPAssistant


class RagTool(Tool):
    """Tool to query Competitive Programming RAG System (algorithms, templates, theory, C++ implementations)."""

    name = "rag_expert"
    description = ("Retrieve and answer algorithm or competitive programming related questions "
                   "using a RAG system (documents + C++ templates + explanations).")
    inputs = {
        "question": {
            "type": "string",
            "description": "The programming/algorithm problem or question."
        },
    }
    output_type = "string"

    def __init__(self, rag_tool_model: str):
        print(rag_tool_model)
        super().__init__()
        self.assistant = CPAssistant()
        try:
            self.assistant.initialize(rag_tool_model)
        except Exception as e:
            print(f"❌ Failed to initialize RAG system: {e}")
            self.assistant = None

    def forward(self, question: str) -> str:  # type: ignore[override]
        if not self.assistant:
            return "Error: RAG system not available."

        try:
            result = self.assistant.ask(question)
            if result and "result" in result:
                return result["result"]
            else:
                return "Error: No result from RAG system."
        except Exception as e:
            return f"Error querying RAG system: {e}"


if __name__ == "__main__":
    tool = RagTool()
    test_question = "Explain Disjoint Set Union (DSU) and its optimizations."
    print(f"\n🔎 Test Query: {test_question}")
    response = tool.forward(test_question)
    print("\n💡 Response:\n", response)
