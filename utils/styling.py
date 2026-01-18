"""Document styling and formatting utilities."""

from typing import Tuple, Dict, Any


class StyleConfig:
    """Configuration for text styling based on block type."""

    # Default style settings
    DEFAULT_STYLES = {
        "text": {"font_weight": "normal", "font_size": 9.0, "font_style": "normal"},
        "title": {"font_weight": "bold", "font_size": 14.0, "font_style": "normal"},
        "header": {"font_weight": "bold", "font_size": 11.0, "font_style": "normal"},
        "abstract": {"font_weight": "normal", "font_size": 9.0, "font_style": "italic"},
        "caption": {"font_weight": "normal", "font_size": 9.0, "font_style": "italic"},
        "image_caption": {"font_weight": "normal", "font_size": 8.5, "font_style": "italic"},
        "table_caption": {"font_weight": "normal", "font_size": 8.5, "font_style": "italic"},
        "footer": {"font_weight": "normal", "font_size": 8.0, "font_style": "normal"},
        "page_footnote": {"font_weight": "normal", "font_size": 8.0, "font_style": "normal"},
        "equation": {"font_weight": "normal", "font_size": 9.0, "font_style": "normal"},
    }

    def __init__(self, custom_styles: Dict[str, Dict[str, Any]] = None):
        """
        Initialize style configuration.

        Args:
            custom_styles: Optional custom style overrides
        """
        self.styles = self.DEFAULT_STYLES.copy()
        if custom_styles:
            self.styles.update(custom_styles)

    def get_style(self, block_type: str) -> Dict[str, Any]:
        """
        Get style configuration for block type.

        Args:
            block_type: Type of block (e.g., 'title', 'text', 'caption')

        Returns:
            Dictionary with font_weight, font_size, font_style
        """
        block_type = (block_type or "text").lower()
        return self.styles.get(block_type, self.styles["text"])

    def get_font_weight(self, block_type: str) -> str:
        """Get font weight for block type."""
        return self.get_style(block_type)["font_weight"]

    def get_font_size(self, block_type: str) -> float:
        """Get font size for block type."""
        return self.get_style(block_type)["font_size"]

    def get_font_style(self, block_type: str) -> str:
        """Get font style (normal, italic, oblique) for block type."""
        return self.get_style(block_type)["font_style"]

    def get_css_style(self, block_type: str, color: str = "rgb(0,0,0)") -> str:
        """
        Generate CSS style string for block type.

        Args:
            block_type: Type of block
            color: CSS color string

        Returns:
            CSS style string
        """
        style = self.get_style(block_type)
        font_style_attr = "font-style" if style["font_style"] != "normal" else ""

        css = (
            f"* {{"
            f"font-family: sans-serif; "
            f"font-size: {style['font_size']}pt; "
            f"font-weight: {style['font_weight']}; "
        )

        if style["font_style"] != "normal":
            css += f"font-style: {style['font_style']}; "

        css += f"color: {color};"
        css += "}"

        return css

    def set_style(self, block_type: str, **kwargs):
        """
        Set custom style for block type.

        Args:
            block_type: Type of block
            **kwargs: Style properties (font_weight, font_size, font_style)
        """
        if block_type not in self.styles:
            self.styles[block_type] = self.styles["text"].copy()

        for key, value in kwargs.items():
            if key in ["font_weight", "font_size", "font_style"]:
                self.styles[block_type][key] = value


def should_translate_block_type(block_type: str) -> bool:
    """
    Determine if a block type should be translated.

    Args:
        block_type: Type of block

    Returns:
        True if block should be translated
    """
    block_type = (block_type or "").lower()

    # Skip non-textual content
    skip_types = {
        "image",
        "table",
        "equation",
        "figure",
        "interline_equation",
        "chart",
        "diagram"
    }

    return block_type not in skip_types


def is_caption_type(block_type: str) -> bool:
    """
    Check if block type is a caption.

    Args:
        block_type: Type of block

    Returns:
        True if block is a caption type
    """
    block_type = (block_type or "").lower()
    return "caption" in block_type or block_type in {"figure_caption", "table_caption", "image_caption"}


def is_footnote_type(block_type: str) -> bool:
    """
    Check if block type is a footnote.

    Args:
        block_type: Type of block

    Returns:
        True if block is a footnote type
    """
    block_type = (block_type or "").lower()
    return "footnote" in block_type or block_type in {"footer", "page_footnote"}


def normalize_block_type(block_type: str) -> str:
    """
    Normalize block type string to standard format.

    Args:
        block_type: Raw block type string

    Returns:
        Normalized block type
    """
    if not block_type:
        return "text"

    block_type = block_type.lower().strip()

    # Normalize common variations
    type_map = {
        "heading": "header",
        "h1": "title",
        "h2": "header",
        "h3": "header",
        "paragraph": "text",
        "body": "text",
        "fig_caption": "image_caption",
        "tbl_caption": "table_caption",
    }

    return type_map.get(block_type, block_type)
