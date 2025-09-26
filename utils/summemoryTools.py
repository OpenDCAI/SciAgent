import os
import time
from smolagents.default_tools import Tool
from base64 import b64decode
from copy import deepcopy

# Import smolagents components for LLM model, memory, and agent handling
from smolagents import LiteLLMModel
from smolagents.models import ChatMessage, MessageRole
from smolagents.memory import (AgentMemory)
from smolagents.agents import MultiStepAgent

# Debug flag for development and troubleshooting
DEBUGGING = False


# Extract agent's memory observation for summarization (similar to smolagents/memory.py/AgentMemory/replay)
def get_agent_memory_observation(agent: MultiStepAgent) -> str:
    """Extract the agent's complete problem-solving history from memory."""

    # Get the complete message history from the agent's memory
    newest_input_messages = agent.write_memory_to_messages().copy()
    agent_observation_and_action_str = ""
    agent_observation_and_action_str += f"You were given this task: {newest_input_messages[1]}\nHere is your previous process: <Your previous solving process>"
    # Note: model_input_message[1] should be the task
    agent_observation_and_action_str += str(newest_input_messages[2:]) + "</Your previous solving process>"
    # Note: model_input_message[0] is system prompt, [1] is first task; [2:] is model response & tool response
    return agent_observation_and_action_str


def summarize_agent_memory(summarize_model: LiteLLMModel, agent: MultiStepAgent = None) -> str:
    """Generate a comprehensive summary of the agent's work on problem parts."""
    agent_observation = get_agent_memory_observation(agent=agent)

    # System prompt for the summarization model to ensure comprehensive summary
    system_prompt = (
        "You are here to summarize your previous work on a given Olympiad problem."
        "You will be given your previous actions on your task: such task is likely composed of several different Parts (e.g. Part A, Part B, Part C, Part D), and your current goal is to cleanly grab your previous work on this provided task, including process and answer (Note: your work will be judged by both complete process and answer, so do not omit any of the process!). "
        "You probably changed your methods (or answer to each sub-problem) during the process: you have to make sure that you summarize your final answer and process to every (sub-) part of this problem that you have finished till now, not the wrong ones."
        "Make sure that you grab ALL the important information from your previous work, including the PROCESS and Final Answer to each sub-problem (that you have finished till now)."
    )

    # Combine agent observation with detailed summarization instructions
    combined_prompt = agent_observation + "\n\n" + (
        "Now, summarize your previous work on the task, including process and answer to each sub-problem (that you have finished till now). "
        "Make sure that you summarize your final answer and process to every (sub-) part of this problem that you have finished till now, not the wrong ones. "
        "You can use the following format:\n"
        "Part A.1.\n [Your final answer and process to Part A.1]\n\n"
        "Part A.2.\n [Your final answer and process to Part A.2]\n\n"
        "..."
        "Part B.1.\n [Your final answer and process to Part B.1]\n\n"
        "..."
        "Please summarize your previous work on the task, including process and answer to each sub-problem (that you have finished till now):\n"
    )

    # Debug mode: save agent observation to file for inspection
    if DEBUGGING:
        with open("sum_input_agent_observation_now.txt", "w") as f:
            f.write(agent_observation)

    # Prepare messages for summarization model
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
        ChatMessage(role=MessageRole.USER, content=combined_prompt),
    ]

    # print(messages)

    # Generate summary using the summarization model
    response = summarize_model.generate(messages)
    summary = response.content
    return summary


