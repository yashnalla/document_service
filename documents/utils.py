import json
from typing import Dict, Any, List


def validate_lexical_content(content: Dict[str, Any]) -> bool:
    """
    Basic validation for Lexical editor content structure.

    Args:
        content: The content to validate

    Returns:
        bool: True if content appears to be valid Lexical format
    """
    if not isinstance(content, dict):
        return False

    # Check for root structure
    if "root" not in content:
        return False

    root = content["root"]
    if not isinstance(root, dict):
        return False

    # Check for children array in root
    if "children" not in root:
        return False

    if not isinstance(root["children"], list):
        return False

    return True


def update_lexical_content_with_text(
    content: Dict[str, Any], new_text: str
) -> Dict[str, Any]:
    """
    Update Lexical content by replacing all text nodes with new text.
    This is a simplified approach that maintains basic structure but replaces content.

    Args:
        content: Original Lexical content
        new_text: New text to insert

    Returns:
        Dict: Updated Lexical content
    """
    if not validate_lexical_content(content):
        # If content is not valid Lexical format, create a basic structure
        return create_basic_lexical_content(new_text)

    # Create a deep copy of the content
    updated_content = json.loads(json.dumps(content))

    # Split new text into paragraphs
    paragraphs = new_text.split("\n") if new_text else [""]

    # Create new children nodes for each paragraph
    new_children = []
    for paragraph in paragraphs:
        if paragraph.strip():  # Skip empty paragraphs
            paragraph_node = {
                "type": "paragraph",
                "children": [
                    {
                        "type": "text",
                        "text": paragraph,
                        "format": 0,
                        "style": "",
                        "mode": "normal",
                        "detail": 0,
                    }
                ],
                "format": "",
                "indent": 0,
                "version": 1,
            }
        else:
            # Empty paragraph
            paragraph_node = {
                "type": "paragraph",
                "children": [],
                "format": "",
                "indent": 0,
                "version": 1,
            }

        new_children.append(paragraph_node)

    # If no paragraphs, create one empty paragraph
    if not new_children:
        new_children = [
            {
                "type": "paragraph",
                "children": [],
                "format": "",
                "indent": 0,
                "version": 1,
            }
        ]

    # Update the root children
    updated_content["root"]["children"] = new_children

    return updated_content


def create_basic_lexical_content(text: str = "") -> Dict[str, Any]:
    """
    Create a basic Lexical content structure with the given text.

    Args:
        text: Text to include in the content

    Returns:
        Dict: Basic Lexical content structure
    """
    paragraphs = text.split("\n") if text else [""]
    children = []

    for paragraph in paragraphs:
        if paragraph.strip():
            children.append(
                {
                    "type": "paragraph",
                    "children": [
                        {
                            "type": "text",
                            "text": paragraph,
                            "format": 0,
                            "style": "",
                            "mode": "normal",
                            "detail": 0,
                        }
                    ],
                    "format": "",
                    "indent": 0,
                    "version": 1,
                }
            )

    # If no content, create empty paragraph
    if not children:
        children = [
            {
                "type": "paragraph",
                "children": [],
                "format": "",
                "indent": 0,
                "version": 1,
            }
        ]

    return {
        "root": {
            "type": "root",
            "format": "",
            "indent": 0,
            "version": 1,
            "children": children,
        }
    }


def extract_text_from_lexical(content: Dict[str, Any]) -> str:
    """
    Extract plain text from Lexical content.
    This is a duplicate of the method in Document model for utility use.

    Args:
        content: Lexical content dictionary

    Returns:
        str: Extracted plain text
    """
    if not content or not isinstance(content, dict):
        return ""

    def extract_text_from_nodes(nodes):
        text_parts = []
        if not isinstance(nodes, list):
            return ""

        for node in nodes:
            if not isinstance(node, dict):
                continue

            if node.get("type") == "text":
                text_parts.append(node.get("text", ""))
            elif "children" in node:
                child_text = extract_text_from_nodes(node["children"])
                if child_text:
                    text_parts.append(child_text)
            elif "content" in node:
                child_text = extract_text_from_nodes(node["content"])
                if child_text:
                    text_parts.append(child_text)

        return " ".join(text_parts)

    # Handle both standard Lexical format (root.children) and alternative format (content)
    root_children = content.get("root", {}).get("children", [])
    if not root_children:
        root_children = content.get("content", [])
        
    return extract_text_from_nodes(root_children).strip()
