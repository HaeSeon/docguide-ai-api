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

---

## LLM 아키텍처 & 동작 흐름

이 백엔드는 단순히 GPT에 한 번 물어보는 수준이 아니라,  
**여러 개의 LLM 태스크를 조합해 “문서 분석 → 행동 가이드 → 질의응답 → 자격 판정”** 까지 처리하는 구조로 설계되어 있습니다.

### 1. 전체 데이터 플로우

```text
[사용자] --(파일 업로드)--> [FastAPI /api/analyze]
     └─> pdfplumber 등으로 텍스트 추출
           │
           ▼
    [LLM 1: 문서 분석]
      - 모델: gpt-4.1-mini
      - 프롬프트: SYSTEM_PROMPT
      - 출력: DocAnalysisResult(JSON)
           │
           ▼
  ┌─────────────────────┐
  │ DocAnalysisResult   │
  │  - summary          │
  │  - actions[]        │
  │  - extracted        │
  │  - evidence[]       │
  │  - uncertainty[]    │
  └─────────────────────┘
           │
           ├─> 프론트 결과 페이지 (요약/To‑Do/핵심 정보)
           ├─> [LLM 2: 자격 판정] /api/analyze/eligibility
           ├─> [LLM 3: 취업지원 자격] /api/analyze/job-support-eligibility
           └─> [LLM 4: 문서 기반 Q&A] /api/chat
```

각 LLM 호출은 **명확한 역할과 스키마**를 가지고 있으며,  
Pydantic 모델을 통해 응답을 검증하여 신뢰성을 높였습니다.

---

## LLM 1: 문서 분석 (`/api/analyze`)

### 역할

- 공공문서 전체 텍스트를 분석해 **문서 유형, 핵심 요약, 행동(To‑Do), 주요 필드, 근거(evidence)** 등을 구조화된 JSON으로 생성
- 출력 스키마: `app/models/schemas.py` 의 `DocAnalysisResult`

### 사용 모델

- `gpt-4.1-mini` (`client.chat.completions.create`)
- `response_format={"type": "json_object"}` 로 **JSON 출력 강제**

### 주요 프롬프트 (SYSTEM_PROMPT 개요)

- 입력: 전체 문서 텍스트
- 출력 형식:
  - `id`: 분석 ID
  - `summary`: **“언제까지 어디서 무엇을 하세요”** 형태의 행동 중심 한 문장 + 추가 설명
  - `actions[]`: `type(pay|apply|check|none)`, `label`, `deadline`, `link`
  - `extracted`:
    - `docType`: 문서 유형 (예: `housing_application`, `income_tax`, `local_tax`, `year_end_tax`, `health_insurance`, `subsidy_notice`)
    - `title`, `amount`, `deadline`, `authority`, `applicantType`
  - `evidence[]`: 각 필드에 대한 근거 문장 + page + confidence
  - `uncertainty[]`: 확실하지 않은 값과 그 이유

프롬프트에서는 **문서 유형별 예시**를 다수 제공하여 Few-shot 효과를 얻습니다.

- 주택청약 공고 예시
- 종합소득세 고지서 예시
- 연말정산 안내문 예시
- 건강보험료 고지서 예시
- 취업지원금 안내문 예시 등

이를 통해 **LLM이 어떤 값을 어떤 필드에 넣어야 하는지 명확히 이해**하도록 유도합니다.

### 안전장치

- Pydantic `DocAnalysisResult` 로 LLM 응답을 검증
  - 필수 필드 누락, 타입 불일치 시 HTTP 500 에러로 처리
- `evidence` 와 `uncertainty` 필드를 사용해
  - “이 값이 어디서 나왔는지”
  - “얼마나 확실한지” 를 함께 저장 → 이후 Q&A/설명에 활용 가능

---

## LLM 2: 주택청약 자격 판정 (`/api/analyze/eligibility`)

### 역할

- **DocAnalysisResult (주택청약 공고)** + **사용자 조건(EligibilityUserProfile)** 을 입력으로 받아,
  - 신청 가능 여부 (`status`)
  - 그 이유 (`status_message`)
  - 예상 배점 (`estimated_score`)
  - 참고 점수 (`score_reference`)
  - 지금 해야 할 행동 체크리스트 (`checklist[]`)
    를 생성합니다.

### 사용 모델 & 프롬프트

- 모델: `gpt-4.1-mini`
- 프롬프트: `ELIGIBILITY_SYSTEM_PROMPT`
  - `EligibilityUserProfile` 필드 정의(소득 구간, 가구 구성 등)를 상세 설명
  - status 코드는 영어 (`eligible`, `likely`, `ineligible`, `unknown`) 를 쓰되,
    사용자에게 보여줄 설명은 **한국어**로만 작성하도록 강제
  - 체크리스트 항목 수, 톤(친절하고 이해하기 쉽도록)을 규정

### 흐름

```text
프론트: 사용자 조건 입력 → /api/analyze/eligibility
    │
    ▼
백엔드: DocAnalysisResult + EligibilityUserProfile + ELIGIBILITY_SYSTEM_PROMPT
    │
    ▼
LLM: 신청 가능성/배점/체크리스트 계산 → EligibilityResult(JSON)
```

