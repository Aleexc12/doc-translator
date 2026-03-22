"""Local Ollama based on OpenAI-compatible API."""

import hashlib
import logging
import os
from pathlib import Path
from typing import List, Optional

from openai import OpenAI

from translators.base import BaseTranslator

logger = logging.getLogger(__name__)

_DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
_DEFAULT_OLLAMA_MODEL = "llama3.2"

class OllamaTranslator(BaseTranslator):
    """Local Ollama based on OpenAI-compatible API."""

    # Language code to name mapping
    LANG_MAP = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ch": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "ar": "Arabic",
        "ru": "Russian",
        "hi": "Hindi",
        "pl": "Polish",
    }

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "es",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        use_cache: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize Ollama translator (OpenAI-compatible HTTP API).

        Args:
            source_lang: Source language code
            target_lang: Target language code
            api_key: Sent to the client(defaults to OLLAMA_API_KEY env var)
            base_url: Custom API base URL (defaults to OLLAMA_BASE_URL env var)
            model: Model name (defaults to OLLAMA_MODEL env var or gpt-4o-mini)
            temperature: Sampling temperature (0.0-1.0)
            use_cache: Enable translation caching
            cache_dir: Cache directory path (defaults to .translation_cache)
        """
        super().__init__(source_lang, target_lang)

        self.api_key = api_key or os.getenv("OLLAMA_API_KEY", "ollama")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE_URL)
        self.model = model or os.getenv("OLLAMA_MODEL", _DEFAULT_OLLAMA_MODEL)
        self.temperature = temperature
        self.use_cache = use_cache

        # Initialize OpenAI client
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

        # Setup cache
        if self.use_cache:
            self.cache_dir = cache_dir or Path(".translation_cache")
            self.cache_dir.mkdir(exist_ok=True)

        logger.info(
            f"✅ OpenAI translator initialized: {self.model} "
            f"({source_lang} → {target_lang})"
        )

    def translate(self, text: str) -> str:
        """
        Translate text from source to target language.

        Args:
            text: Text to translate

        Returns:
            Translated text
        """
        if not self.is_translation_needed(text):
            return text

        # Check cache
        cached = self._get_cached(text)
        if cached:
            return cached

        try:
            # Build language names for prompt
            source_name = self.LANG_MAP.get(self.source_lang, self.source_lang)
            target_name = self.LANG_MAP.get(self.target_lang, self.target_lang)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Translate the following text from {source_name} to {target_name}. "
                            "Only return the translation, no quotes, no extra text. "
                            "Preserve meaning and formatting markers if present.\n\n"
                            f"Text:\n{text}"
                        ),
                    }
                ],
                temperature=self.temperature,
            )

            translation = response.choices[0].message.content.strip()

            # Remove quotes if wrapped
            if translation.startswith('"') and translation.endswith('"'):
                translation = translation[1:-1]
            if translation.startswith("'") and translation.endswith("'"):
                translation = translation[1:-1]

            # Save to cache
            self._save_cache(text, translation)

            return translation

        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    def translate_batch(self, texts: List[str]) -> List[str]:
        """
        Translate multiple texts (currently processes sequentially).

        Args:
            texts: List of texts to translate

        Returns:
            List of translated texts in same order
        """
        return [self.translate(text) for text in texts]

    def get_name(self) -> str:
        """Return the name of this translator."""
        return f"Ollama ({self.model})"

    def supports_language_pair(self, source: str, target: str) -> bool:
        """
        Check if this translator supports the given language pair.

        Ollama models support most language pairs.

        Args:
            source: Source language code
            target: Target language code

        Returns:
            True (Ollama supports most languages)
        """
        return True

    def _cache_key(self, text: str) -> Path:
        """
        Generate cache key from text.

        Args:
            text: Text to cache

        Returns:
            Path to cache file
        """
        hash_val = hashlib.md5(
            f"ollama:{self.model}:{self.source_lang}:{self.target_lang}:{text}".encode("utf-8")
        ).hexdigest()
        return self.cache_dir / f"{hash_val}.txt"

    def _get_cached(self, text: str) -> Optional[str]:
        """
        Retrieve cached translation if available.

        Args:
            text: Original text

        Returns:
            Cached translation or None
        """
        if not self.use_cache:
            return None

        cache_file = self._cache_key(text)
        if cache_file.exists():
            try:
                return cache_file.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def _save_cache(self, text: str, translation: str):
        """
        Save translation to cache.

        Args:
            text: Original text
            translation: Translated text
        """
        if not self.use_cache:
            return

        try:
            self._cache_key(text).write_text(translation, encoding="utf-8")
        except Exception:
            pass
