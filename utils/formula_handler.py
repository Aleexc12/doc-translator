"""Formula and equation handling utilities."""

import re
from typing import Dict, Tuple


class FormulaHandler:
    """Handles formula preservation during translation using placeholder system."""

    def __init__(self, placeholder_prefix: str = "__FORMULA", placeholder_suffix: str = "__"):
        """
        Initialize formula handler.

        Args:
            placeholder_prefix: Prefix for placeholder tokens
            placeholder_suffix: Suffix for placeholder tokens
        """
        self.prefix = placeholder_prefix
        self.suffix = placeholder_suffix
        self.formula_counter = 0

    def replace_formulas_with_placeholders(self, text: str, formulas: list) -> Tuple[str, Dict[str, str]]:
        """
        Replace formula content with placeholder tokens.

        Args:
            text: Text containing formulas
            formulas: List of formula strings to replace

        Returns:
            Tuple of (text_with_placeholders, placeholder_mapping)
        """
        placeholders = {}
        modified_text = text

        for formula in formulas:
            if formula in modified_text:
                token = self._generate_token()
                placeholders[token] = formula
                modified_text = modified_text.replace(formula, token, 1)

        return modified_text, placeholders

    def create_placeholder_mapping(self, formulas: list) -> Dict[str, str]:
        """
        Create placeholder tokens for a list of formulas.

        Args:
            formulas: List of formula strings

        Returns:
            Dictionary mapping placeholder tokens to formulas
        """
        placeholders = {}
        for formula in formulas:
            token = self._generate_token()
            placeholders[token] = formula
        return placeholders

    def restore_formulas(self, text: str, placeholders: Dict[str, str]) -> str:
        """
        Restore formulas from placeholder tokens.

        Args:
            text: Text with placeholder tokens
            placeholders: Mapping of tokens to formulas

        Returns:
            Text with formulas restored
        """
        restored_text = text
        for token, formula in placeholders.items():
            restored_text = restored_text.replace(token, formula)
        return restored_text

    def _generate_token(self) -> str:
        """Generate unique placeholder token."""
        token = f"{self.prefix}{self.formula_counter}{self.suffix}"
        self.formula_counter += 1
        return token

    def reset_counter(self):
        """Reset the formula counter."""
        self.formula_counter = 0

    def is_placeholder(self, text: str) -> bool:
        """
        Check if text is a placeholder token.

        Args:
            text: Text to check

        Returns:
            True if text matches placeholder pattern
        """
        pattern = re.escape(self.prefix) + r'\d+' + re.escape(self.suffix)
        return bool(re.fullmatch(pattern, text))

    def extract_placeholders(self, text: str) -> list:
        """
        Extract all placeholder tokens from text.

        Args:
            text: Text to search

        Returns:
            List of placeholder tokens found
        """
        pattern = re.escape(self.prefix) + r'\d+' + re.escape(self.suffix)
        return re.findall(pattern, text)
