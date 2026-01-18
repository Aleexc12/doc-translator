#!/usr/bin/env python3
"""
Standalone CLI wrapper for pdf_translator.
Can be run directly: python translate_cli.py document.pdf
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import pdf_translator
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Now import and run the CLI
from pdf_translator.cli import main

if __name__ == "__main__":
    main()
