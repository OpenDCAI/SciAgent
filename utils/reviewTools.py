import os
import time
from typing import Any, Dict, List, Optional
from smolagents.default_tools import Tool

# Import smolagents components for LLM model and message handling
from smolagents import (LiteLLMModel)
from smolagents.models import ChatMessage, MessageRole
from .markdown_utils import MarkdownMessage, compressed_image_content


class ReviewRequestTool(Tool):
    """Expert reviewer to provide critical reviews and feedback on solution accuracy."""

    name = "ask_review_expert"
    description = ("Request expert review of your work after completing a step from the plan. "
                   "Provide your solution for that specific step and the context of the step.")
    inputs = {
        "my_solution": {
            "type":
            "string",
            "description":
            "Your detailed solution for the specific step that needs review. This must be a complete and clear account of your work for this step."
        },
        "my_note": {
            "type":
            "string",
            "description":
            "What specific aspects you are uncertain about and want the expert to focus on (e.g., 'Check my integration limits', 'Verify the final algebraic simplification')."
        },
        "step_context": {
            "type":
            "string",
            "description":
            "The context of the step you are solving, ideally copied from the plan provided by breakdown_question_expert. For example: 'Part 2, Step 3: Calculate the longitudinal number density n(t).'"
        }
    }
    output_type = "string"

    def __init__(self, worker_agent=None, review_tool_model: str = "openai/gpt-4-turbo"):  # Using a strong model for review
        super().__init__()
        self.worker_agent = worker_agent
        api_key = os.environ.get("OPENROUTER_API_KEY")
        self.review_model = LiteLLMModel(
            model_id=review_tool_model,
            api_key=api_key,
            api_base=os.environ.get("OPENROUTER_API_BASE"),
            max_completion_tokens=16000,
            num_retries=3,
            timeout=600,
        )

    def forward(self, my_solution: str, my_note: str, step_context: str) -> str:
        if not self.worker_agent or not hasattr(self.worker_agent, "markdown_content_high_res_image"):
            markdown_content = MarkdownMessage(content=[])
        else:
            markdown_content = compressed_image_content(self.worker_agent.markdown_content_high_res_image)

        system_prompt = (
            "You are an extremely meticulous and critical peer-reviewer for a physics/math competition. "
            "Assume the student's solution likely contains a subtle error. Your primary goal is to find it. "
            "Do not praise. Do not say 'the solution is correct' unless you have exhaustively verified every single detail. "
            "Check for dimensional consistency, correctness of formulas, logical leaps, and calculation errors. "
            "If you find an error, explain it clearly and provide the correct path. If the solution seems correct, challenge the student to explain a specific part in more detail to test their understanding."
        )

        review_instruction = (f"The student is working on the following step:\n"
                              f"--- STEP CONTEXT ---\n{step_context}\n\n"
                              f"Here is their proposed solution for this step:\n"
                              f"--- STUDENT'S SOLUTION ---\n{my_solution}\n\n"
                              f"The student has the following specific concerns:\n"
                              f"--- STUDENT'S NOTE ---\n{my_note}\n\n"
                              f"Please provide your critical review. The full original problem is attached for your reference.")

        combined_content: List[Dict[str, Any]] = [{"type": "text", "text": review_instruction}] + markdown_content.content

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=[{
                "type": "text",
                "text": system_prompt
            }]),
            ChatMessage(role=MessageRole.USER, content=combined_content),
        ]

        # Retry logic remains the same
        max_try = 3
        returned = None
        for _ in range(max_try):
            chat_message = self.review_model.generate(messages)
            if chat_message and chat_message.content:
                returned = chat_message.content.strip()
                if returned:
                    return returned
            time.sleep(5)

        return "The reviewer is temporarily unavailable. Please carefully re-check your own work for any potential errors before proceeding."
