# Import all custom tools available for the physics agent
from .markdown_utils import MarkdownMessage, load_markdown_from_filepath, markdown_to_plaintext, markdown_images_compress  # Markdown processing utilities
from .imgTools import AskImageTool  # Image analysis tool for physics diagrams
from .reviewTools import ReviewRequestTool  # Expert review tool for solution validation
from .summemoryTools import SummarizeMemoryTool  # Memory summarization tool for long problems
from .breakdownTools import BreakdownTool
from .ragTools import RagTool
from .smilesTools import SmilesTool  # SMILES verification tool
# Dependency check: make sure tenacity is installed, as LiteLLMModel uses it for retrying logic
try:
    import tenacity
except Exception as e:
    raise ImportError("LiteLLMModel requires the 'tenacity' package for retrying logic. "
                      "Please install it with 'pip install tenacity'.") from e
