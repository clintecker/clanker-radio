"""Configuration management for AI Radio Station.

Backward compatibility: Old imports still work via re-export.
"""
from ai_radio.config_legacy import RadioConfig, config

__all__ = ["RadioConfig", "config"]
