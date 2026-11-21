"""EMS AI Service Configuration via pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "evaluator_mapping_db"
    DB_USERNAME: str = "root"
    DB_PASSWORD: str = ""

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # LLM
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 4096

    # EMS Backend
    EMS_API_BASE_URL: str = "http://localhost:8080"
    EMS_API_JWT_TOKEN: str = ""
    EMS_API_TIMEOUT: int = 30

    # MCP Server
    MCP_HOST: str = "localhost"
    MCP_PORT: int = 8002

    # Workflow API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001

    # Import
    IMPORT_DATA_DIR: str = "./data/imports"
    ATTACHMENT_STORAGE_DIR: str = "./data/attachments"

    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
