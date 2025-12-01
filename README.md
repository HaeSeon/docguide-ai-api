# DocGuide AI API

공공문서 분석을 위한 FastAPI 기반 AI API 서버

## 요구사항

- Python 3.11 이상

## 설치 방법

### 1. 가상환경 생성 및 활성화

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

설치되는 패키지:

- `fastapi==0.115.0` - FastAPI 프레임워크
- `uvicorn[standard]==0.32.0` - ASGI 서버
- `python-multipart==0.0.12` - 파일 업로드 지원
- `pydantic==2.9.2` - 데이터 검증
- `pydantic-settings==2.5.2` - 설정 관리

## 실행 방법

### 개발 서버 실행

```bash
uvicorn app.main:app --reload
```

서버는 `http://localhost:8000`에서 실행됩니다.

`--reload` 옵션은 코드 변경 시 자동으로 서버를 재시작합니다.

## API 엔드포인트 테스트

서버 실행 후 아래 방법으로 테스트할 수 있습니다.

### 1. 브라우저/Swagger UI로 테스트 (가장 쉬운 방법)

서버 실행 후 브라우저에서 다음 URL을 열어주세요:

- **Swagger UI (대화형 API 문서)**: http://localhost:8000/docs
- **ReDoc (문서 스타일)**: http://localhost:8000/redoc

Swagger UI에서는:

1. 각 엔드포인트를 클릭하여 상세 정보 확인
2. "Try it out" 버튼으로 직접 API 호출 테스트
3. `/api/analyze` 엔드포인트는 파일 업로드도 테스트 가능

### 2. curl로 테스트

#### GET `/` - 상태 확인

```bash
curl http://localhost:8000/
```

**예상 응답:**

```json
{ "message": "docguide-ai-api is running" }
```

#### GET `/health` - 헬스 체크

```bash
curl http://localhost:8000/health
```

**예상 응답:**

```json
{ "status": "ok" }
```

#### POST `/api/analyze` - 문서 분석

```bash
# 테스트용 파일이 있는 경우
curl -X POST "http://localhost:8000/api/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/document.pdf"

# 파일이 없어도 mock 데이터가 반환됩니다
curl -X POST "http://localhost:8000/api/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.txt"
```

**예상 응답:**

```json
{
  "id": "mock-1",
  "summary": "당신은 이번 LH 청약에 신청 가능해 보이며, 6월 7일까지 온라인으로 신청해야 합니다.",
  "actions": [
    {
      "type": "apply",
      "label": "청약 신청하러 가기",
      "deadline": "2025-06-07",
      "link": "https://apply.lh.or.kr"
    }
  ],
  "extracted": {
    "docType": "housing_application_notice",
    "title": "2025년 서울지역 공공분양 주택 입주자 모집공고",
    "deadline": "2025-06-07",
    "authority": "한국토지주택공사(LH)",
    "applicantType": "무주택세대구성원 중 청약저축가입자"
  },
  "evidence": [
    {
      "field": "deadline",
      "text": "신청기간: 2025년 5월 20일(월) 09:00 ~ 2025년 6월 7일(금) 18:00",
      "page": 1,
      "confidence": 0.95
    }
  ],
  "uncertainty": [
    {
      "field": "amount",
      "reason": "문서에서 정확한 분양가격 정보를 찾을 수 없음",
      "confidence": 0.3
    }
  ]
}
```

### 3. httpie로 테스트 (더 읽기 쉬운 방법)

httpie가 설치되어 있다면:

```bash
# GET 요청
http GET http://localhost:8000/
http GET http://localhost:8000/health

# POST 요청 (파일 업로드)
http POST http://localhost:8000/api/analyze file@/path/to/document.pdf
```

## OpenAPI 문서 확인

서버 실행 후 다음 URL에서 OpenAPI 스키마를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs

  - 대화형 API 문서
  - 각 엔드포인트의 요청/응답 스키마 확인
  - 직접 API 호출 테스트 가능

- **ReDoc**: http://localhost:8000/redoc

  - 읽기 좋은 문서 스타일
  - 스키마 상세 정보 확인

- **OpenAPI JSON 스키마**: http://localhost:8000/openapi.json
  - OpenAPI 스펙 JSON 형식으로 다운로드 가능

## 프로젝트 구조

```
docguide-ai-api/
  app/
    __init__.py
    main.py              # FastAPI 앱 진입점
    api/
      __init__.py
      routes/
        __init__.py
        analyze.py       # 문서 분석 라우트
    core/
      __init__.py
      config.py          # 설정 관리
    models/
      __init__.py
      schemas.py         # Pydantic 스키마
  tests/
  requirements.txt
```

## 주요 기능

- 문서 업로드 및 분석
- CORS 설정 (프론트엔드 연동)
- 파일 형식 및 크기 검증
- API 문서 자동 생성
