from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analyze

app = FastAPI(
    title="DocGuide AI API",
    description="공공문서 분석을 위한 AI API 서버",
    version="0.1.0",
)

# CORS 설정 - 개발 환경: Next.js 프론트엔드 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js 개발 서버
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(analyze.router, prefix="/api", tags=["analyze"])


@app.get("/")
async def root():
    return {"message": "docguide-ai-api is running"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}

