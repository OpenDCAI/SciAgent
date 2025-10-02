import os

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)  # Load from .env file in the current directory
    print("dotenv loaded successfully from .env file")
    print(f"Currently using api key: {os.environ.get('API_KEY')[:20]}...")
except ImportError:
    # dotenv not available, continue without it
    print("dotenv not available, continuing without it")
    pass
except Exception:
    # .env file doesn't exist or other error, continue without raising exception
    print("Error loading .env file, continuing without it")
    pass

# use openrouter by default; if you want to use other API bases (e.g. openai api base, etc.), simply set API_BASE to your base
os.environ["API_BASE"] = os.environ.get("API_BASE", "https://openrouter.ai/api/v1")

import argparse

# for type hints
from typing import List
from smolagents.default_tools import Tool
from smolagents import (
    MultiStepAgent,
    LiteLLMModel,
    ToolCallingAgent,
)
from sciagent import SciCodeAgent
from smolagents.agents import ActionStep

# deal with markdown contents
from sciagent.utils import MarkdownMessage
from sciagent.utils import load_markdown_from_filepath, markdown_to_plaintext, markdown_images_compress

# Import tools usable for agents
from sciagent.tools import AskImageTool, ReviewRequestTool, SummarizeMemoryTool, BreakdownTool, SmilesTool

TOOLNAME2TOOL = {
    'ask_image_expert': AskImageTool,
    'ask_review_expert': ReviewRequestTool,
    'finalize_part_answer': SummarizeMemoryTool,
    'breakdown_question_expert': BreakdownTool,
    'smiles_verify_expert': SmilesTool,
}

def cleanup_memory_step(memory_step: ActionStep, agent: SciCodeAgent) -> None:
    for memory_step in agent.memory.steps:
        if isinstance(memory_step, ActionStep):
            if not memory_step.model_output:
                memory_step.observations = None
                memory_step.observations_images = None
                memory_step.model_output = None
                memory_step.tool_calls = None
                memory_step.error = None
            elif "breakdown_question_expert" in memory_step.model_output:
                if not memory_step.error:
                    memory_step.model_output = None
                    memory_step.tool_calls = None
                    memory_step.error = None
                else:
                    memory_step.model_output = None
            elif "smiles_verify_expert" in memory_step.model_output:
                if not memory_step.error:
                    memory_step.model_output = None
                    memory_step.error = None
                else:
                    memory_step.model_output = None
            elif "ask_image_expert" in memory_step.model_output:
                if not memory_step.error:
                    memory_step.model_output = None
                    memory_step.tool_calls = None
                    memory_step.error = None
                else:
                    memory_step.model_output = None
            elif "ask_review_expert" in memory_step.model_output:
                if not memory_step.error:
                    memory_step.model_output = None
                    memory_step.tool_calls = None
                    memory_step.error = None
                else:
                    memory_step.model_output = None
            elif "finalize_part_answer" in memory_step.model_output or "final_answer" in memory_step.model_output:
                if not memory_step.error:
                    memory_step.model_output = None
                    memory_step.tool_calls = None
                    memory_step.error = None
                else:
                    memory_step.model_output = None

