"""read_image MCP tool — read a screenshot/image and return as base64 content block."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from ui_agent.state import set_image_path


@tool(
    "read_image",
    "Read a screenshot or image file and return it as a base64 image content block "
    "for visual analysis. Supports PNG, JPEG, GIF, and WebP. "
    "Provide 'path' to the image file.",
    {"path": str},
)
async def read_image(args: dict[str, Any]) -> dict[str, Any]:
    image_path = args.get("path", "")

    if not image_path:
        return {
            "content": [{"type": "text", "text": "Error: 'path' is required."}],
            "is_error": True,
        }

    path = Path(image_path).resolve()
    if not path.exists():
        return {
            "content": [{"type": "text", "text": f"Error: File not found: {image_path}"}],
            "is_error": True,
        }

    # Validate image with Pillow
    try:
        from PIL import Image

        img = Image.open(path)
        width, height = img.size
        img_format = img.format or "PNG"
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: Cannot open image: {e}"}],
            "is_error": True,
        }

    # Map format to media type
    media_types = {
        "PNG": "image/png",
        "JPEG": "image/jpeg",
        "JPG": "image/jpeg",
        "GIF": "image/gif",
        "WEBP": "image/webp",
    }
    media_type = media_types.get(img_format.upper(), "image/png")

    # Read and encode
    image_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")

    set_image_path(str(path))

    return {
        "content": [
            {
                "type": "text",
                "text": f"Image loaded: {path.name} ({width}x{height}, {img_format})",
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            },
        ],
    }