class SummarizeMemoryTool_vanilla(Tool):
    """Tool to summarize the agent's memory for completed problem parts."""

    name = "finalize_part_answer"

    description = (
        "When you have finished (including process, final answer, and discussion with review expert) a part (e.g., Part A, Part B, etc.) of the problem, you should call this tool to summarize your work on that part, for your reference when doing the next part."
        "This tool will summarize your previous work on the task, including process and answer to each sub-problem (that you have finished till now), and write to the answer sheet. Therefore, you should call this tool Only When you are sure that you have finished a Part of the problem."
        "This tool can see your previous work on the task, including process and answer to each sub-problem (that you have finished till now), so you don't have to explicitly parse in your process to this tool."
    )

    inputs = {}  # No inputs required - tool accesses agent memory directly

    output_type = "string"

    def __init__(self, worker_agent=None, summarize_model_id: str = "openai/gemini-2.5-pro"):
        super().__init__()
        self.worker_agent = worker_agent  # Reference to the main agent for memory access
        api_key = os.environ.get("OPENROUTER_API_KEY")
        # Initialize summarization model with higher token limit for comprehensive summaries
        self.summarize_model = LiteLLMModel(
            model_id=summarize_model_id,
            api_key=api_key,
            api_base=os.environ.get("OPENROUTER_API_BASE"),
            max_completion_tokens=16384,
            num_retries=3,
            timeout=1200,
        )
        self.is_first_use = True  # Track first use to modify task instructions

    def forward(self) -> str:  # type: ignore[override]
        """Execute memory summarization and reset agent memory for next problem part."""
        if not self.worker_agent or not hasattr(self.worker_agent, "memory"):
            return "Error: No memory available."

        memory: AgentMemory = self.worker_agent.memory

        # Retry logic for robust summarization
        max_try = 3
        for _ in range(max_try):
            summary = summarize_agent_memory(self.summarize_model, agent=self.worker_agent)

            if summary is None or summary.strip() == "":
                time.sleep(5)  # Wait before retry
            else:
                break
        if summary is None or summary.strip() == "":
            return "Error: No summary generated after multiple attempts. Please try again later."

        # Reset agent memory and prepare for next problem part
        # Create new memory step based on initial task but with updated instructions
        new_memory_step = deepcopy(memory.steps[0])
        if self.is_first_use:
            new_memory_step.task += "You have finished a portion of the problem, and you have summarized your work on that part. Now you should continue to solve the rest parts of the problem. Please refer to previous output of 'finalize_part_answer' tool for previous context, in which the system and user have provided you with your previous work.\nNote that when calling reviewer, you should parse in your previous work to-be-reviewed through 'my_solution' input, or the reviewer would not be able to see it!"
        # Clear memory and set up fresh start with context
        self.worker_agent.memory.reset()
        self.worker_agent.memory.steps = []
        self.worker_agent.memory.steps.append(new_memory_step)

        # Format the summary for agent reference
        this_tool_return_prompt = f"""Till now, in your previous work, you have finished some portion of the problem, and written to the answer sheet. For context length issues, detailed observations. This part of your answer is summarized as follows:
        
{summary}

Your next steps should be to solve the rest parts of the given problem of the user, following instructions. You may refer to this summary when you are solving the rest parts of the problem."""
        self.is_first_use = False  # Mark that tool has been used at least once
        return this_tool_return_prompt


class SummarizeMemoryTool(Tool):
    """
    A tool to finalize and record the solution for a specific part of the problem 
    after it has been successfully reviewed.
    """

    name = "finalize_part_answer"

    description = (
        "Call this tool ONLY after your solution for a specific part has been successfully reviewed by the 'ask_review_expert'. "
        "This tool records your final answer for that part and provides a summary for context in subsequent steps.")

    inputs = {
        "part_to_finalize": {
            "type":
            "string",
            "description":
            "The specific part or step you are finalizing, e.g., 'Part (1)', 'Part (2)', or a step from the breakdown plan."
        },
        "solution_for_part": {
            "type":
            "string",
            "description":
            "Your complete, final, and reviewed solution for this specific part, including the process and the result."
        }
    }

    output_type = "string"

    def __init__(self, worker_agent=None, summarize_model_id: str = "openai/gemini-2.5-pro"):
        super().__init__()
        self.worker_agent = worker_agent
        api_key = os.environ.get("OPENROUTER_API_KEY")
        self.summarize_model = LiteLLMModel(
            model_id=summarize_model_id,
            api_key=api_key,
            api_base=os.environ.get("OPENROUTER_API_BASE"),
            max_completion_tokens=4096,  # Summary doesn't need to be excessively long
            num_retries=3,
            timeout=180,
        )

    def forward(self, part_to_finalize: str, solution_for_part: str) -> str:
        """
        Summarizes the provided solution for a part and returns a confirmation message.
        This method NO LONGER MODIFIES the agent's memory.
        """
        if not self.worker_agent or not hasattr(self.worker_agent, "memory"):
            return "Error: Agent context is not available."

        # The system prompt for the summarizer is now more focused.
        system_prompt = (
            "You are a scientific rapporteur. Your task is to concisely summarize a provided solution "
            "for a specific part of a larger problem. The summary must be brief but capture the key method and final result. "
            "Do not add any commentary; just summarize.")

        # The user prompt for the summarizer is now much cleaner.
        user_prompt = (f"Please summarize the following solution for '{part_to_finalize}'.\n\n"
                       f"--- SOLUTION ---\n{solution_for_part}\n\n"
                       f"--- END SOLUTION ---\n\n"
                       f"Your concise summary:")

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=[{
                "type": "text",
                "text": system_prompt
            }]),
            ChatMessage(role=MessageRole.USER, content=[{
                "type": "text",
                "text": user_prompt
            }]),
        ]

        try:
            response = self.summarize_model.generate(messages)
            summary = response.content.strip() if response and response.content else "Summary could not be generated."
        except Exception as e:
            summary = f"An error occurred during summarization: {e}"

        # The tool now returns a clean, informative string that will become the next observation.
        return (f"Successfully finalized and recorded the solution for '{part_to_finalize}'.\n\n"
                f"Summary of the finalized part:\n{summary}\n\n"
                f"You may now proceed to the next step of the problem.")
