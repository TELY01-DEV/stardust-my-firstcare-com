import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra='allow',
        populate_by_name=True  # This replaces allow_population_by_field_name
    )
    
    # MongoDB Configuration
    mongodb_uri: str = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin"
    mongodb_host: str = "coruscant.my-firstcare.com"
    mongodb_port: int = 27023
    mongodb_username: str = "opera_admin"
    mongodb_password: str = "Sim!443355"
    mongodb_auth_db: str = "admin"
    mongodb_ssl: bool = True
    mongodb_ssl_ca_file: str = "ssl/ca-latest.pem"
    mongodb_ssl_client_file: str = "ssl/client-combined-latest.pem"
    
    # JWT Authentication Configuration
    jwt_auth_base_url: str = "https://stardust-v1.my-firstcare.com"
    jwt_login_endpoint: str = "/auth/login"
    jwt_refresh_endpoint: str = "/auth/refresh"
    jwt_me_endpoint: str = "/auth/me"
    enable_jwt_auth: bool = True
    
    # Application Configuration
    app_name: str = "My FirstCare Opera Panel"
    app_version: str = "1.0.0"
    debug: bool = False
    dev_mode: bool = False
    port: int = 5054
    host: str = "0.0.0.0"
    
    # SSL Configuration
    ssl_validate: bool = False
    ssl_ca_file: str = "ssl/ca-latest.pem"
    ssl_client_file: str = "ssl/client-combined-latest.pem"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_rotation: str = "1 day"
    log_retention: str = "30 days"
    
    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    enable_cache: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    
    # Environment Settings
    environment: str = os.getenv("ENVIRONMENT", "production")
    node_env: str = "production"

# Initialize settings
settings = Settings()

# Configure logging
logger.remove()
logger.add(
    settings.log_file,
    rotation=settings.log_rotation,
    retention=settings.log_retention,
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
)
logger.add(
    lambda msg: print(msg, end=""),
    level=settings.log_level,
    format="{time:HH:mm:ss} | {level} | {message}"
) 