def _create_Olympics_agent(Tools_list: List[type[Tool]],
                           markdown_content: MarkdownMessage,
                           model_id: str = "",
                           managed_agents_list: List[MultiStepAgent] = None,
                           max_steps: int = 80,
                           **kwargs) -> ToolCallingAgent | SciCodeAgent:  # either returns ToolCallingAgent or SciCodeAgent

    # LLM to use for the agent
    model = LiteLLMModel(
        model_id=model_id,
        api_key=os.environ.get("API_KEY"),
        api_base=os.environ.get("API_BASE"),
        max_completion_tokens=32768,
        num_retries=3,
        timeout=1200,
    )

    # tools for the manager agent
    tools = []
    for tool in Tools_list:
        if tool.__name__ == "AskImageTool" and "image_tool_model" in kwargs:
            tools.append(tool(vision_model_id=kwargs["image_tool_model"]))
        elif tool.__name__ == "ReviewRequestTool" and "review_tool_model" in kwargs:
            tools.append(tool(review_tool_model=kwargs["review_tool_model"]))
        elif tool.__name__ == "SummarizeMemoryTool" and "summarize_tool_model" in kwargs:
            tools.append(tool(summarize_model_id=kwargs["summarize_tool_model"]))
        elif tool.__name__ == "BreakdownTool" and "breakdown_tool_model" in kwargs:
            tools.append(tool(breakdown_tool_model=kwargs["breakdown_tool_model"]))
        elif tool.__name__ == "SmilesTool" and "smiles_tool_model" in kwargs:
            tools.append(tool(smiles_tool_model=kwargs["smiles_tool_model"]))
        else:
            tools.append(tool())

    # initialize the manager agent
    manager_agent_kwargs = dict(model=model,
                                tools=tools,
                                max_steps=max_steps,
                                verbosity_level=2,
                                name="olympics_agent",
                                description="",
                                step_callbacks=[cleanup_memory_step],
                                managed_agents=managed_agents_list)

    if kwargs["manager_type"] == "SciCodeAgent":
        manager_agent_kwargs["additional_authorized_imports"] = [
            "os", "sys", "time", "argparse", "pathlib", "matplotlib.pyplot", "numpy", "pandas"
        ]
        managerAgent = SciCodeAgent(**manager_agent_kwargs)
    elif kwargs["manager_type"] == "ToolCallingAgent":
        manager_agent_kwargs["max_tool_threads"] = 1
        managerAgent = ToolCallingAgent(**manager_agent_kwargs)
    else:
        raise ValueError(f"Unknown manager type: {kwargs['manager_type']}. Must be 'ToolCallingAgent' or 'SciCodeAgent'.")

    # register the tools with the agent
    for toolName in managerAgent.tools:
        managerAgent.tools[toolName].worker_agent = managerAgent

    # set high res images in the agent, for the AskImageTool to use
    managerAgent.markdown_content_high_res_image = markdown_content

    return managerAgent


def get_managed_agents_list(managed_agents_list: List[str] = None,
                            managed_agents_list_model_id: str = None) -> List[MultiStepAgent]:
    if managed_agents_list is None:
        return []

    managed_agents = []
    for agent_name in managed_agents_list:
        # LLM model
        model = LiteLLMModel(
            model_id=managed_agents_list_model_id,
            api_key=os.environ.get("API_KEY"),
            api_base=os.environ.get("API_BASE"),
            max_completion_tokens=32768,
            num_retries=3,
            timeout=1200,
        )
        # managed agent
        managed_agent = SciCodeAgent(
            tools=[],
            model=model,
            name=agent_name,
            additional_authorized_imports=["os", "sys", "time", "argparse", "pathlib", "matplotlib.pyplot", "numpy", "pandas"],
            description=f"I am a managed agent with name {agent_name}. I can assist with code-related tasks",
            max_steps=80,
            verbosity_level=2,
        )
        managed_agents.append(managed_agent)

    return managed_agents


# create the agent
def create_agent(model_id: str = "",
                 input_markdown_file: str = None,
                 tools_list: List[str] = [],
                 managed_agents_list: List[str] = None,
                 managed_agents_list_model_id: str = None,
                 **kwargs) -> ToolCallingAgent | SciCodeAgent:
    markdown_content = load_markdown_from_filepath(input_markdown_file)

    # create the manager agent
    ToolsList = [TOOLNAME2TOOL[x] for x in tools_list]
    OlympicsAgent = _create_Olympics_agent(Tools_list=ToolsList,
                                           markdown_content=markdown_content,
                                           model_id=model_id,
                                           managed_agents_list=get_managed_agents_list(managed_agents_list,
                                                                                       managed_agents_list_model_id),
                                           **kwargs)
    return OlympicsAgent


