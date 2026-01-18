"""PyMuPDF-based PDF extractor."""

import logging
from pathlib import Path
from typing import List, Optional

import pymupdf

from .base import BaseExtractor, TextBlock, FormulaBlock, ExtractionResult

logger = logging.getLogger(__name__)


class PyMuPDFExtractor(BaseExtractor):
    """Fast extractor using PyMuPDF for text-based PDFs."""

    def __init__(self, mode: str = "line", config: Optional[dict] = None):
        """
        Initialize PyMuPDF extractor.

        Args:
            mode: Extraction mode - 'line' or 'paragraph'
            config: Additional configuration
        """
        super().__init__(config)
        self.mode = mode
        logger.info(f"PyMuPDF extractor initialized (mode: {mode})")

    def extract(self, pdf_path: Path) -> ExtractionResult:
        """
        Extract structured content from PDF using PyMuPDF.

        Args:
            pdf_path: Path to input PDF file

        Returns:
            ExtractionResult containing extracted content
        """
        if not self.validate_pdf(pdf_path):
            raise FileNotFoundError(f"Invalid PDF file: {pdf_path}")

        logger.info(f"Extracting text from {pdf_path} using PyMuPDF...")

        pdf_doc = pymupdf.open(str(pdf_path))
        text_blocks = []
        formula_blocks = []
        total_pages = len(pdf_doc)

        for page_no in range(total_pages):
            page = pdf_doc[page_no]
            lines = self._extract_lines_from_page(page)

            for line in lines:
                text_block = TextBlock(
                    text=line["text"],
                    bbox=[line["x0"], line["y0"], line["x1"], line["y1"]],
                    block_type="text",
                    page_num=page_no,
                    font_size=None,
                    font_weight=None,
                    metadata=None,
                )
                text_blocks.append(text_block)

        pdf_doc.close()

        logger.info(
            f"Extracted {len(text_blocks)} text blocks from {total_pages} pages"
        )

        return ExtractionResult(
            text_blocks=text_blocks,
            formula_blocks=formula_blocks,
            total_pages=total_pages,
            metadata={"extractor": "pymupdf", "mode": self.mode},
        )

    def _extract_lines_from_page(self, page) -> List[dict]:
        """
        Extract text lines from a page using PyMuPDF.

        Args:
            page: PyMuPDF page object

        Returns:
            List of lines with bbox and text
        """
        lines = []
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                spans = line.get("spans", [])
                if not spans:
                    continue

                # Combine text from all spans in the line
                line_text = "".join(span["text"] for span in spans).strip()
                if not line_text:
                    continue

                # Get line bbox
                bbox = line["bbox"]
                lines.append(
                    {"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3], "text": line_text}
                )

        return lines

    def supports_ocr(self) -> bool:
        """Return whether this extractor supports OCR."""
        return False

    def get_name(self) -> str:
        """Return the name of this extractor."""
        return f"PyMuPDF ({self.mode})"
