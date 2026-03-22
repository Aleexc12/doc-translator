"""Docling PDF extractor — good for academic papers / arXiv."""

import logging
import math
import os
import re
from pathlib import Path
from typing import List, Optional

from extractors.base import BaseExtractor, ExtractionResult, FormulaBlock, TextBlock

logger = logging.getLogger(__name__)

def _chunks_from_markdown(markdown: str) -> List[str]:
    parts = re.split(r"\n\s*\n+", (markdown or "").strip())
    return [p.strip() for p in parts if p.strip()]

def _normalize_docling_bbox(raw_bbox, page_width: float, page_height: float):
    left = float(raw_bbox.l)
    top = float(raw_bbox.t)
    right = float(raw_bbox.r)
    bottom = float(raw_bbox.b)

    if not all(math.isfinite(value) for value in (left, top, right, bottom)):
        return None

    x0, x1 = sorted((left, right))
    y0, y1 = sorted((top, bottom))

    x0 = max(0.0, min(x0, page_width))
    x1 = max(0.0, min(x1, page_width))
    y0 = max(0.0, min(y0, page_height))
    y1 = max(0.0, min(y1, page_height))

    if (x1 - x0) < 0.5 or (y1 - y0) < 0.5:
        return None

    return [x0, y0, x1, y1]

class DoclingExtractor(BaseExtractor):
    """Docling PDF extractor — good for academic papers / arXiv."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        config: Optional[dict] = None,
    ):
        super().__init__(config)
        self.output_dir = output_dir or Path("output") / "docling"
        self.use_gpu = self.config.get("use_gpu", True) if self.config else True

    def extract(self, pdf_path: Path) -> ExtractionResult:
        if not self.validate_pdf(pdf_path):
            raise FileNotFoundError(f"Invalid PDF file: {pdf_path}")

        try:
            import torch
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
            from docling.datamodel.document import DocItemLabel
        except ImportError:
            raise RuntimeError("Docling is not installed. Please install all requirements from requirements(-rocm).txt.")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        pipeline_options = PdfPipelineOptions()

        if self.use_gpu and torch.cuda.is_available():
            logger.info("Run Docling with GPU acceleration.")
            pipeline_options.accelerator_options = AcceleratorOptions(
                num_threads=torch.cuda.device_count(),
                device=AcceleratorDevice.CUDA,
            )
            device_name = "cuda"
        else:
            logger.info("Run Docling with CPU acceleration.")
            pipeline_options.accelerator_options = AcceleratorOptions(
                num_threads=os.cpu_count(),
                device=AcceleratorDevice.CPU,
            )
            device_name = "cpu"

        converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

        logger.info(f"Running Docling on {device_name} with {pipeline_options.accelerator_options.num_threads} threads.")

        result = converter.convert(str(pdf_path))
        document = result.document

        text_blocks: List[TextBlock] = []
        formula_blocks: List[FormulaBlock] = []

        for item, level in document.iterate_items():
            try:
                if not hasattr(item, "text") or not item.text.strip():
                    continue

                bbox = [0.0,0.0,0.0,0.0]
                page_num = 1

                if hasattr(item, "prov") and item.prov:
                    prov = item.prov[0]
                    page_num = max(0, int(prov.page_no) - 1)

                    if hasattr(prov, "bbox"):
                        page_width = None
                        page_height = None

                        if hasattr(document, "pages") and isinstance(document.pages, dict):
                            page_info = document.pages.get(prov.page_no) or document.pages.get(page_num)

                            if page_info and hasattr(page_info, "size"):
                                page_width = float(page_info.size.width)
                                page_height = float(page_info.size.height)

                        if page_width is None or page_height is None:
                            page_width, page_height = 10000.0, 10000.0

                        bbox_object = prov.bbox
                        if hasattr(bbox_object, "to_top_left_origin"):
                            bbox_object = bbox_object.to_top_left_origin(page_height)

                        normalized_bbox = _normalize_docling_bbox(bbox_object, page_width, page_height)
                        if normalized_bbox is None:
                            continue

                        bbox = normalized_bbox

                label_str = str(item.label).split('.')[-1].lower()

                if item.label == DocItemLabel.FORMULA:
                    formula_blocks.append(
                        FormulaBlock(
                            content=item.text,
                            bbox=bbox,
                            page_num=page_num,
                            format_type="latex"
                        )
                    )
                else:
                    text_blocks.append(
                        TextBlock(
                            text=item.text,
                            bbox=bbox,
                            block_type=label_str, 
                            page_num=page_num,
                            metadata={"level": level}
                        )
                    )
            except Exception as e:
                logger.error("Critical error in Docling extraction: %s", e)
                raise

        if hasattr(document, "pages") and isinstance(document.pages, dict):
            total_pages = len(document.pages)
        elif hasattr(document, "num_pages") and callable(document.num_pages):
            total_pages = document.num_pages()
        else:
            total_pages = 1

        logger.info(f"Extracted {len(text_blocks)} text blocks and {len(formula_blocks)} formula blocks from {total_pages} pages.")

        return ExtractionResult(
            text_blocks=text_blocks,
            formula_blocks=formula_blocks,
            total_pages=int(total_pages),
            metadata={"extractor": "docling", "device": device_name, "source_pdf": str(pdf_path)},
        )
    
    def supports_ocr(self) -> bool:
        return True

    def get_name(self) -> str:
        return "Docling"
