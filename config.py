"""Configuration management for PDF translator."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Central configuration for PDF translator."""

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration.

        Args:
            config_dict: Optional configuration dictionary to override defaults
        """
        self.config = self._load_defaults()
        if config_dict:
            self._update_config(config_dict)

    def _load_defaults(self) -> Dict[str, Any]:
        """Load default configuration from environment variables."""
        return {
            # General settings
            "verbose": False,
            "use_cache": True,

            # Translation settings
            "translator": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "base_url": os.getenv("OPENAI_API_BASE"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "temperature": 0.3,
                "max_tokens": 4000,
                "source_lang": "en",
                "target_lang": "es",
            },

            # Extractor settings
            "extractor": {
                "type": "auto",  # auto, pymupdf, ocr, mineru
                "pymupdf": {
                    "mode": "paragraph",  # line, paragraph
                    "column_detection": True,
                },
                "ocr": {
                    "engine": "tesseract",  # tesseract, easyocr, paddleocr
                    "languages": ["eng"],
                    "confidence_threshold": 0.7,
                },
                "mineru": {
                    "backend": "hybrid-auto-engine",
                    "parse_method": "auto",  # auto, txt, ocr
                    "formula_enable": True,
                    "table_enable": True,
                },
            },

            # Renderer settings
            "renderer": {
                "type": "overlay",  # overlay, replacement
                "padding": 0.5,
                "background_color": "white",
                "preserve_fonts": True,
                "fallback_font": "sans-serif",
            },

            # Cache settings
            "cache": {
                "dir": Path(".pdf_translator_cache"),
                "ttl_days": 30,
                "max_size_gb": 5,
            },

            # Paths
            "paths": {
                "output_dir": Path("output"),
                "temp_dir": Path("temp"),
            },
        }

    def _update_config(self, config_dict: Dict[str, Any]):
        """
        Update configuration with custom values.

        Args:
            config_dict: Dictionary with configuration updates
        """
        def deep_update(base: dict, update: dict):
            """Recursively update nested dictionaries."""
            for key, value in update.items():
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    deep_update(base[key], value)
                else:
                    base[key] = value

        deep_update(self.config, config_dict)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key (use dot notation for nested keys, e.g., 'translator.model')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set configuration value by key.

        Args:
            key: Configuration key (use dot notation for nested keys)
            value: Value to set
        """
        keys = key.split(".")
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_translator_config(self) -> Dict[str, Any]:
        """Get translator configuration."""
        return self.config["translator"]

    def get_extractor_config(self) -> Dict[str, Any]:
        """Get extractor configuration."""
        return self.config["extractor"]

    def get_renderer_config(self) -> Dict[str, Any]:
        """Get renderer configuration."""
        return self.config["renderer"]

    def get_cache_dir(self) -> Path:
        """Get cache directory path."""
        cache_dir = self.config["cache"]["dir"]
        cache_dir.mkdir(exist_ok=True)
        return cache_dir

    def get_output_dir(self) -> Path:
        """Get output directory path."""
        output_dir = self.config["paths"]["output_dir"]
        output_dir.mkdir(exist_ok=True)
        return output_dir

    def is_verbose(self) -> bool:
        """Check if verbose mode is enabled."""
        return self.config.get("verbose", False)

    def use_cache(self) -> bool:
        """Check if caching is enabled."""
        return self.config.get("use_cache", True)

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Check API key
        if not self.get("translator.api_key"):
            raise ValueError("OPENAI_API_KEY not set in environment or config")

        # Check extractor type
        extractor_type = self.get("extractor.type")
        valid_extractors = ["auto", "pymupdf", "ocr", "mineru"]
        if extractor_type not in valid_extractors:
            raise ValueError(f"Invalid extractor type: {extractor_type}")

        # Check renderer type
        renderer_type = self.get("renderer.type")
        valid_renderers = ["overlay", "replacement"]
        if renderer_type not in valid_renderers:
            raise ValueError(f"Invalid renderer type: {renderer_type}")

        return True

    def __repr__(self) -> str:
        """String representation of config."""
        return f"Config({self.config})"


# Global config instance
_global_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance.

    Returns:
        Global Config instance
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def set_config(config: Config):
    """
    Set global configuration instance.

    Args:
        config: Config instance to set as global
    """
    global _global_config
    _global_config = config


def reset_config():
    """Reset global configuration to defaults."""
    global _global_config
    _global_config = None
