from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    POLYGEN_BACKEND_URL: AnyHttpUrl = "http://localhost:3000"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

# Create a single, importable instance of the settings
settings = Settings()