# obtain task string and images for the agent to run.
def obtain_task_and_images(
    input_markdown_file: str = None,
    tools_list: List[str] = [],
    managed_agents_list: List[str] = None,
    manager_type: str = "ToolCallingAgent",
) -> tuple[str, List[bytes]]:

    # load markdown content with high res images
    markdown_content = load_markdown_from_filepath(input_markdown_file)

    # create the manager agent
    ToolsList = [TOOLNAME2TOOL[x] for x in tools_list]

    # get task and images (to parse into agents) from the markdown content
    problem_text = markdown_to_plaintext(markdown_content)
    compressed_problem_images = markdown_images_compress(markdown_content, max_short_side_pixels=1080)

    # system prompt for the agent.
    task = "Below is the full Olympics problem. If there are Images, Images are attached; reference them using their placeholders (e.g. <image_1>, <image_2>). "

    # system prompts for agent related to tools (if there are any)
    IMG_TOOL_PROMPT = """
You have the ability to perceive and understand images directly. However, some scientific and technical images can be deceptively complex, containing dense information, subtle details, or requiring precise quantitative extraction that is prone to error.

To ensure the highest accuracy, you are equipped with a specialized tool: `ask_image_expert`. Think of this as your "magnifying glass" or "precision measurement instrument." While you can see the image, this tool can analyze it with a higher degree of fidelity.

You MUST follow this protocol for intelligent use of your vision capabilities:

**1. Initial Self-Assessment (A Mandatory Mental Checkpoint)**

Whenever a problem references an image (e.g., `<image_1>`), your first `Thought` process for that step must include a self-assessment of the image's complexity. Ask yourself these questions:

*   **Is precise quantitative data required?** (e.g., reading values from a graph, measuring lengths, reading a dial).
*   **Is the diagram dense or cluttered?** (e.g., a complex circuit diagram, a detailed biological pathway, an engineering schematic).
*   **Are the labels small, handwritten, or potentially ambiguous?**
*   **Is the relationship between components non-trivial and critical to the problem?** (e.g., understanding the 3D structure of a molecule, the exact topology of a network).

**2. The Decision to Escalate: When to Call the Expert**

*   **You MUST call `ask_image_expert` if the answer to ANY of the self-assessment questions is 'Yes'.** Relying on your general perception for these tasks is high-risk and can lead to critical errors.
*   If the image is simple and purely illustrative (e.g., a stock photo of an apple when the problem is about gravity), you may proceed without calling the expert, but you should state your reasoning (e.g., "Thought: The image of the apple is illustrative; I can proceed with the calculation directly.").

**3. How to Formulate Expert Queries**

When you decide to call the tool, do not ask trivial questions. Ask targeted, expert-level questions to get the precise information you need. Refer to these categories for inspiration:

*   **A. For Precise Data Extraction:**
    *   *Instead of guessing:* "From the graph in <image_1>, what is the precise value and unit of the peak labeled 'A'?"
    *   *Instead of estimating:* "What is the exact numerical reading on the digital multimeter in <image_2>?"

*   **B. For Deconstructing Complex Diagrams:**
    *   *Instead of a high-level glance:* "Analyze the circuit in <image_1>. List all components in the loop containing the resistor R3 and specify their connections (series/parallel)."
    *   *Instead of assuming function:* "Describe the function of the component labeled 'catalytic converter' within the system diagram of <image_2> based on its connections."

*   **C. For Verifying Your Own Reading:**
    *   *When in doubt:* "I am interpreting the label on the x-axis as 'Time (ms)'. Can you please verify this and list all other axis labels and titles in <image_1>?"

**Protocol Summary:**
**See Image -> Assess Complexity -> If Complex or Quantitative, Call Expert -> Use Expert's Precise Answer.**

This protocol ensures you leverage your native vision for efficiency on simple tasks while relying on a specialized tool for the precision and accuracy required to solve complex scientific problems correctly.
"""

    REVIEW_TOOL_PROMPT = """
To ensure the highest accuracy, you MUST use the `ask_review_expert` tool to validate your work.

1.  **Review After Every Step:** After you complete the work for each step outlined by the `breakdown_question_expert`, you MUST call `ask_review_expert` before starting the next step.

2.  **How to Call:** When calling the tool, you must provide:
    *   `my_solution`: Your complete work for that specific step.
    *   `step_context`: The description of the step you just completed, taken from the breakdown plan.
    *   `my_note`: Any specific points you are unsure about.

This review process is mandatory. Do not proceed with a multi-step problem without having each intermediate step validated.
"""

    BREAKDOWN_TOOL_PROMPT = """
You are equipped with a powerful tool: `breakdown_question_expert`. You must adhere to the following protocol:

1.  **Mandatory First Step:** For any new complex problem (like math, physics or chemistry), your can call `breakdown_question_expert`. You must provide all parameters:
    *   Provide the full problem text in the `question` parameter.
    *   Set `current_context` to "This is the first step. I need a plan to start."
    *   **Set `previous_steps` to "No previous steps taken yet."**
    Do not perform any of your own analysis before this initial call. Your turn must end immediately after calling the tool.

2.  **Follow the Plan:** The expert will return a step-by-step plan. You must follow this plan, executing one step at a time.

3.  **Re-planning When Stuck:** If you find the plan is flawed, you get stuck, or encounter an unexpected error, you MUST call `breakdown_question_expert` again to get a revised plan. When re-planning, you MUST:
    *   Provide the full original `question` again.
    *   Clearly explain why you are stuck in the `current_context` parameter.
    *   Summarize the steps you have already taken and their results in the `previous_steps` parameter.
"""

    SMILES_VERIFY_TOOL_PROMPT = "You MUST verify any provided SMILES string by calling the `smiles_verify_expert` tool at the very beginning. Always perform this verification before any chemical reasoning, visualization, or property calculation. If the verification result is `True`, proceed with downstream analysis. If the verification result is `False`, you MUST attempt to repair the SMILES. "

    if SummarizeMemoryTool in ToolsList:
        REVIEW_TOOL_PROMPT += "Before you use the `finalize_part_answer` tool, you MUST use the `ask_review_expert` tool to review your (part) answer, to ensure that your answer is correct and complete. "

    FINALIZE_PART_ANSWER_PROMPT = """
The 'finalize_part_answer' tool is used as the final action for completing a major part of the problem (e.g., Part (1), Part (2)).

You MUST follow this strict protocol:
1.  **Solve the Part:** Complete all the necessary calculations and derivations for the current part based on the breakdown plan.
2.  **Finalize:** Once the review is successful, your very next action MUST be to call `finalize_part_answer`. Provide the name of the part in `part_to_finalize` and your full, corrected solution in `solution_for_part`.

This protocol is not optional. It ensures your work is recorded correctly before you move on.
"""

    # if ReviewRequestTool in ToolsList:
    #     FINALIZE_PART_ANSWER_PROMPT += "If you can use the review tool, you MUST use `ask_review_expert` tool to review your (part) answer before calling this tool, to ensure that your answer is correct and complete. You should call this tool only when you are sure that you have finished a part of the problem, and you have used the ask-review_expert tool! Also, you should not call it when there are parts left to solve! "

    task += BREAKDOWN_TOOL_PROMPT if BreakdownTool in ToolsList else ""
    task += IMG_TOOL_PROMPT if AskImageTool in ToolsList else ""
    task += SMILES_VERIFY_TOOL_PROMPT if SmilesTool in ToolsList else ""
    task += REVIEW_TOOL_PROMPT if ReviewRequestTool in ToolsList else ""

    task += FINALIZE_PART_ANSWER_PROMPT if SummarizeMemoryTool in ToolsList else ""

    # system propmts for agent related to managed agent(s) (if there are any)
    MANAGE_AGENT_PROMPT = f"You may use the managed Code Agent: {managed_agents_list} to assist you with code-related tasks. "

    SELF_IS_CODE_AGENT_PROMPT = """
Your core capability is the Python Code Interpreter. Treat it as a tool that you invoke to perform actions.

1.  **Invocation:** You call the interpreter by writing a complete, single block of Python code. This code block represents your entire action for a turn, and your output must stop immediately after it.

2.  **Purposeful Action:** You must only invoke the interpreter for a specific, necessary purpose. Valid purposes include:
    *   **Calculation:** To compute numerical or logical results.
    *   **Data Manipulation:** To process or transform variables currently in your memory state.

3.  **Intelligent Restraint:** Crucially, you must treat code execution as a deliberate action, not a default behavior. **Do not** write code if:
    *   The information required to answer is already available in the preceding `Observation`.
    *   The task can be resolved by simply stating a fact you have already deduced.
    *   The user's request is conversational and does not require an action.

Your goal is to solve the task efficiently, using the code interpreter as a precise instrument only when needed.
"""

    task += MANAGE_AGENT_PROMPT if len(managed_agents_list) > 0 else ""
    task += SELF_IS_CODE_AGENT_PROMPT if manager_type == "SciCodeAgent" else ""

    # system prompts for agent related to the problem solving
    PROBLEM_SOLVING_PROMPT = (
        "Your task is to solve the problem part by part, step by step. "
        "ONLY after you have FISHED the WHOLE PROBLEM should you call final_answer, never call final_answer when there are parts left! Or the program will shut down immediately, and you would have NO CHANCE to continue solving!\n\n"
        "PROBLEM STATEMENT (text with image placeholders):\n" + problem_text)
    task += PROBLEM_SOLVING_PROMPT

    return task, compressed_problem_images


