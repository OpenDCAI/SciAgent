import ast
import json
import re
from textwrap import dedent
from typing import Any

from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

from sciagent.scimonitoring import SciMonitor

from smolagents import (
    CodeAgent,
    ActionOutput
)

from smolagents.memory import (
    ActionStep,
    ToolCall
)

from smolagents.models import (
    CODEAGENT_RESPONSE_FORMAT,
    ChatMessage,
    ChatMessageStreamDelta,
    agglomerate_stream_deltas
)

from smolagents.utils import (
    AgentExecutionError,
    AgentGenerationError,
    AgentParsingError,
    truncate_content
)

from smolagents.monitoring import (
    LogLevel, )

from smolagents.local_python_executor import fix_final_answer_code


def extract_first_code_block(text: str, code_block_tags: tuple[str, str]) -> str | None:
    """
    Extracts ONLY the first valid code block from the LLM's output.
    It tries the primary tags first, then falls back to a common markdown pattern.
    """
    # Strategy 1: Try the primary tags (e.g., <code>...</code>)
    primary_pattern = rf"{code_block_tags[0]}(.*?){code_block_tags[1]}"
    match = re.search(primary_pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Strategy 2: Fallback to markdown pattern (e.g., ```python...```)
    markdown_pattern = r"```(?:python|py)\n(.*?)\n```"
    match = re.search(markdown_pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


def parse_first_code_block(text: str, code_block_tags: tuple[str, str]) -> str:
    """
    Parses and returns ONLY the first code block found in the text.
    Includes fallback for naked code and provides helpful error messages.
    """
    code = extract_first_code_block(text, code_block_tags)

    if code:
        return code

    # Fallback Strategy: Check if the whole text is valid code
    try:
        ast.parse(text)
        return text.strip()
    except SyntaxError:
        pass  # If it's not valid code, we'll proceed to the error messages.

    # Error Handling: Provide specific, helpful error messages
    if "final" in text and "answer" in text:
        raise ValueError(
            dedent(f"""
                Your output is invalid. I could not find a valid code block starting with '{code_block_tags[0]}' or '```python'.
                It seems you are trying to return a final answer. Please format it correctly inside a code block, for example:
                {code_block_tags}
                final_answer("YOUR FINAL ANSWER HERE")
                {code_block_tags}
                """).strip())
    raise ValueError(
        dedent(f"""
            Your output is invalid. I could not find a valid code block starting with '{code_block_tags}' or '```python'.
            Every turn must contain exactly one code block.
            Correct format:
            Thought: Your thoughts...
            {code_block_tags[0]}
            # Your single action python code here
            {code_block_tags[1]}
            """).strip())

class SciCodeAgent(CodeAgent):
    """
    A custom CodeAgent that modifies the streaming step process.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = SciMonitor(self.model, self.logger)
        self._setup_step_callbacks(None)

    def _step_stream(self, memory_step: ActionStep):
        """
        Executes one step in the ReAct framework. This version is robustly designed to:
        1. Force the LLM to stop after a single code block.
        2. Handle both the official `<code>` and the common Markdown ` ``` ` formats.
        """
        memory_messages = self.write_memory_to_messages()
        input_messages = memory_messages.copy()
        memory_step.model_input_messages = input_messages

        stop_sequences = [self.code_block_tags[1], "```", "Observation:", "Calling tools:"]

        try:
            additional_args: dict[str, Any] = {}
            if self._use_structured_outputs_internally:
                additional_args["response_format"] = CODEAGENT_RESPONSE_FORMAT
            if self.stream_outputs:
                output_stream = self.model.generate_stream(
                    input_messages,
                    stop_sequences=stop_sequences,
                    **additional_args,
                )
                chat_message_stream_deltas: list[ChatMessageStreamDelta] = []
                with Live("", console=self.logger.console, vertical_overflow="visible") as live:
                    for event in output_stream:
                        chat_message_stream_deltas.append(event)
                        live.update(Markdown(agglomerate_stream_deltas(chat_message_stream_deltas).render_as_markdown()))
                        yield event
                chat_message = agglomerate_stream_deltas(chat_message_stream_deltas)
                memory_step.model_output_message = chat_message
                output_text = chat_message.content
            else:
                chat_message: ChatMessage = self.model.generate(
                    input_messages,
                    stop_sequences=stop_sequences,
                    **additional_args,
                )
                memory_step.model_output_message = chat_message
                output_text = chat_message.content
                self.logger.log_markdown(
                    content=output_text,
                    title="Output message of the LLM:",
                    level=LogLevel.DEBUG,
                )

            if not self._use_structured_outputs_internally:
                # This adds the end code sequence (i.e. the closing code block tag) to the history.
                # This will nudge subsequent LLM calls to finish with this end code sequence, thus efficiently stopping generation.
                if output_text and not output_text.strip().endswith(self.code_block_tags[1]):
                    output_text += self.code_block_tags[1]
                    memory_step.model_output_message.content = output_text

            memory_step.token_usage = chat_message.token_usage
            memory_step.model_output = output_text
        except Exception as e:
            raise AgentGenerationError(f"Error in generating model output:\n{e}", self.logger) from e

        # --- Stage 2: Parse the Action (Extract Code) ---
        try:
            if self._use_structured_outputs_internally:
                code_action_json = json.loads(output_text)
                code_action = parse_first_code_block(code_action_json["code"], self.code_block_tags)
            else:
                code_action = parse_first_code_block(output_text, self.code_block_tags)

            # `parse_code_blobs` raises its own clear ValueError if no code is found, so we don't need a `code_action is None` check.
            code_action = fix_final_answer_code(code_action)
            memory_step.code_action = code_action
        except ValueError as e:  # `parse_code_blobs` raises ValueError
            raise AgentParsingError(f"Error parsing code from model output: {e}", self.logger) from e
        except Exception as e:
            raise AgentParsingError(f"An unexpected error occurred during parsing: {e}", self.logger) from e

        # --- Stage 3: Execute the Action and Observe ---

        tool_call = ToolCall(
            name="python_interpreter",
            arguments=code_action,
            id=f"call_{len(self.memory.steps)}",
        )
        yield tool_call
        memory_step.tool_calls = [tool_call]

        self.logger.log_code(title="Executing parsed code:", content=code_action, level=LogLevel.INFO)
        try:
            code_output = self.python_executor(code_action)
            execution_outputs_console = []
            if len(code_output.logs) > 0:
                execution_outputs_console += [
                    Text("Execution logs:", style="bold"),
                    Text(code_output.logs),
                ]
            observation = "Execution logs:\n" + code_output.logs
        except Exception as e:
            if hasattr(self.python_executor, "state") and "_print_outputs" in self.python_executor.state:
                execution_logs = str(self.python_executor.state["_print_outputs"])
                if len(execution_logs) > 0:
                    execution_outputs_console = [
                        Text("Execution logs:", style="bold"),
                        Text(execution_logs),
                    ]
                    memory_step.observations = "Execution logs:\n" + execution_logs
                    self.logger.log(Group(*execution_outputs_console), level=LogLevel.INFO)
            error_msg = str(e)
            if "Import of " in error_msg and " is not allowed" in error_msg:
                self.logger.log(
                    "[bold red]Warning to user: Code execution failed due to an unauthorized import - Consider passing said import under `additional_authorized_imports` when initializing your CodeAgent.",
                    level=LogLevel.INFO,
                )
            raise AgentExecutionError(error_msg, self.logger)

        truncated_output = truncate_content(str(code_output.output))
        observation += "Last output from code snippet:\n" + truncated_output
        memory_step.observations = observation

        if not code_output.is_final_answer:
            execution_outputs_console += [
                Text(f"Out: {truncated_output}", ),
            ]
        self.logger.log(Group(*execution_outputs_console), level=LogLevel.INFO)
        memory_step.action_output = code_output.output
        yield ActionOutput(output=code_output.output, is_final_answer=code_output.is_final_answer)
