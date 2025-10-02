import os
import time
from typing import Any, Dict, List
from smolagents.default_tools import Tool
from smolagents import LiteLLMModel
from smolagents.models import ChatMessage, MessageRole
from utils.markdown_utils import MarkdownMessage, compressed_image_content


class BreakdownTool(Tool):
    """
    A tool to consult an expert for breaking down a complex math or physics problem 
    into a logical, step-by-step plan.
    """

    name = "breakdown_question_expert"
    description = ("Consults an expert to break down a complex math or physics problem into a sequence of solvable steps. "
                   "Use this at the beginning of a problem or when you are stuck and need a new plan.")
    inputs = {
        "question": {
            "type": "string",
            "description": "The full, original problem statement."
        },
        "current_context": {
            "type":
            "string",
            "description": ("A brief description of the current situation. For example: "
                            "'This is the first step, I need a plan to start.' or "
                            "'I am stuck on calculating the atomic flux, the previous plan was not detailed enough.' "
                            "or 'The previous steps led to a contradiction, I need to re-evaluate my approach.'")
        },
        "previous_steps": {
            "type":
            "string",
            # CHANGE 1: 'optional' flag removed.
            # CHANGE 2: Description updated with instruction for the first call.
            "description":
            "A summary of the steps already taken and their outcomes. If this is the first call, provide the string 'No previous steps taken yet.'."
        },
    }
    output_type = "string"

    def __init__(self, worker_agent=None, breakdown_tool_model: str = "openai/gemini-2.5-pro"):
        super().__init__()
        self.worker_agent = worker_agent
        api_key = os.environ.get("API_KEY")
        self.break_model = LiteLLMModel(
            model_id=breakdown_tool_model,
            api_key=api_key,
            api_base=os.environ.get("API_BASE", "https://openrouter.ai/api/v1"),
            max_completion_tokens=16000,
            num_retries=3,
            timeout=600,
        )

    # CHANGE 3: `forward` signature updated. `Optional` and `= None` removed from `previous_steps`.
    def forward(self, question: str, current_context: str, previous_steps: str) -> str:
        if not self.worker_agent or not hasattr(self.worker_agent, "markdown_content_high_res_image"):
            markdown_content = MarkdownMessage(content=[])
        else:
            markdown_content = compressed_image_content(self.worker_agent.markdown_content_high_res_image)

        system_prompt = (
            "You are a world-class Physics and Mathematics Olympiad coach. Your task is to break down a complex problem "
            "into a clear, logical, and principled sequence of steps that a student agent can follow. "
            "Focus on the underlying principles and the logical flow, not just the calculation. "
            "For each step, provide a clear 'goal' and a brief 'rationale'. "
            "If the user is re-planning, analyze their previous steps and context to provide a revised, better plan.")

        user_prompt = f"Original Problem:\n---\n{question}\n---\n"
        user_prompt += f"Current Context:\n---\n{current_context}\n---\n"

        # CHANGE 4: Logic updated to handle the mandatory parameter.
        if previous_steps and previous_steps != "No previous steps taken yet.":
            user_prompt += f"Summary of Previous Steps and Outcomes:\n---\n{previous_steps}\n---\n"

        user_prompt += ("Please provide the new step-by-step plan. "
                        "The plan should guide me to the final answer. "
                        "Here is a breakdown of the problem into sequential steps:")

        combined_content: List[Dict[str, Any]] = [{"type": "text", "text": user_prompt}] + markdown_content.content

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=[{
                "type": "text",
                "text": system_prompt
            }]),
            ChatMessage(role=MessageRole.USER, content=combined_content),
        ]

        # ... (rest of the function remains the same)
        max_try = 3
        returned = None
        for _ in range(max_try):
            chat_message = self.break_model.generate(messages)
            if chat_message and chat_message.content:
                returned = chat_message.content.strip()
                if returned:
                    return returned
            time.sleep(5)

        return ("The breakdown expert is temporarily unavailable. Please attempt to break down the question yourself, "
                "focusing on one small, logical step at a time.")
