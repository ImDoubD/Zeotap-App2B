import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    REDIS_HOST: str = os.getenv("REDIS_HOST")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT"))
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER")
    SMTP_PORT: int = os.getenv("SMTP_PORT")
    SMTP_SENDER_EMAIL: str = os.getenv("SMTP_SENDER_EMAIL")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")

settings = Settings()
