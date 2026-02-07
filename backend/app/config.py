"""
NutriPilot AI - Configuration Management

Loads and validates environment variables for API keys and settings.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    google_api_key: str = Field(
        default="",
        alias="GOOGLE_GENERATIVE_AI_API_KEY",
        description="Google Gemini API key"
    )
    opik_api_key: str = Field(
        default="",
        alias="OPIK_API_KEY",
        description="Comet Opik API key for observability"
    )
    usda_api_key: str = Field(
        default="",
        alias="USDA_API_KEY",
        description="USDA FoodData Central API key"
    )
    
    # Application Settings
    environment: str = Field(
        default="development",
        alias="ENVIRONMENT"
    )
    debug: bool = Field(
        default=True,
        alias="DEBUG"
    )
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL"
    )
    
    # Opik Settings
    opik_project_name: str = Field(
        default="nutripilot",
        alias="OPIK_PROJECT_NAME"
    )
    
    # API Settings
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    
    # CORS Settings (for frontend communication)
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "https://*.vercel.app"],
        alias="CORS_ORIGINS"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    def validate_required_keys(self) -> dict[str, bool]:
        """Check which API keys are configured."""
        return {
            "google_api_key": bool(self.google_api_key),
            "opik_api_key": bool(self.opik_api_key),
            "usda_api_key": bool(self.usda_api_key),
        }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