응답은 `EligibilityResult` Pydantic 스키마로 검증됩니다.

---

## LLM 3: 취업지원금 자격 판정 (`/api/analyze/job-support-eligibility`)

### 역할

- 취업지원/지원금 공고(예: 국민취업지원제도)와 사용자 조건을 바탕으로,
  - I유형(요건심사형) / II유형(선발형) / 부적격 판정
  - 예상 지원 금액/기간 설명
  - 준비 서류 체크리스트
  - 주의사항 리스트
    를 생성합니다.

### 사용 모델 & 프롬프트

- 모델: `gpt-4.1-mini`
- 프롬프트: `JOB_SUPPORT_ELIGIBILITY_PROMPT`
  - `JobSupportUserProfile` 각 필드를 상세 설명
  - I·II 유형의 전형적인 기준(소득 중위 60% 이하, 재산 4억 이하, 취업경험 유무 등)을 예시로 제공
  - JSON 스키마(`JobSupportEligibilityResult`)에 맞게만 출력하도록 명시

### 흐름

```text
프론트: 취업지원금 모달에서 조건 입력 → /api/analyze/job-support-eligibility
    │
    ▼
백엔드: DocAnalysisResult + JobSupportUserProfile + JOB_SUPPORT_ELIGIBILITY_PROMPT
    │
    ▼
LLM: eligible_type(type_1/type_2/ineligible) + 설명/체크리스트/주의사항 생성
```

응답은 `JobSupportEligibilityResult` 스키마로 검증하여 UI에 그대로 사용됩니다.

---

## LLM 4: 문서 기반 Q&A (`/api/chat`)

### 역할

- 사용자가 업로드한 문서에 대해 자연어로 질문하면,
  - 문서 내용에 기반한 답변 (`message`)
  - 다음에 물어볼 만한 추천 질문 (`suggestions[]`)
  - 답변의 근거가 된 문장/문단 (`sources[]`)
    를 반환합니다.

### 입력 구조 (`ChatRequest`)

- `doc_id`: 분석 결과 ID
- `doc_context`: 전체 `DocAnalysisResult`
- `messages[]`: 대화 히스토리 (`role=user|assistant|system`)

### 사용 모델 & 프롬프트

- 모델: `gpt-4o-mini`
- 시스템 프롬프트: `CHAT_SYSTEM_PROMPT`
  - 한국 공공문서 해석용으로 **역할(role)과 답변 규칙**을 명시
  - 문서에 없는 정보는 “문서에서 확인할 수 없습니다”라고 답하도록 강제
  - 2~4문장, 존댓말, 과하지 않은 이모지 사용 지침
- `get_chat_prompt(doc_context)`:

```python
context_summary = f"""
문서 유형: {doc_context['extracted']['docType']}
문서 제목: {doc_context['extracted']['title']}
핵심 요약: {doc_context['summary']}
추출 정보: {extracted JSON}
행동 안내: {actions JSON}
"""
```

이 요약 정보를 `CHAT_SYSTEM_PROMPT` 에 삽입하여,  
LLM이 항상 **문서 컨텍스트를 인지한 상태에서 Q&A** 를 수행하도록 합니다.

### 근거(sources) 생성

- `DocAnalysisResult.evidence[]` 를 활용해, 마지막 사용자 질문과 가장 관련 있어 보이는 항목 상위 3개를 선택
- 이를 `AnswerSource(text, page, field)` 로 변환하여 `ChatResponse.sources[]` 로 반환
- 프론트에서는 이 정보를 바탕으로:
  - “📄 이 답변의 근거” 블록
  - “원문 보기” 버튼(해당 페이지로 점프)을 구성

이 구조 덕분에, 사용자 입장에서 **“AI가 무슨 근거로 이렇게 답했는지”** 를 바로 확인할 수 있습니다.

---

## LLM 활용 정리

이 백엔드에서 LLM은 다음과 같은 원칙으로 사용됩니다.

1. **모두 JSON 스키마 기반**
   - 각 태스크마다 Pydantic 모델을 정의하고, LLM은 항상 그 스키마에 맞게 JSON만 출력하도록 요구합니다.
2. **태스크 분리**
   - 문서 분석 / 자격 판정(청약/취업지원) / 문서 기반 Q&A / 추천 질문 등으로 역할을 분리하여  
     하나의 거대한 프롬프트 대신, **작고 명확한 여러 LLM 태스크**로 구성했습니다.
3. **근거와 불확실성 노출**
   - `evidence` 와 `uncertainty` 필드를 통해, LLM의 판단이 어디에서 나왔는지와 신뢰도를 함께 제공합니다.
4. **프론트엔드와의 긴밀한 연동**
   - `docType`, `actions`, `extracted` 값이 프론트의 UI(요약 카드, 모달, 채팅 추천 질문)에 직접 연결되어,  
     모델 출력이 그대로 사용자 경험(UX)으로 이어지도록 설계되어 있습니다.
