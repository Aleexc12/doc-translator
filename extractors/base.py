"""Base abstract class for PDF extractors."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class TextBlock:
    """Represents a text block extracted from PDF."""
    text: str
    bbox: List[float]  # [x0, y0, x1, y1]
    block_type: str  # 'text', 'title', 'header', 'footer', 'caption', etc.
    page_num: int
    font_size: Optional[float] = None
    font_weight: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FormulaBlock:
    """Represents a formula/equation extracted from PDF."""
    content: str  # LaTeX or MathML
    bbox: List[float]
    page_num: int
    format_type: str  # 'latex', 'mathml', etc.


@dataclass
class ExtractionResult:
    """Result of PDF extraction."""
    text_blocks: List[TextBlock]
    formula_blocks: List[FormulaBlock]
    total_pages: int
    metadata: Dict[str, Any]


class BaseExtractor(ABC):
    """Abstract base class for PDF extractors."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize extractor with optional configuration.

        Args:
            config: Extractor-specific configuration dictionary
        """
        self.config = config or {}

    @abstractmethod
    def extract(self, pdf_path: Path) -> ExtractionResult:
        """
        Extract structured content from PDF.

        Args:
            pdf_path: Path to input PDF file

        Returns:
            ExtractionResult containing all extracted content

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ExtractionError: If extraction fails
        """
        pass

    @abstractmethod
    def supports_ocr(self) -> bool:
        """Return whether this extractor supports OCR."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this extractor."""
        pass

    def validate_pdf(self, pdf_path: Path) -> bool:
        """
        Validate that the PDF file exists and is readable.

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if valid, False otherwise
        """
        if not pdf_path.exists():
            return False
        if not pdf_path.is_file():
            return False
        if not pdf_path.suffix.lower() == '.pdf':
            return False
        return True
