"""Overlay-based PDF renderer."""

import logging
from pathlib import Path
from typing import List, Dict

import pymupdf as fitz

from renderers.base import BaseRenderer
from extractors.base import TextBlock, FormulaBlock
from utils.styling import StyleConfig

logger = logging.getLogger(__name__)


class OverlayRenderer(BaseRenderer):
    """
    Renderer that overlays translated text on top of original PDF.

    Note: This approach preserves the original text in the PDF structure.
    Re-extracting may yield both original and translated text.
    """

    def __init__(
        self,
        padding: float = 0.5,
        background_color: str = "white",
        text_color: tuple = (0, 0, 0),
        style_config: StyleConfig = None,
        config: dict = None,
    ):
        """
        Initialize overlay renderer.

        Args:
            padding: Padding around bounding boxes
            background_color: Background color for overlay rectangles
            text_color: RGB tuple for text color (0-1 range)
            style_config: StyleConfig for block-type styling
            config: Additional configuration
        """
        super().__init__(config)
        self.padding = padding
        self.background_color = background_color
        self.text_color = text_color
        self.style_config = style_config or StyleConfig()
        logger.info("Overlay renderer initialized")

    def render(
        self,
        input_pdf: Path,
        output_pdf: Path,
        text_blocks: List[TextBlock],
        formula_blocks: List[FormulaBlock],
        translated_texts: Dict[str, str],
    ) -> Path:
        """
        Render translated content as overlay on original PDF.

        Args:
            input_pdf: Path to original PDF
            output_pdf: Path for output PDF
            text_blocks: List of extracted text blocks
            formula_blocks: List of extracted formula blocks
            translated_texts: Mapping of original text to translated text

        Returns:
            Path to generated output PDF
        """
        if not self.validate_inputs(input_pdf, text_blocks, translated_texts):
            raise ValueError("Invalid inputs for rendering")

        logger.info(f"Rendering translated PDF from {input_pdf}...")

        # Open PDF
        doc = fitz.open(str(input_pdf))

        # Group blocks by page
        blocks_by_page = {}
        for block in text_blocks:
            page_num = block.page_num
            if page_num not in blocks_by_page:
                blocks_by_page[page_num] = []
            blocks_by_page[page_num].append(block)

        # Process each page
        total_rendered = 0
        for page_num, blocks in blocks_by_page.items():
            if page_num >= len(doc):
                logger.warning(f"Page {page_num} out of range, skipping")
                continue

            page = doc[page_num]

            for block in blocks:
                original_text = block.text
                translated_text = translated_texts.get(original_text)

                if not translated_text:
                    continue

                # Get bbox with padding
                bbox = self._expand_bbox(block.bbox, self.padding)
                rect = fitz.Rect(bbox)

                # Cover original text with white rectangle
                page.draw_rect(
                    rect, color=None, fill=fitz.utils.getColor(self.background_color)
                )

                # Get CSS style for block type
                css = self.style_config.get_css_style(
                    block.block_type,
                    color=f"rgb({int(self.text_color[0]*255)}, "
                    f"{int(self.text_color[1]*255)}, "
                    f"{int(self.text_color[2]*255)})",
                )

                # Insert translated text
                try:
                    page.insert_htmlbox(rect, translated_text, css=css)
                    total_rendered += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to render block on page {page_num}: {e}"
                    )

        # Save output
        logger.info(f"Saving translated PDF to {output_pdf}...")
        doc.save(str(output_pdf), garbage=4, deflate=True, clean=True)
        doc.close()

        logger.info(f"✓ Rendered {total_rendered} blocks to {output_pdf}")

        return output_pdf

    def get_name(self) -> str:
        """Return the name of this renderer."""
        return "Overlay"

    def preserves_original_text(self) -> bool:
        """
        Return whether this renderer preserves original text.

        Returns:
            True (overlay method preserves original text in PDF structure)
        """
        return True

    def _expand_bbox(self, bbox: List[float], padding: float) -> List[float]:
        """
        Expand bounding box by padding amount.

        Args:
            bbox: [x0, y0, x1, y1] coordinates
            padding: Amount to expand

        Returns:
            Expanded bbox
        """
        return [
            bbox[0] - padding,
            bbox[1] - padding,
            bbox[2] + padding,
            bbox[3] + padding,
        ]
