from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 설정
    API_V1_PREFIX: str = "/api"

    # OpenAI 설정
    OPEN_AI_KEY: str | None = None
    
    # CORS 설정 (필요 시 .env 에서 덮어쓰기)
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://docguide-ai-fe.vercel.app",
    ]
    
    # 파일 업로드 설정
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".txt"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


