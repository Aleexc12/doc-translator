#!/usr/bin/env python3
"""
MarianMT-based translator using HuggingFace Transformers.

Provides free, local GPU-accelerated translation using open-source models.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional

from .base import BaseTranslator

logger = logging.getLogger(__name__)


class MarianMTTranslator(BaseTranslator):
    """
    Local GPU-accelerated translator using MarianMT models.

    Features:
    - Free and open-source
    - GPU acceleration (CUDA) when available
    - Automatic chunking for long texts
    - No API costs

    Note: Requires transformers and torch packages.
    """

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "es",
        model_name: Optional[str] = None,
    ):
        """
        Initialize MarianMT translator.

        Args:
            source_lang: Source language code
            target_lang: Target language code
            model_name: HuggingFace model name (auto-detected if not provided)
        """
        super().__init__(source_lang, target_lang)

        try:
            import torch
            from transformers import MarianMTModel, MarianTokenizer
        except ImportError:
            raise ImportError(
                "MarianMT translator requires transformers and torch. "
                "Install with: pip install transformers torch"
            )

        # Detect device (GPU or CPU)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🖥️  Using device: {self.device}")
        if self.device == "cuda":
            logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")

        # Auto-detect model name based on language pair
        if model_name is None:
            model_name = f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"

        self.model_name = model_name
        logger.info(f"📦 Loading MarianMT model ({model_name})...")

        try:
            self.model = MarianMTModel.from_pretrained(model_name).to(self.device)
            self.tokenizer = MarianTokenizer.from_pretrained(model_name)
            logger.info("✅ MarianMT translator initialized!")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise ValueError(
                f"Could not load MarianMT model '{model_name}'. "
                f"Make sure the language pair {source_lang}->{target_lang} is supported. "
                f"Check available models at: https://huggingface.co/Helsinki-NLP"
            )

    def translate(self, text: str) -> str:
        """
        Translate a single text string.

        Args:
            text: Text to translate

        Returns:
            Translated text
        """
        if not text.strip():
            return text

        try:
            # MarianMT has a max input length (~400 tokens)
            max_length = 400
            if len(text) > max_length:
                return self._translate_long_text(text)

            # Translate
            tokens = self.tokenizer([text], return_tensors="pt", padding=True, truncation=True)
            tokens = {k: v.to(self.device) for k, v in tokens.items()}
            translated = self.model.generate(**tokens, max_length=512)
            return self.tokenizer.decode(translated[0], skip_special_tokens=True)

        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    def translate_batch(self, texts: List[str]) -> List[str]:
        """
        Translate a batch of texts (more efficient than one-by-one).

        Args:
            texts: List of texts to translate

        Returns:
            List of translated texts
        """
        if not texts:
            return []

        try:
            # Filter empty texts
            non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
            non_empty_texts = [texts[i] for i in non_empty_indices]

            if not non_empty_texts:
                return texts

            # Tokenize batch
            tokens = self.tokenizer(
                non_empty_texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=400
            )
            tokens = {k: v.to(self.device) for k, v in tokens.items()}

            # Translate batch
            translated = self.model.generate(**tokens, max_length=512)
            translated_texts = [
                self.tokenizer.decode(t, skip_special_tokens=True)
                for t in translated
            ]

            # Reconstruct with empty texts in original positions
            result = texts.copy()
            for i, idx in enumerate(non_empty_indices):
                result[idx] = translated_texts[i]

            return result

        except Exception as e:
            logger.error(f"Batch translation error: {e}")
            # Fallback to individual translation
            return [self.translate(t) for t in texts]

    def _translate_long_text(self, text: str) -> str:
        """
        Translate text that exceeds max length by splitting into sentences.

        Args:
            text: Long text to translate

        Returns:
            Translated text
        """
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        translated_parts = []
        current_chunk = ""

        for sentence in sentences:
            # If adding this sentence would exceed limit, translate current chunk
            if len(current_chunk) + len(sentence) < 400:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    translated_parts.append(self._translate_chunk(current_chunk))
                current_chunk = sentence

        # Translate remaining chunk
        if current_chunk:
            translated_parts.append(self._translate_chunk(current_chunk))

        return " ".join(translated_parts)

    def _translate_chunk(self, text: str) -> str:
        """
        Translate a single chunk of text.

        Args:
            text: Chunk to translate

        Returns:
            Translated chunk
        """
        try:
            tokens = self.tokenizer([text], return_tensors="pt", padding=True, truncation=True)
            tokens = {k: v.to(self.device) for k, v in tokens.items()}
            translated = self.model.generate(**tokens, max_length=512)
            return self.tokenizer.decode(translated[0], skip_special_tokens=True)
        except Exception as e:
            logger.error(f"Chunk translation error: {e}")
            return text

    def get_name(self) -> str:
        """Return the name of this translator."""
        return f"MarianMT ({self.model_name})"

    def supports_language_pair(self, source: str, target: str) -> bool:
        """
        Check if this translator supports the given language pair.

        MarianMT models are language-pair specific, so we check if the
        current model matches the requested pair.

        Args:
            source: Source language code
            target: Target language code

        Returns:
            True if supported, False otherwise
        """
        return source == self.source_lang and target == self.target_lang
