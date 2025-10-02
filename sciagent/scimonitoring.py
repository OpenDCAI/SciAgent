from smolagents.monitoring import Monitor
from rich.text import Text

class SciMonitor(Monitor):
    def update_metrics(self, step_log):
        """Update the metrics of the monitor.

        Args:
            step_log ([`MemoryStep`]): Step log to update the monitor with.
        """
        step_duration = step_log.timing.duration
        self.step_durations.append(step_duration)
        console_outputs = f"| Step {len(self.step_durations)}: Duration {step_duration:.2f} seconds |\n"

        if step_log.token_usage is not None:
            self.total_input_token_count += step_log.token_usage.input_tokens
            self.total_output_token_count += step_log.token_usage.output_tokens
            console_outputs += (
                f"| Input Step tokens: {step_log.token_usage.input_tokens:,} | Output Step tokens: {step_log.token_usage.output_tokens:,} |\n| Input Total tokens: {self.total_input_token_count:,} | Output Total tokens: {self.total_output_token_count:,} |"
            )
        self.logger.log(Text(console_outputs, style="dim"), level=1)