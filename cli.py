#!/usr/bin/env python3
"""
Command-line interface for PDF translator.

This CLI matches the behavior of the original translate.py script.
"""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from main import translate_pdf, resolve_pdf_path

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="PDF Translator with MinerU - High-accuracy layout-preserving translation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - auto-finds in pdfs/ folder (English to Spanish, uses MinerU + OpenAI by default)
  python translate_cli.py document.pdf
  python translate_cli.py document              # .pdf extension optional

  # Fast PyMuPDF extraction (simple, fast, good for text-based PDFs)
  python translate_cli.py document.pdf --extractor pymupdf

  # Free local GPU translation with MarianMT (no API costs!)
  python translate_cli.py document.pdf --translator marianmt

  # Fast extraction + free translation (best for simple PDFs)
  python translate_cli.py document.pdf --extractor pymupdf --translator marianmt

  # MinerU extraction with different backend (accurate, handles formulas/tables)
  python translate_cli.py document.pdf --extractor mineru --backend vlm-auto-engine

  # Force re-extraction (ignores cached middle.json, only for MinerU)
  python translate_cli.py document.pdf --f

  # Different language pair
  python translate_cli.py document.pdf --source-lang en --target-lang fr

Environment Variables (for OpenAI translator):
  OPENAI_API_KEY    - OpenAI API key (required for --translator openai)
  OPENAI_API_BASE   - Custom API base URL (optional)
  OPENAI_MODEL      - Model name (default: gpt-4o-mini)

Notes:
  - PDF search order: direct path -> pdfs/filename -> with .pdf extension
  - Output: <input>_translated_<lang>.pdf (same folder as input)
  - Cached extraction: ./output/<stem>/hybrid_auto/<stem>_middle.json
  - Translation cache: ./.translation_cache/
        """,
    )

    parser.add_argument(
        "pdf",
        help="PDF filename (auto-searches in pdfs/) or full path"
    )

    parser.add_argument(
        "--source-lang",
        default="en",
        help="Source language (default: en)",
    )

    parser.add_argument(
        "--target-lang",
        default="es",
        help="Target language (default: es)",
    )

    parser.add_argument(
        "--extractor",
        default="mineru",
        choices=["pymupdf", "mineru"],
        help="Extraction method: pymupdf (fast, simple) or mineru (accurate, complex) (default: mineru)",
    )

    parser.add_argument(
        "--translator",
        default="openai",
        choices=["openai", "marianmt"],
        help="Translation backend: openai (API, high quality) or marianmt (local GPU, free) (default: openai)",
    )

    parser.add_argument(
        "--f",
        action="store_true",
        help="Force re-extraction (ignore cached middle.json, only for mineru)",
    )

    parser.add_argument(
        "--backend",
        default="hybrid-auto-engine",
        choices=[
            "pipeline",
            "hybrid-auto-engine",
            "hybrid-http-client",
            "vlm-auto-engine",
            "vlm-http-client",
        ],
        help="MinerU backend (default: hybrid-auto-engine, only for mineru extractor)",
    )

    parser.add_argument(
        "--api-key",
        help="OpenAI API key (overrides env var)",
    )

    parser.add_argument(
        "--base-url",
        help="OpenAI API base URL (overrides env var)",
    )

    parser.add_argument(
        "--model",
        help="OpenAI model (default: gpt-4o-mini)",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable translation caching",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging (DEBUG level)",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output PDF path (default: <input>_translated_<lang>.pdf)",
    )

    return parser.parse_args()


def main():
    """Main CLI entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Resolve input PDF path
        input_pdf = resolve_pdf_path(args.pdf, SCRIPT_DIR)
        logger.info(f"Found PDF: {input_pdf}")

        # Determine output path
        output_pdf = Path(args.output) if args.output else None

        # Run translation
        stats = translate_pdf(
            pdf_path=input_pdf,
            output_pdf=output_pdf,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            extractor=args.extractor,
            translator=args.translator,
            backend=args.backend,
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
            use_cache=not args.no_cache,
            force_extract=args.f,
        )

        print(f"\n✓ Success! Translated PDF: {stats['output_pdf']}")
        print(f"⏱️  Total time: {stats['elapsed_time']:.2f} seconds")

    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
