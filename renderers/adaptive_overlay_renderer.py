"""Adaptive overlay PDF renderer with style recovery."""

import os
import platform
import logging
import math
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pymupdf as fitz

from extractors.base import FormulaBlock, TextBlock
from renderers.base import BaseRenderer
from utils.styling import StyleConfig

logger = logging.getLogger(__name__)


class AdaptiveOverlayRenderer(BaseRenderer):
    """
    Safer overlay renderer:
    - extractor-agnostic page mapping (0-based / 1-based)
    - bbox sanitization + clamping
    - style recovery from original PDF spans
    """

    def __init__(
        self,
        padding: float = 0.5,
        background_color: Optional[str] = "white",
        text_color: Tuple[float, float, float] = (0, 0, 0),
        style_config: Optional[StyleConfig] = None,
        min_font_size: float = 6.5,
        font_shrink_step: float = 0.5,
        max_font_shrink_attempts: int = 8,
        config: Optional[dict] = None,
    ):
        super().__init__(config)
        self.padding = padding
        self.background_color = background_color
        self.text_color = text_color
        self.style_config = style_config or StyleConfig()
        self.min_font_size = min_font_size
        self.font_shrink_step = font_shrink_step
        self.max_font_shrink_attempts = max_font_shrink_attempts
        self.unicode_font_candidates = self._build_unicode_font_candidates(config)

        self._page_spans_cache: Dict[int, List[dict]] = {}
        logger.info("Adaptive overlay renderer initialized")

    def render(
        self,
        input_pdf: Path,
        output_pdf: Path,
        text_blocks: List[TextBlock],
        formula_blocks: List[FormulaBlock],
        translated_texts: Dict[str, str],
    ) -> Path:
        if not self.validate_inputs(input_pdf, text_blocks, translated_texts):
            raise ValueError("Invalid inputs for rendering")

        logger.info(f"Rendering translated PDF from {input_pdf}...")

        document = fitz.open(str(input_pdf))
        rendered_count = 0

        blocks_by_page: Dict[int, List[TextBlock]] = {}
        for text_block in text_blocks:
            blocks_by_page.setdefault(text_block.page_num, []).append(text_block)

        for raw_page_num, page_blocks in blocks_by_page.items():
            resolved_page_index = self._resolve_page_index(raw_page_num, len(document))
            if resolved_page_index is None:
                logger.warning(f"Page {raw_page_num} out of range, skipping")
                continue

            page = document[resolved_page_index]
            page_spans = self._extract_page_spans(page, resolved_page_index)

            for text_block in page_blocks:
                source_text = text_block.text
                translated_text = translated_texts.get(source_text)

                if not translated_text:
                    continue

                target_rect = self._safe_rect(text_block.bbox, page.rect, self.padding)
                if target_rect is None:
                    continue

                matched_spans = self._match_spans_for_rect(target_rect, page_spans)
                style = self._build_style(text_block.block_type, matched_spans)

                if self.background_color:
                    page.draw_rect(
                        target_rect,
                        color=None,
                        fill=fitz.utils.getColor(self.background_color),
                    )

                inserted = self._insert_text_with_fallback(
                    page=page,
                    rect=target_rect,
                    text=translated_text,
                    style=style,
                )
                if inserted:
                    rendered_count += 1
                else:
                    logger.warning(
                        f"Failed to place translated text on page {resolved_page_index}"
                    )

        logger.info(f"Saving translated PDF to {output_pdf}...")
        document.save(str(output_pdf), garbage=4, deflate=True, clean=True)
        document.close()

        logger.info(f"✓ Rendered {rendered_count} blocks to {output_pdf}")
        return output_pdf

    def get_name(self) -> str:
        return "AdaptiveOverlay"

    def preserves_original_text(self) -> bool:
        return True

    def _build_unicode_font_candidates(self, config: Optional[dict]) -> List[Path]:
        env_font = os.getenv("PDF_TRANSLATOR_FONT_PATH")
        if env_font:
            candidates.append(Path(env_font).expanduser())

        if config:
            configured_font = config.get("font_path")
            if configured_font:
                candidates.append(Path(configured_font).expanduser())

        candidates: List[Path] = []

        system_name = platform.system()

        if system_name == "Windows":
            windows_font_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
            candidates.extend(
                [
                    windows_font_dir / "arial.ttf",
                    windows_font_dir / "segoeui.ttf",
                    windows_font_dir / "calibri.ttf",
                    windows_font_dir / "tahoma.ttf",
                ]
            )

        if system_name == "Darwin":
            candidates.extend(
                [
                    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
                    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
                    Path("/System/Library/Fonts/Supplemental/Helvetica.ttc"),
                    Path("/Library/Fonts/Arial Unicode.ttf"),
                    Path("/Library/Fonts/Arial.ttf"),
                ]
            )

        if system_name == "Linux":
            candidates.extend(
                [
                    Path("/usr/share/fonts/noto/NotoSans-Regular.ttf"),
                    Path("/usr/share/fonts/noto/NotoSerif-Regular.ttf"),
                    Path("/usr/share/fonts/TTF/NotoSans-Regular.ttf"),
                    Path("/usr/share/fonts/TTF/NotoSerif-Regular.ttf"),
                    Path("/usr/share/fonts/TTF/IBMPlexSans-Regular.ttf"),
                    Path("/usr/share/fonts/TTF/IBMPlexSerif-Regular.ttf"),
                ]
            )

        unique_candidates: List[Path] = []
        seen = set()

        for path in candidates:
            key = str(path)
            if key not in seen:
                seen.add(key)
                unique_candidates.append(path)

        return unique_candidates

    def _get_unicode_fontfile(self) -> Optional[str]:
        for font_path in self.unicode_font_candidates:
            if font_path.exists() and font_path.is_file():
                return str(font_path)
        return None

    def _resolve_page_index(self, page_num: int, page_count: int) -> Optional[int]:
        if 0 <= page_num < page_count:
            return page_num
        if 1 <= page_num <= page_count:
            return page_num - 1
        return None

    def _safe_rect(
        self,
        bbox: List[float],
        page_rect: fitz.Rect,
        padding: float,
    ) -> Optional[fitz.Rect]:
        if not bbox or len(bbox) != 4:
            return None

        try:
            x0, y0, x1, y1 = (float(value) for value in bbox)
        except (TypeError, ValueError, OverflowError):
            return None

        if not all(math.isfinite(value) for value in (x0, y0, x1, y1)):
            return None

        x0, x1 = sorted((x0 - padding, x1 + padding))
        y0, y1 = sorted((y0 - padding, y1 + padding))

        x0 = max(page_rect.x0, min(x0, page_rect.x1))
        x1 = max(page_rect.x0, min(x1, page_rect.x1))
        y0 = max(page_rect.y0, min(y0, page_rect.y1))
        y1 = max(page_rect.y0, min(y1, page_rect.y1))

        if (x1 - x0) < 0.5 or (y1 - y0) < 0.5:
            return None

        return fitz.Rect(x0, y0, x1, y1)

    def _extract_page_spans(self, page: fitz.Page, page_index: int) -> List[dict]:
        if page_index in self._page_spans_cache:
            return self._page_spans_cache[page_index]

        spans: List[dict] = []
        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    span_bbox = span.get("bbox")
                    if not span_bbox or len(span_bbox) != 4:
                        continue
                    spans.append(span)

        self._page_spans_cache[page_index] = spans
        return spans

    def _match_spans_for_rect(self, rect: fitz.Rect, spans: List[dict]) -> List[dict]:
        matches: List[dict] = []
        rect_area = max(rect.get_area(), 1e-6)

        for span in spans:
            span_rect = fitz.Rect(span["bbox"])
            intersection = rect & span_rect
            if intersection.is_empty:
                continue

            overlap_ratio = intersection.get_area() / rect_area
            if overlap_ratio >= 0.08:
                matches.append(span)

        return matches

    def _build_style(self, block_type: str, spans: List[dict]) -> dict:
        fallback_style = self.style_config.get_style(block_type)

        if not spans:
            return {
                "font_size": float(fallback_style["font_size"]),
                "font_name": "helv",
                "color": self.text_color,
            }

        font_sizes = [
            float(span.get("size", fallback_style["font_size"]))
            for span in spans
            if isinstance(span.get("size"), (int, float))
        ]
        font_size = (
            float(statistics.median(font_sizes))
            if font_sizes
            else float(fallback_style["font_size"])
        )

        flags = [int(span.get("flags", 0)) for span in spans]
        is_bold = sum(1 for value in flags if value & 16) >= max(1, len(flags) // 2)
        is_italic = sum(1 for value in flags if value & 2) >= max(1, len(flags) // 2)

        colors = [int(span.get("color", 0)) for span in spans if "color" in span]
        if colors:
            dominant_color_int = max(set(colors), key=colors.count)
            color = self._int_to_rgb_tuple(dominant_color_int)
        else:
            color = self.text_color

        font_name = self._select_builtin_font_name(is_bold=is_bold, is_italic=is_italic)

        return {
            "font_size": max(self.min_font_size, min(font_size, 48.0)),
            "font_name": font_name,
            "color": color,
        }

    def _insert_text_with_fallback(
        self,
        page: fitz.Page,
        rect: fitz.Rect,
        text: str,
        style: dict,
    ) -> bool:
        fontfile = self._get_unicode_fontfile()
        font_size = float(style["font_size"])
        font_name = "F0" if fontfile else style.get("font_name", "helv")
        color = style["color"]

        logger.info(f"Inserting text with fontfile: {fontfile}")

        for _ in range(self.max_font_shrink_attempts):

            remaining = page.insert_textbox(
                rect,
                text,
                fontsize=font_size,
                fontname=font_name,
                fontfile=fontfile,
                color=color,
                align=fitz.TEXT_ALIGN_LEFT,
            )
            if remaining >= 0:
                return True

            font_size -= self.font_shrink_step
            if font_size < self.min_font_size:
                break

        return False

    def _select_builtin_font_name(self, is_bold: bool, is_italic: bool) -> str:
        if is_bold and is_italic:
            return "hebi"
        if is_bold:
            return "hebo"
        if is_italic:
            return "heit"
        return "helv"

    def _int_to_rgb_tuple(self, color_value: int) -> Tuple[float, float, float]:
        red = (color_value >> 16) & 255
        green = (color_value >> 8) & 255
        blue = color_value & 255
        return (red / 255.0, green / 255.0, blue / 255.0)