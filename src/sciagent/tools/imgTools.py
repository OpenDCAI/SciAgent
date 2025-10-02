import os
import time
from smolagents.default_tools import Tool
from base64 import b64decode

# Import smolagents components for LLM model and message handling
from smolagents import LiteLLMModel
from smolagents.models import ChatMessage, MessageRole
from sciagent.utils.markdown_utils import MarkdownMessage


class AskImageTool(Tool):
    """Image expert to answer a question about a specific figure. You MUST call this tool when you need to measure quantities from an image."""

    name = "ask_image_expert"
    description = (
        "Given an image reference (placeholder like <image_10>) and a question, "
        "return the image expert's answer about that image."
        "When you need to measure quantities from an image, you MUST call this tool for Accurate Measurements: measuring youself alone is not accurate enough and could lead to errors!"
    )
    inputs = {
        "image_ref": {
            "type": "string",
            "description": "Placeholder identifying the image (e.g. <image_N>)"
        },
        "question": {
            "type": "string",
            "description": "Question to ask about the image"
        },
    }
    output_type = "string"

    def __init__(self, worker_agent=None, vision_model_id: str = "openai/gemini-2.5-pro", max_short_side_pixels: int = 9999):
        super().__init__()
        self.worker_agent = worker_agent  # Reference to the main agent for accessing markdown content
        api_key = os.environ.get("API_KEY")
        # Initialize vision model for image analysis
        self.vision_model = LiteLLMModel(
            model_id=vision_model_id,
            api_key=api_key,
            api_base=os.environ.get("API_BASE", "https://openrouter.ai/api/v1"),
            max_completion_tokens=8192,
            num_retries=3,
            timeout=1200,
        )
        self.max_short_side_pixels = max_short_side_pixels  # Maximum image resolution for processing

    def _extract_image_bytes(self, image_ref: str) -> bytes | None:
        """Extract image bytes from markdown content using image reference like <image_1>."""
        if not self.worker_agent or not hasattr(self.worker_agent, "markdown_content_high_res_image"):
            return None
        md: MarkdownMessage = self.worker_agent.markdown_content_high_res_image
        # Parse image reference to extract index (supports both <image_N> and plain numbers)
        idx = None
        if image_ref.startswith("<image_") and image_ref.endswith(">"):
            try:
                idx = int(image_ref.strip("<image_>")) - 1  # Convert to 0-based index
            except ValueError:
                pass
        else:
            try:
                idx = int(image_ref) - 1  # Handle plain number references
            except ValueError:
                pass
        if idx is None:
            return None
        # Extract all image blocks from markdown content
        img_blocks = [it for it in md.content if it.get("type") == "image_url"]
        if 0 <= idx < len(img_blocks):
            data_url = img_blocks[idx]["image_url"]["url"]
            if data_url.startswith("data:image"):
                base64_part = data_url.split(",", 1)[1]  # Remove data URL prefix
                return b64decode(base64_part)  # Decode base64 to bytes
        return None

    def forward(self, image_ref: str, question: str) -> str:  # type: ignore[override]
        """Process image analysis request and return expert response."""
        img_bytes = self._extract_image_bytes(image_ref)
        # Resize image if it exceeds maximum resolution for better processing
        if self.max_short_side_pixels is not None:
            from PIL import Image
            from io import BytesIO

            if img_bytes is None:
                return f"Error: Could not find image {image_ref}; the parsed in image_ref should be like <image_N>."

            # Check image size and resize if necessary
            img = Image.open(BytesIO(img_bytes))
            width, height = img.size
            if min(width, height) > self.max_short_side_pixels:
                scale = self.max_short_side_pixels / min(width, height)
                new_size = (int(width * scale), int(height * scale))
                # Use BILINEAR resampling (ANTIALIAS deprecated in newer PIL versions)
                img = img.resize(new_size, Image.Resampling.BILINEAR)
        if img_bytes is None:
            return f"Error: Could not find image {image_ref}; the parsed in image_ref should be like <image_N>."

        # Convert bytes to PIL.Image for vision model processing
        from PIL import Image
        import io
        pil_img = Image.open(io.BytesIO(img_bytes))

        # Prepare messages for vision model with system prompt and user query
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content="You are an expert in dealing with image in Olympiads Problems."),
            ChatMessage(role=MessageRole.USER,
                        content=[
                            {
                                "type": "image",
                                "image": pil_img
                            },
                            {
                                "type": "text",
                                "text": question
                            },
                        ]),
        ]

        # print(messages)

        # Retry logic for robust image analysis
        max_try = 3
        for _ in range(max_try):
            # Generate response from vision model
            try:
                resp = self.vision_model.generate(messages)
                if resp.content and resp.content.strip():
                    return resp.content.strip()
            except Exception as e:
                print(f"Error during vision model generation: {str(e)}")
                time.sleep(5)  # Wait before retry
        return resp.content or "No response"
