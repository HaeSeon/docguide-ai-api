import json
import os
from typing import Final

import pdfplumber
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.models.schemas import (
    DocAnalysisResult,
    EligibilityResult,
    EligibilityUserProfile,
    ErrorResponse,
)
from openai import OpenAI


client = OpenAI(api_key=settings.OPEN_AI_KEY)

SYSTEM_PROMPT: Final[str] = """
당신은 한국어 공공 문서(공고문, 안내문 등)를 분석해서 사용자에게 꼭 필요한 핵심 정보만 구조화해서 제공하는 AI 비서입니다.

아래 요구사항을 반드시 지키세요.

1. 입력으로 공공 문서의 전체 텍스트가 주어집니다.
2. 문서를 읽고 다음 정보를 JSON으로만 출력해야 합니다. 설명 문장이나 다른 텍스트는 절대 추가하지 마세요.
3. 출력 JSON 스키마는 다음 `DocAnalysisResult`와 정확히 같아야 합니다.

{
  "id": "string",                     // 임의의 분석 ID (예: \"analysis-2025-0001\")
  "summary": "string",                // 행동 중심 요약 - "언제까지 어디서/어떻게 무엇을 하세요" 형태로 작성 (한국어, 존댓말)
  "actions": [
    {
      "type": "pay | apply | check | none",
      "label": "string",
      "deadline": "string | null",
      "link": "string | null"
    }
  ],
  "extracted": {
    "docType": "string",
    "title": "string | null",
    "amount": "number | null",
    "deadline": "string | null",
    "authority": "string | null",
    "applicantType": "string | null"
  },
  "evidence": [
    {
      "field": "string",
      "text": "string",
      "page": "number | null",
      "confidence": "number (0.0 ~ 1.0)"
    }
  ],
  "uncertainty": [
    {
      "field": "string",
      "reason": "string",
      "confidence": "number (0.0 ~ 1.0)"
    }
  ]
}

**summary 작성 규칙:**
- 첫 문장은 반드시 "~까지 ~에서/~로 ~하세요" 형태의 명령형으로 시작
- 예시: "11월 28일까지 LH 청약센터 홈페이지에서 온라인으로 신청하세요"
- 예시: "5월 31일까지 홈택스에서 500만원을 납부하세요"
- 예시: "2월 28일까지 회사에 연말정산 서류를 제출하세요"
- 두 번째 문장부터는 추가 설명, 자격 조건, 주의사항 등을 자연스럽게 서술
- 전체 summary는 2-4문장으로 구성

주의사항:
- JSON 이외의 텍스트(설명, 마크다운, 코멘트)는 절대 출력하지 마세요.
- 값이 확실하지 않은 경우 `null` 또는 합리적인 추정 + `uncertainty` 항목을 채워주세요.
- 날짜/마감일은 사람이 읽기 쉬운 형태(예: "2025-06-07", "2025년 6월 7일" 등)로 적어도 됩니다.
"""

router = APIRouter()


ELIGIBILITY_SYSTEM_PROMPT: Final[str] = """
당신은 한국 공공 임대/분양 주택 공고를 기반으로,
사용자가 입력한 간단한 조건(거주지, 가구 구성, 소득 수준, 특별 자격 등)에 따라
신청 가능성/예상 배점/해야 할 일 체크리스트를 정리해 주는 AI 비서입니다.

입력으로는 두 가지 정보가 주어집니다.
1) 공고문 분석 결과 (DocAnalysisResult 형태)
2) 신청자 조건 (EligibilityUserProfile 형태)

EligibilityUserProfile의 income_level 필드는 다음 중 하나입니다.
- "under_30m": 가구 연 소득 3,000만 원 미만
- "between_30m_50m": 가구 연 소득 3,000만 ~ 5,000만 원
- "over_50m": 가구 연 소득 5,000만 원 이상
- "unknown": 소득 수준을 잘 모름

주의:
- status 필드에는 "eligible" / "likely" / "ineligible" / "unknown" 같은 영문 코드를 사용하지만,
  자연어 설명(status_message) 안에서는 이러한 영어 코드를 그대로 쓰지 말고
  "신청 가능", "신청 가능성이 높음", "조건 미충족", "판단 유보"처럼 한국어로만 표현하세요.

당신의 역할:
- 공고문에서 추출된 정보와 신청자 조건을 함께 보고,
  - 신청 가능 여부: "eligible", "likely", "ineligible", "unknown" 중 하나로 판단
  - 그 이유를 한국어로 친절하게 설명 (status_message)
  - 예상 배점을 대략적으로 추정하고 (가능하면), 없으면 null
  - 당락 기준 점수/참고 정보를 간단히 요약 (score_reference)
  - 지금 사용자가 해야 할 행동을 3~5줄 정도의 체크리스트로 정리 (checklist)

반드시 아래 JSON 스키마에 맞춰 **JSON만** 출력하세요.

{
  "status": "eligible | likely | ineligible | unknown",
  "status_message": "string",
  "estimated_score": number | null,
  "score_reference": "string | null",
  "checklist": ["string", "..."]
}

주의:
- JSON 이외의 텍스트(설명 문장, 마크다운 등)는 절대 포함하지 마세요.
- 제도/점수 체계가 확실하지 않으면 대략적인 설명과 함께 "likely" 또는 "unknown"을 사용하세요.
"""


