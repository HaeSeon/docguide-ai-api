"""
대화형 질의응답 API
"""
from fastapi import APIRouter, HTTPException, status
from openai import OpenAI

from app.core.config import settings
from app.core.prompts import get_chat_prompt, get_suggested_questions
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    SuggestedQuestion,
    ErrorResponse,
)


client = OpenAI(api_key=settings.OPEN_AI_KEY)

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="문서에 대한 대화형 질의응답",
    description="""
    분석된 문서에 대해 자연어로 질문하고 답변을 받습니다.
    
    - 문서 컨텍스트(doc_context)와 대화 히스토리(messages)를 함께 전송
    - AI가 문서 내용을 바탕으로 답변 생성
    - 추천 질문도 함께 반환
    """,
)
async def chat_with_document(request: ChatRequest):
    """
    문서에 대한 대화형 질의응답
    
    Args:
        request: 채팅 요청 (문서 컨텍스트 + 대화 히스토리)
        
    Returns:
        ChatResponse: AI 답변 + 추천 질문
        
    Raises:
        HTTPException: OpenAI API 키가 없거나 응답 생성 중 오류 발생
    """
    if not settings.OPEN_AI_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPEN_AI_KEY가 서버에 설정되어 있지 않습니다.",
        )
    
    # 대화 히스토리가 너무 길면 최근 10개만 유지 (토큰 절약)
    recent_messages = request.messages[-10:] if len(request.messages) > 10 else request.messages
    
    # 시스템 프롬프트 생성 (문서 컨텍스트 포함)
    system_prompt = get_chat_prompt(request.doc_context.model_dump())
    
    try:
        # OpenAI Chat API 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 빠르고 저렴한 모델
            temperature=0.3,  # 일관된 답변을 위해 낮게 설정
            max_tokens=500,  # 답변 길이 제한
            messages=[
                {"role": "system", "content": system_prompt},
                *[
                    {"role": msg.role, "content": msg.content}
                    for msg in recent_messages
                ],
            ],
        )
        
        answer = response.choices[0].message.content
        
        if not answer:
            raise ValueError("AI 응답이 비어 있습니다.")
        
        # 문서 유형에 맞는 추천 질문 생성
        doc_type = request.doc_context.extracted.docType
        suggested_questions_list = get_suggested_questions(doc_type, limit=3)
        
        suggestions = [
            SuggestedQuestion(text=q["text"], category=q["category"])
            for q in suggested_questions_list
        ]
        
        return ChatResponse(
            message=answer,
            suggestions=suggestions,
            confidence=0.9,  # 추후 실제 신뢰도 계산 로직 추가 가능
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"채팅 응답 생성 중 오류가 발생했습니다: {str(e)}",
        ) from e


@router.get(
    "/chat/suggestions/{doc_type}",
    response_model=list[SuggestedQuestion],
    summary="문서 유형별 추천 질문 조회",
    description="특정 문서 유형에 대한 추천 질문 목록을 반환합니다.",
)
async def get_suggestions_by_type(doc_type: str, limit: int = 5):
    """
    특정 문서 유형에 대한 추천 질문 목록을 반환
    
    Args:
        doc_type: 문서 유형 (예: "housing_application_notice")
        limit: 반환할 최대 질문 개수 (기본값: 5)
        
    Returns:
        추천 질문 목록
    """
    questions = get_suggested_questions(doc_type, limit)
    return [
        SuggestedQuestion(text=q["text"], category=q["category"])
        for q in questions
    ]

