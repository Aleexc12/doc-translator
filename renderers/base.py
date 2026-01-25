"""Base abstract class for PDF renderers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List
from extractors.base import TextBlock, FormulaBlock


class BaseRenderer(ABC):
    """Abstract base class for PDF renderers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize renderer with optional configuration.

        Args:
            config: Renderer-specific configuration
        """
        self.config = config or {}

    @abstractmethod
    def render(
        self,
        input_pdf: Path,
        output_pdf: Path,
        text_blocks: List[TextBlock],
        formula_blocks: List[FormulaBlock],
        translated_texts: Dict[str, str]  # maps original text -> translated text
    ) -> Path:
        """
        Render translated content back into PDF.

        Args:
            input_pdf: Path to original PDF
            output_pdf: Path for output PDF
            text_blocks: List of extracted text blocks
            formula_blocks: List of extracted formula blocks
            translated_texts: Mapping of original text to translated text

        Returns:
            Path to generated output PDF

        Raises:
            RenderError: If rendering fails
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this renderer."""
        pass

    @abstractmethod
    def preserves_original_text(self) -> bool:
        """
        Return whether this renderer preserves original text in PDF structure.

        Returns:
            False if original text is removed/replaced (recommended)
            True if original text remains (overlay approach, not recommended)
        """
        pass

    def validate_inputs(
        self,
        input_pdf: Path,
        text_blocks: List[TextBlock],
        translated_texts: Dict[str, str]
    ) -> bool:
        """
        Validate inputs before rendering.

        Args:
            input_pdf: Input PDF path
            text_blocks: Text blocks to render
            translated_texts: Translation mapping

        Returns:
            True if valid, False otherwise
        """
        if not input_pdf.exists():
            return False
        if not text_blocks:
            return False
        if not translated_texts:
            return False
        return True