def parse_args():
    ap = argparse.ArgumentParser(description="Run the Science Agent with specified tools and model.")
    ap.add_argument(
        "--input-markdown-file",
        type=str,
        default="",
        help="Path to the markdown file containing the science problem.",
    )
    ap.add_argument(
        "--manager-model",
        type=str,
        default="",
        help="Model ID to use for the agent.",
    )

    # Choose between ToolCallingAgent and SciCodeAgent for the manager agent
    ap.add_argument(
        "--manager-type",
        type=str,
        default="SciCodeAgent",
        choices=["SciCodeAgent"],
        help="Type of agent to create (default: ToolCallingAgent).",
    )

    # Tools available for the manager agent.
    ap.add_argument(
        "--tools-list",
        type=str,
        nargs='*',
        default=["ask_image_expert",
            "finalize_part_answer",
            "ask_review_expert",
            "breakdown_question_expert",
            "smiles_verify_expert"],
        help="List of tool names to use in the agent.",
    )
    # LLM model ids for the tools
    ap.add_argument(
        "--image-tool-model",
        type=str,
        default="",
        help="Model ID to use for the image model.",
    )
    ap.add_argument(
        "--breakdown-tool-model",
        type=str,
        default="",
        help="Model ID to use for the image model.",
    )
    ap.add_argument(
        "--review-tool-model",
        type=str,
        default="",
        help="Model ID to use for the review model.",
    )
    ap.add_argument(
        "--smiles-tool-model",
        type=str,
        default="",
        help="Model ID to use for the review model.",
    )
    ap.add_argument(
        "--summarize-tool-model",
        type=str,
        default="",
        help="Model ID to use for the summarizer model.",
    )

    # agent names of managed agents.
    ap.add_argument(
        "--managed-agents-list",
        type=str,
        nargs='*',
        default=[],
        help="List of managed agents to use in the agent.",
    )
    # LLM model ids for the managed agents
    ap.add_argument(
        "--managed-agents-list-model",
        type=str,
        default=None,
        help="Model ID to use for the agent.",
    )

    args = ap.parse_args()

    if not args.input_markdown_file:
        raise ValueError("You must provide a markdown file position with --input-markdown-file.")
    if not os.path.exists(args.input_markdown_file):
        raise FileNotFoundError(f"Markdown file {args.input_markdown_file} does not exist.")
    return args


