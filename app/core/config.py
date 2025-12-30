import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # JWT Configuration
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-here-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    
    # SMTP Configuration
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:8080"
    FRONTEND_URL_8081: str = "http://localhost:8000"
    
    # OTP Configuration
    OTP_EXPIRY_MINUTES: int = 10
    RESET_TOKEN_EXPIRY_MINUTES: int = 15
    
    # Development
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables

settings = Settings()