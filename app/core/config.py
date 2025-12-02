import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "Revit Key Backend"
    SQLALCHEMY_DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./revit_keys.db")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change_this_secret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    # SMTP settings for email (support both naming conventions)
    SMTP_HOST: str = os.getenv("MAIL_HOST") or os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("MAIL_PORT") or os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("MAIL_USERNAME") or os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("MAIL_PASSWORD") or os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("MAIL_FROM_ADDRESS") or os.getenv("SMTP_FROM_EMAIL", "noreply@example.com")
    SMTP_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "Revit Key Management")

    OTP_EXPIRE_MINUTES: int = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))

settings = Settings()

def access_token_expires():
    return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
