"""
Main orchestrator for PDF translation using modular architecture.

This module provides the high-level workflow that matches the original translate.py behavior.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Optional

from extractors import MinerUExtractor, PyMuPDFExtractor, ExtractionResult
from translators import OpenAITranslator, MarianMTTranslator
from renderers import OverlayRenderer
from utils.styling import should_translate_block_type
from utils.formula_handler import FormulaHandler

logger = logging.getLogger(__name__)


def translate_pdf(
    pdf_path: Path,
    output_pdf: Optional[Path] = None,
    source_lang: str = "en",
    target_lang: str = "es",
    extractor: str = "mineru",
    translator: str = "openai",
    backend: str = "hybrid-auto-engine",
    parse_method: str = "auto",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    use_cache: bool = True,
    force_extract: bool = False,
    output_dir: Optional[Path] = None,
) -> Dict:
    """
    Complete PDF translation workflow: extract + translate + render.

    Args:
        pdf_path: Path to input PDF
        output_pdf: Path for output PDF (defaults to <input>_translated_<lang>.pdf)
        source_lang: Source language code
        target_lang: Target language code
        extractor: Extraction method ('pymupdf' or 'mineru')
        translator: Translation backend ('openai' or 'marianmt')
        backend: MinerU backend (only for mineru extractor)
        parse_method: MinerU parse method (only for mineru extractor)
        api_key: OpenAI API key (only for openai translator)
        base_url: OpenAI API base URL (only for openai translator)
        model: Model name (OpenAI model or HuggingFace model)
        use_cache: Enable translation caching (only for openai translator)
        force_extract: Force re-extraction even if cached (only for mineru)
        output_dir: Output directory for MinerU extraction

    Returns:
        Dictionary with translation statistics
    """
    start_time = time.time()

    # Set default output path
    if output_pdf is None:
        # If PDF is in pdfs/ folder, output to output_pdfs/ folder
        if pdf_path.parent.name == "pdfs":
            output_pdfs_dir = pdf_path.parent.parent / "output_pdfs"
            output_pdfs_dir.mkdir(exist_ok=True)
            output_pdf = output_pdfs_dir / f"{pdf_path.stem}_translated_{target_lang}.pdf"
        else:
            output_pdf = pdf_path.parent / f"{pdf_path.stem}_translated_{target_lang}.pdf"

    # Set default output directory
    if output_dir is None:
        output_dir = Path("output")

    logger.info("=" * 60)
    logger.info("PDF TRANSLATION WORKFLOW")
    logger.info("=" * 60)
    logger.info(f"Input:  {pdf_path}")
    logger.info(f"Output: {output_pdf}")
    logger.info(f"Languages: {source_lang} -> {target_lang}")
    logger.info(f"Extractor: {extractor}")
    logger.info(f"Translator: {translator}")
    if extractor == "mineru":
        logger.info(f"Backend: {backend}")

    # Step 1: Extract PDF structure
    logger.info("=" * 60)
    logger.info("STEP 1: EXTRACTING PDF STRUCTURE")
    logger.info("=" * 60)

    if extractor == "pymupdf":
        # Use PyMuPDF extractor (fast, simple)
        extractor_instance = PyMuPDFExtractor(mode="line")
        extraction_result = extractor_instance.extract(pdf_path)
    else:
        # Use MinerU extractor (accurate, complex)
        extractor_instance = MinerUExtractor(
            backend=backend,
            parse_method=parse_method,
            lang=source_lang,
            formula_enable=True,
            table_enable=True,
            output_dir=output_dir,
        )

        # Check if we need to force extraction
        middle_json_path = extractor_instance._get_middle_json_path(pdf_path)
        if force_extract and middle_json_path.exists():
            logger.info("Force extraction requested, removing cached middle.json...")
            middle_json_path.unlink()

        extraction_result = extractor_instance.extract(pdf_path)

    logger.info(
        f"✓ Extracted {len(extraction_result.text_blocks)} text blocks, "
        f"{len(extraction_result.formula_blocks)} formula blocks"
    )

    # Step 2: Translate content
    logger.info("=" * 60)
    logger.info("STEP 2: TRANSLATING CONTENT")
    logger.info("=" * 60)

    # Select translator backend
    if translator == "marianmt":
        translator_instance = MarianMTTranslator(
            source_lang=source_lang,
            target_lang=target_lang,
            model_name=model,
        )
    else:  # openai (default)
        translator_instance = OpenAITranslator(
            source_lang=source_lang,
            target_lang=target_lang,
            api_key=api_key,
            base_url=base_url,
            model=model,
            use_cache=use_cache,
        )

    formula_handler = FormulaHandler()
    translated_texts = {}
    translated_count = 0
    skipped_count = 0

    for block in extraction_result.text_blocks:
        # Skip non-translatable blocks
        if not should_translate_block_type(block.block_type):
            skipped_count += 1
            continue

        original_text = block.text
        if not original_text or not original_text.strip():
            skipped_count += 1
            continue

        # Get formulas from metadata if present
        formulas = block.metadata.get("formulas", {}) if block.metadata else {}

        # Translate text
        translated = translator_instance.translate(original_text)

        # Restore formulas
        if formulas:
            translated = formula_handler.restore_formulas(translated, formulas)

        translated_texts[original_text] = translated
        translated_count += 1

        if translated_count % 20 == 0:
            logger.info(f"Translated {translated_count} blocks...")

    logger.info(
        f"✓ Translated {translated_count} blocks, skipped {skipped_count} blocks"
    )

    # Step 3: Render translated PDF
    logger.info("=" * 60)
    logger.info("STEP 3: RENDERING TRANSLATED PDF")
    logger.info("=" * 60)

    renderer = OverlayRenderer()
    output_path = renderer.render(
        input_pdf=pdf_path,
        output_pdf=output_pdf,
        text_blocks=extraction_result.text_blocks,
        formula_blocks=extraction_result.formula_blocks,
        translated_texts=translated_texts,
    )

    elapsed_time = time.time() - start_time

    # Summary
    logger.info("=" * 60)
    logger.info("TRANSLATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Input:  {pdf_path}")
    logger.info(f"Output: {output_path}")
    logger.info(
        f"Stats:  {translated_count}/{len(extraction_result.text_blocks)} blocks translated"
    )
    logger.info(f"Time:   {elapsed_time:.2f}s")

    return {
        "input_pdf": str(pdf_path),
        "output_pdf": str(output_path),
        "total_blocks": len(extraction_result.text_blocks),
        "translated_blocks": translated_count,
        "skipped_blocks": skipped_count,
        "elapsed_time": elapsed_time,
    }


def resolve_pdf_path(pdf_arg: str, script_dir: Path) -> Path:
    """
    Resolve PDF path - check direct path first, then pdfs/ folder.

    Args:
        pdf_arg: PDF filename or path from command line
        script_dir: Script directory

    Returns:
        Resolved Path to PDF file

    Raises:
        FileNotFoundError if PDF not found
    """
    # Try as direct path first
    direct_path = Path(pdf_arg)
    if direct_path.exists() and direct_path.is_file():
        return direct_path

    # Try in pdfs/ folder (just filename)
    pdfs_dir = script_dir / "pdfs"
    in_pdfs = pdfs_dir / pdf_arg
    if in_pdfs.exists() and in_pdfs.is_file():
        return in_pdfs

    # Try adding .pdf extension if not present
    if not pdf_arg.endswith(".pdf"):
        direct_with_ext = Path(f"{pdf_arg}.pdf")
        if direct_with_ext.exists():
            return direct_with_ext

        in_pdfs_with_ext = pdfs_dir / f"{pdf_arg}.pdf"
        if in_pdfs_with_ext.exists():
            return in_pdfs_with_ext

    raise FileNotFoundError(
        f"PDF not found: tried '{pdf_arg}', '{in_pdfs}', and with .pdf extension"
    )
