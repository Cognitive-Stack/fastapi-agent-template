from typing import Literal
from pydantic import SecretStr, field_validator, AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "chatbot-api"
    env: Literal["dev", "stg", "prod"] = "dev"
    debug: bool = False
    
    # Database
    mongo_uri: AnyUrl
    mongo_db_name: str = "chatbot_db"
    
    # Security
    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    api_key: SecretStr
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]
    
    # Logging
    log_level: str = "INFO"
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


settings = Settings() 