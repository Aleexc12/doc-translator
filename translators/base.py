"""Base abstract class for translators."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class BaseTranslator(ABC):
    """Abstract base class for text translators."""

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "es",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize translator.

        Args:
            source_lang: Source language code (e.g., 'en', 'es', 'fr')
            target_lang: Target language code
            config: Translator-specific configuration
        """
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.config = config or {}

    @abstractmethod
    def translate(self, text: str) -> str:
        """
        Translate text from source to target language.

        Args:
            text: Text to translate

        Returns:
            Translated text

        Raises:
            TranslationError: If translation fails
        """
        pass

    @abstractmethod
    def translate_batch(self, texts: List[str]) -> List[str]:
        """
        Translate multiple texts in batch (more efficient).

        Args:
            texts: List of texts to translate

        Returns:
            List of translated texts in same order

        Raises:
            TranslationError: If translation fails
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this translator."""
        pass

    @abstractmethod
    def supports_language_pair(self, source: str, target: str) -> bool:
        """
        Check if this translator supports the given language pair.

        Args:
            source: Source language code
            target: Target language code

        Returns:
            True if supported, False otherwise
        """
        pass

    def is_translation_needed(self, text: str) -> bool:
        """
        Check if text needs translation (e.g., skip empty strings).

        Args:
            text: Text to check

        Returns:
            True if translation needed, False otherwise
        """
        return bool(text and text.strip())