@router.post(
    "/analyze",
    response_model=DocAnalysisResult,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def analyze_document(file: UploadFile = File(...)):
    """
    문서를 업로드하고 AI로 분석합니다.

    - **file**: 업로드할 문서 파일 (multipart/form-data)
    """
    # 간단한 파일 타입/크기 검증 (필요 시 config의 설정을 사용할 수 있음)
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="업로드된 파일이 없습니다.",
        )

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="빈 파일입니다.",
        )

    # 파일 확장자에 따라 텍스트 추출 방식 분기
    _, ext = os.path.splitext(file.filename.lower())

    if ext == ".pdf":
        # PDF 파일: pdfplumber로 텍스트 추출
        try:
            # UploadFile은 스포일되었으므로 bytes 기반으로 처리
            # pdfplumber는 파일 경로나 파일 객체를 기대하므로 BytesIO 사용
            import io

            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages]
            text = "\n\n".join(pages_text).strip()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF 파일을 읽는 중 오류가 발생했습니다: {e}",
            ) from e

        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF에서 추출할 수 있는 텍스트가 없습니다.",
            )
    else:
        # 기본: UTF-8 텍스트 파일로 처리
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재는 UTF-8 인코딩 텍스트(.txt) 또는 PDF 파일만 지원합니다.",
            )

    if not settings.OPEN_AI_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPEN_AI_KEY가 서버에 설정되어 있지 않습니다.",
        )

    try:
        # OpenAI LLM 호출
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"다음 공공 문서를 분석해서 위 스키마에 맞는 JSON만 출력하세요.\n\n파일 이름: {file.filename}\n\n문서 내용:\n{text}",
                },
            ],
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM 응답이 비어 있습니다.")

        data = json.loads(content)
    except HTTPException:
        # 위에서 이미 적절한 상태코드로 raise 한 경우
        raise
    except Exception as e:
        # LLM 호출/파싱 중 에러
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 분석 중 오류가 발생했습니다: {e}",
        ) from e

    # Pydantic 스키마로 검증 후 반환
    return DocAnalysisResult(**data)


@router.post(
    "/analyze/eligibility",
    response_model=EligibilityResult,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def analyze_eligibility(
    profile: EligibilityUserProfile, doc: DocAnalysisResult
):
    """
    사용자의 조건을 입력받아 해당 공고에 대한 신청 가능성을 평가합니다.

    - **profile**: 사용자의 간단한 조건 정보
    - **doc**: 앞 단계에서 생성된 문서 분석 결과
    """
    if not settings.OPEN_AI_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPEN_AI_KEY가 서버에 설정되어 있지 않습니다.",
        )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": ELIGIBILITY_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        "다음 공고 분석 결과(DocAnalysisResult)와 "
                        "사용자 조건(EligibilityUserProfile)을 참고하여, "
                        "위에서 설명한 EligibilityResult JSON만 출력하세요.\n\n"
                        f"[공고 분석 결과]\n"
                        f"{json.dumps(doc.model_dump(), ensure_ascii=False)}\n\n"
                        f"[사용자 조건]\n"
                        f"{json.dumps(profile.model_dump(), ensure_ascii=False)}"
                    ),
                },
            ],
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM 응답이 비어 있습니다.")

        data = json.loads(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"신청 가능성 분석 중 오류가 발생했습니다: {e}",
        ) from e

    return EligibilityResult(**data)

