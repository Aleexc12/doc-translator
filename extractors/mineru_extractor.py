"""MinerU-based PDF extractor."""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from extractors.base import BaseExtractor, TextBlock, FormulaBlock, ExtractionResult

logger = logging.getLogger(__name__)


def _detect_cuda_available() -> bool:
    """Check if CUDA is available for GPU acceleration."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def _get_magic_pdf_config_path() -> Path:
    """Get path to magic-pdf.json config file."""
    if os.name == "nt":  # Windows
        home = Path(os.environ.get("USERPROFILE", "C:/Users"))
    else:  # Linux/Mac
        home = Path.home()
    return home / "magic-pdf.json"


def _ensure_cuda_config():
    """
    Ensure MinerU config has CUDA enabled if available.

    MinerU uses ~/magic-pdf.json for configuration.
    This function auto-detects CUDA and updates the config.
    """
    config_path = _get_magic_pdf_config_path()

    # Detect CUDA
    cuda_available = _detect_cuda_available()
    device_mode = "cuda" if cuda_available else "cpu"

    # Load existing config or create new
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            config = {}
    else:
        config = {}

    # Check if we need to update
    current_mode = config.get("device-mode", "cpu")

    if current_mode != device_mode:
        config["device-mode"] = device_mode

        # Write updated config
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Updated MinerU config: device-mode = {device_mode}")
        except IOError as e:
            logger.warning(f"Could not update MinerU config: {e}")

    return device_mode


class MinerUExtractor(BaseExtractor):
    """High-accuracy extractor using MinerU."""

    def __init__(
        self,
        backend: str = "hybrid-auto-engine",
        parse_method: str = "auto",
        lang: str = "en",
        formula_enable: bool = True,
        table_enable: bool = True,
        output_dir: Optional[Path] = None,
        config: Optional[dict] = None,
        device: Optional[str] = None,
    ):
        """
        Initialize MinerU extractor.

        Args:
            backend: MinerU backend (hybrid-auto-engine, vlm-auto-engine, etc.)
            parse_method: Parse method (auto, txt, ocr)
            lang: Language for OCR
            formula_enable: Enable formula recognition
            table_enable: Enable table recognition
            output_dir: Output directory for MinerU results
            config: Additional configuration
            device: Device mode ("cuda", "cpu", or None for auto-detect)
        """
        super().__init__(config)
        self.backend = backend
        self.parse_method = parse_method
        self.lang = lang
        self.formula_enable = formula_enable
        self.table_enable = table_enable
        self.output_dir = output_dir or Path("output")

        # Auto-detect and configure CUDA
        if device is None:
            self.device_mode = _ensure_cuda_config()
        else:
            self.device_mode = device
            # Update config with specified device
            config_path = _get_magic_pdf_config_path()
            try:
                if config_path.exists():
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                else:
                    cfg = {}
                cfg["device-mode"] = device
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except IOError:
                pass

        device_emoji = "🚀 GPU" if self.device_mode == "cuda" else "🖥️  CPU"
        logger.info(f"MinerU extractor initialized (backend: {backend}, device: {device_emoji})")

    def extract(self, pdf_path: Path) -> ExtractionResult:
        """
        Extract structured content from PDF using MinerU.

        Args:
            pdf_path: Path to input PDF file

        Returns:
            ExtractionResult containing extracted content
        """
        if not self.validate_pdf(pdf_path):
            raise FileNotFoundError(f"Invalid PDF file: {pdf_path}")

        # Get or create middle.json
        middle_json = self._get_middle_json_path(pdf_path)

        if not middle_json.exists():
            logger.info(f"Running MinerU extraction on {pdf_path}...")
            middle_json = self._run_mineru_extraction(pdf_path)

        # Load and parse middle.json
        logger.info(f"Loading middle.json from {middle_json}...")
        pdf_info = self._load_middle_json(middle_json)

        # Convert to ExtractionResult
        text_blocks = []
        formula_blocks = []

        for page_idx, page_info in enumerate(pdf_info):
            para_blocks = page_info.get("para_blocks", [])

            for para in para_blocks:
                # Extract main block
                block_type = para.get("type", "text")
                bbox = para.get("bbox", [])

                if not bbox or len(bbox) != 4:
                    continue

                # Extract text and formulas
                text, formulas = self._extract_paragraph_text_with_formulas(para)

                if text:
                    text_block = TextBlock(
                        text=text,
                        bbox=bbox,
                        block_type=block_type,
                        page_num=page_idx,
                        font_size=None,
                        font_weight=None,
                        metadata={"formulas": formulas},
                    )
                    text_blocks.append(text_block)

                # Extract formula blocks
                for formula in formulas.values():
                    formula_block = FormulaBlock(
                        content=formula,
                        bbox=bbox,  # Use same bbox as parent block
                        page_num=page_idx,
                        format_type="latex",
                    )
                    formula_blocks.append(formula_block)

                # Handle nested blocks (captions, footnotes)
                nested_blocks = para.get("blocks", [])
                for nested in nested_blocks:
                    nested_type = nested.get("type", "")
                    nested_bbox = nested.get("bbox", [])

                    if nested_bbox and len(nested_bbox) == 4:
                        nested_text, nested_formulas = (
                            self._extract_paragraph_text_with_formulas(nested)
                        )

                        if nested_text:
                            text_block = TextBlock(
                                text=nested_text,
                                bbox=nested_bbox,
                                block_type=nested_type,
                                page_num=page_idx,
                                font_size=None,
                                font_weight=None,
                                metadata={"formulas": nested_formulas, "nested": True},
                            )
                            text_blocks.append(text_block)

        logger.info(
            f"Extracted {len(text_blocks)} text blocks, "
            f"{len(formula_blocks)} formula blocks from {len(pdf_info)} pages"
        )

        return ExtractionResult(
            text_blocks=text_blocks,
            formula_blocks=formula_blocks,
            total_pages=len(pdf_info),
            metadata={
                "extractor": "mineru",
                "backend": self.backend,
                "middle_json": str(middle_json),
            },
        )

    def _run_mineru_extraction(self, pdf_path: Path) -> Path:
        """
        Run MinerU extraction and return path to middle.json.

        Args:
            pdf_path: Path to input PDF

        Returns:
            Path to generated middle.json
        """
        cmd = [
            "mineru",
            "-p",
            str(pdf_path),
            "-o",
            str(self.output_dir),
            "-b",
            self.backend,
            "-m",
            self.parse_method,
        ]

        if self.lang:
            cmd.extend(["-l", self.lang])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error("MinerU extraction failed:")
            logger.error(result.stdout)
            logger.error(result.stderr)
            raise RuntimeError("MinerU extraction failed")

        logger.info("✓ MinerU extraction completed")

        # Return path to middle.json
        middle_json_path = self._get_middle_json_path(pdf_path)

        if not middle_json_path.exists():
            raise FileNotFoundError(
                f"Expected middle.json not found at: {middle_json_path}"
            )

        return middle_json_path

    def _get_middle_json_path(self, pdf_path: Path) -> Path:
        """
        Get path to middle.json for a given PDF.

        Args:
            pdf_path: Path to input PDF

        Returns:
            Path where middle.json should be located
        """
        stem = pdf_path.stem

        # Determine folder name based on backend
        if self.backend.startswith("hybrid"):
            folder_name = f"hybrid_{self.parse_method}"
        elif self.backend.startswith("vlm"):
            folder_name = "vlm"
        else:  # pipeline
            folder_name = self.parse_method

        return self.output_dir / stem / folder_name / f"{stem}_middle.json"

    def _load_middle_json(self, path: Path) -> List[Dict]:
        """
        Load MinerU middle.json file.

        Args:
            path: Path to middle.json

        Returns:
            List of page info dictionaries
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "pdf_info" not in data or not isinstance(data["pdf_info"], list):
            raise ValueError("Invalid middle.json: missing 'pdf_info' list")

        return data["pdf_info"]

    def _extract_paragraph_text_with_formulas(self, para_block: Dict) -> tuple:
        """
        Extract text from paragraph block, replacing formulas with placeholders.

        Args:
            para_block: Paragraph block from middle.json

        Returns:
            Tuple of (text_with_placeholders, placeholder_mapping)
        """
        lines = para_block.get("lines", [])
        texts = []
        placeholders = {}
        formula_idx = 0

        for line in lines:
            spans = line.get("spans", [])
            parts = []

            for span in spans:
                span_type = (span.get("type") or "").lower()
                text_format = (span.get("text_format") or "").lower()
                content = span.get("content", "")

                # Check if this is a formula
                if span_type == "equation" or text_format == "latex":
                    token = f"__FORMULA{formula_idx}__"
                    placeholders[token] = content
                    parts.append(token)
                    formula_idx += 1
                else:
                    parts.append(content)

            line_text = "".join(parts).strip()
            if line_text:
                texts.append(line_text)

        return "\n".join(texts).strip(), placeholders

    def supports_ocr(self) -> bool:
        """Return whether this extractor supports OCR."""
        return True

    def get_name(self) -> str:
        """Return the name of this extractor."""
        device = "GPU" if self.device_mode == "cuda" else "CPU"
        return f"MinerU ({self.backend}, {device})"
