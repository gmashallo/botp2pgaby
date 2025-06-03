import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    api_key: str = os.getenv("API_KEY", "")
    api_secret: str = os.getenv("API_SECRET", "")
    binance_api_url: str = "https://api.binance.com"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    """
    Returns cached settings instance to avoid reading .env file on every call
    """
    return Settings()
