from typing import Literal, Union
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
    allowed_origins: Union[str, list[str]] = "http://localhost:3000"
    
    # Logging
    log_level: str = "INFO"
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Split comma-separated string into list
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            return origins
        return v if isinstance(v, list) else [str(v)]
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


settings = Settings() 