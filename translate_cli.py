#!/usr/bin/env python3
"""
PDF Translator CLI - Translate PDF documents while preserving layout.

Usage:
    python translate_cli.py document.pdf
    python translate_cli.py pdfs/document.pdf --extractor pymupdf
    python translate_cli.py document.pdf --translator marianmt
"""

from cli import main

if __name__ == "__main__":
    main()
