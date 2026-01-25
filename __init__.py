"""
PDF Translator - Modular PDF translation toolkit.

A modular, open-source PDF translation toolkit that preserves document layout
while translating content between languages.
"""

__version__ = "1.0.0"

from main import translate_pdf
from extractors import (
    BaseExtractor,
    PyMuPDFExtractor,
    MinerUExtractor,
    TextBlock,
    FormulaBlock,
    ExtractionResult,
)
from translators import BaseTranslator, OpenAITranslator, MarianMTTranslator
from renderers import BaseRenderer, OverlayRenderer
from config import Config, get_config, set_config

__all__ = [
    "translate_pdf",
    "BaseExtractor",
    "PyMuPDFExtractor",
    "MinerUExtractor",
    "TextBlock",
    "FormulaBlock",
    "ExtractionResult",
    "BaseTranslator",
    "OpenAITranslator",
    "MarianMTTranslator",
    "BaseRenderer",
    "OverlayRenderer",
    "Config",
    "get_config",
    "set_config",
]
