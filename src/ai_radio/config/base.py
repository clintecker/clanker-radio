"""Configuration composition root (to be populated in later tasks)."""
from pydantic_settings import BaseSettings


class RadioConfig(BaseSettings):
    """Root configuration - will compose domain configs in later tasks."""
    pass