def main():
    args = parse_args()
    print(
        f"Running Olympics Agent with model: {args.manager_model}, tools: {args.tools_list}, markdown file: {args.input_markdown_file}"
    )

    managerAgent = create_agent(
        model_id=args.manager_model,
        input_markdown_file=args.input_markdown_file,
        tools_list=args.tools_list,
        image_tool_model=args.image_tool_model,
        review_tool_model=args.review_tool_model,
        summarize_tool_model=args.summarize_tool_model,
        breakdown_tool_model=args.breakdown_tool_model,
        managed_agents_list=args.managed_agents_list if hasattr(args, 'managed_agents_list') else None,
        managed_agents_list_model_id=args.managed_agents_list_model if hasattr(args, 'managed_agents_list_model') else None,
        manager_type=args.manager_type,
    )

    task, compressed_problem_images = obtain_task_and_images(
        input_markdown_file=args.
        input_markdown_file,  # markdown file with problem statement and images, will be loaded and parsed to tasks and images.
        tools_list=args.tools_list,  # system prompt is related to tools
        managed_agents_list=args.managed_agents_list
        if hasattr(args, 'managed_agents_list') else None,  # system prompt is related to managed agents
        manager_type=args.manager_type,  # system prompt is related to manager type (SciCodeAgent)
    )

    managerAgent.run(task, images=compressed_problem_images)


if __name__ == "__main__":
    main()
