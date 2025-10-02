import re
import base64
from pathlib import Path

from typing import Any, Dict, List

from base64 import b64decode

class MarkdownMessage:
    """Custom data type to hold OpenAI-compatible message content with embedded images."""
    def __init__(self, content: List[Dict[str, Any]], filename: str = ""):
        self.content = content
        self.filename = filename
        
    def __str__(self):
        """Return a manager-friendly summary (small, no base64)."""
        texts = [item["text"] for item in self.content if item.get("type") == "text"]
        images = [item["image_url"].get("url", "") for item in self.content if item.get("type") == "image_url"]
        # Build short preview of text (first 400 chars)
        preview = " ".join(texts)[:400].replace("\n", " ") + ("…" if sum(len(t) for t in texts) > 400 else "")
        image_list = [f"<image_{idx+1}>" for idx in range(len(images))]
        return (
            f"MarkdownMessage '{self.filename}' | text_preview: '{preview}' | "
            f"images: {', '.join(image_list)} (total {len(images)})"
        )
        
def compressed_image_content(markdownMessage: MarkdownMessage, max_short_side_pixels: int = 1080) -> MarkdownMessage:
    """Return a new MarkdownMessage with images compressed to max_short_side_pixels."""
    from PIL import Image
    import io
    
    new_content = []
    for item in markdownMessage.content:
        if item.get("type") == "image_url":
            url = item["image_url"].get("url", "")
            if url.startswith("data:image"):
                try:
                    base64_part = url.split(",", 1)[1]
                    img_bytes = b64decode(base64_part)
                    img = Image.open(io.BytesIO(img_bytes))
                    
                    short_side_pixels = min(img.size)
                    if short_side_pixels >= max_short_side_pixels:
                        scale = max_short_side_pixels / short_side_pixels
                        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
                        img = img.resize(new_size, Image.LANCZOS)
                    
                    # Encode back to base64
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    
                    new_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"}
                    })
                except Exception as e:
                    new_content.append({
                        "type": "text",
                        "text": f"[Error loading image: {str(e)}]"
                    })
        else:
            new_content.append(item)
    
    return MarkdownMessage(new_content, markdownMessage.filename)
        
        
        
        
def obtain_newContent_and_images_from_markdown(content: str, image_base_dir: str):
    """
    Parse markdown content and extract images, similar to direct_ask.py
    Returns content with image placeholders and a dict of image paths.
    """
    IMG_FILE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
    image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    images = {}
    new_content = content
    
    image_counter = 0
    for match in image_pattern.finditer(content):
        image_path = match.group(2)  # Get the path part
        if any(image_path.lower().endswith(ext) for ext in IMG_FILE_EXTENSIONS):
            image_counter += 1
            
            # Resolve relative paths
            if not Path(image_path).is_absolute():
                full_image_path = Path(image_base_dir) / image_path
            else:
                full_image_path = Path(image_path)
                
            if full_image_path.exists():
                current_key = f"<image_{image_counter}>"
                images[current_key] = str(full_image_path)
                new_content = new_content.replace(match.group(0), current_key)
            else:
                # Replace with error message
                new_content = new_content.replace(match.group(0), f"[Image not found: {image_path}]")
    
    return new_content, images
        


def encode_image_to_base64(path: str) -> str:
    """Encode image file to base64 string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
        
        
        
        
        
        


def create_openai_message_content(text: str, image_paths: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Create OpenAI-compatible message content from text with image placeholders.
    Based on the logic from direct_ask.py
    """
    content = []
    
    def append_content(item):
        if content and item["type"] == "text" and content[-1]["type"] == "text":
            content[-1]["text"] += item["text"]
        else:
            content.append(item)
    
    if image_paths:
        pattern = re.compile("|".join(map(re.escape, image_paths.keys())))
        pos = 0
        
        for match in pattern.finditer(text):
            start, end = match.span()
            placeholder = match.group()
            
            # Add text before the image placeholder
            if start > pos:
                append_content({"type": "text", "text": text[pos:start]})
            
            # Add placeholder text so language model sees token
            append_content({"type": "text", "text": f" {placeholder} "})
            # Add the image
            img_path = image_paths[placeholder]
            try:
                # Determine MIME type
                ext = Path(img_path).suffix.lower()
                mime_type = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg', 
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp'
                }.get(ext, 'image/jpeg')
                
                encoded = encode_image_to_base64(img_path)
                append_content({
                    "type": "image_url", 
                    "image_url": {"url": f"data:{mime_type};base64,{encoded}"}
                })
            except Exception as e:
                append_content({
                    "type": "text", 
                    "text": f"[Error loading image {img_path}: {str(e)}]"
                })
            
            pos = end
        
        # Add remaining text
        if pos < len(text):
            append_content({"type": "text", "text": text[pos:]})
    else:
        append_content({"type": "text", "text": text})
    
    return content
        
        
        
def load_markdown_from_filepath(file_path: str) -> MarkdownMessage:
        """Parse markdown file and return OpenAI-compatible message content."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
                
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
            
            # Use the same logic as direct_ask.py
            image_base_dir = str(file_path.parent)
            new_content, images = obtain_newContent_and_images_from_markdown(
                markdown_text, image_base_dir
            )
            
            # Create OpenAI-compatible message content
            message_content = create_openai_message_content(new_content, images)
            
            return MarkdownMessage(message_content, str(file_path))
            
        except Exception as e:
            # Return error as MarkdownMessage
            return MarkdownMessage([{
                "type": "text",
                "text": f"Error parsing markdown file: {str(e)}"
            }], str(file_path))
            

def markdown_to_plaintext(markdown_content: MarkdownMessage) -> str:
    """Extract plain text from MarkdownMessage for LLM context (keep image placeholders)."""
    parts: list[str] = []
    for item in markdown_content.content:
        if item.get("type") == "text":
            parts.append(item["text"])
        # image_url blocks are ignored: placeholder already in preceding text
    return "\n".join(parts)
    
def markdown_images_compress(markdown_content: MarkdownMessage, max_short_side_pixels: int = 1000):
    """Extract and compress images from MarkdownMessage, returning list of PIL Images."""
    from PIL import Image
    import io
    images: list[Image.Image] = []  # List to store processed images
    for item in markdown_content.content:
        if item.get("type") == "image_url":
            url = item["image_url"].get("url", "")
            if url.startswith("data:image"):
                try:
                    # Decode base64 image data
                    base64_part = url.split(",", 1)[1]
                    img_bytes = b64decode(base64_part)
                    img = Image.open(io.BytesIO(img_bytes))
                    
                    # Compress image if it exceeds maximum dimensions
                    short_side_pixels = min(img.size)
                    if short_side_pixels < max_short_side_pixels:
                        img = img  # No compression needed
                    else:
                        scale = max_short_side_pixels / short_side_pixels
                        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
                        img = img.resize(new_size, Image.LANCZOS)
                    # Add processed image to list
                    
                    
                    images.append(img)
                except Exception:
                    pass  # Skip images that can't be processed
    return images