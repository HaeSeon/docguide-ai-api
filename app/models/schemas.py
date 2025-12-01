from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ActionType 정의
ActionType = Literal["pay", "apply", "check", "none"]


class DocAction(BaseModel):
    """문서에서 추출된 행동 항목"""
    
    type: ActionType = Field(..., description="행동 유형")
    label: str = Field(..., description="행동 라벨/설명")
    deadline: Optional[str] = Field(None, description="마감일 (ISO 8601 형식 또는 자연어)")
    link: Optional[str] = Field(None, description="관련 링크 URL")


class ExtractedFields(BaseModel):
    """문서에서 추출된 주요 필드"""
    
    docType: str = Field(..., description="문서 유형")
    title: Optional[str] = Field(None, description="문서 제목")
    amount: Optional[float] = Field(None, description="금액 (숫자)")
    deadline: Optional[str] = Field(None, description="마감일")
    authority: Optional[str] = Field(None, description="주관 기관")
    applicantType: Optional[str] = Field(None, description="신청자 유형")


class EvidenceItem(BaseModel):
    """추출된 정보의 근거/증거 항목"""
    
    field: str = Field(..., description="필드명")
    text: str = Field(..., description="원본 텍스트")
    page: Optional[int] = Field(None, description="페이지 번호")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도 (0.0 ~ 1.0)")


class UncertaintyItem(BaseModel):
    """불확실한 정보 항목"""
    
    field: str = Field(..., description="필드명")
    reason: str = Field(..., description="불확실한 이유")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도 (0.0 ~ 1.0)")


class DocAnalysisResult(BaseModel):
    """문서 분석 결과"""
    
    id: str = Field(..., description="분석 결과 ID")
    summary: str = Field(..., description="문서 요약")
    actions: list[DocAction] = Field(..., description="행동 항목 목록")
    extracted: ExtractedFields = Field(..., description="추출된 필드")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="근거 항목 목록")
    uncertainty: list[UncertaintyItem] = Field(default_factory=list, description="불확실한 항목 목록")


# 기존 스키마 (하위 호환성 유지)
class DocumentAnalysisRequest(BaseModel):
    """문서 분석 요청 스키마"""
    
    file_name: str = Field(..., description="업로드된 파일명")
    file_size: int = Field(..., description="파일 크기 (bytes)")


class DocumentAnalysisResponse(BaseModel):
    """문서 분석 응답 스키마 (레거시)"""
    
    document_id: str = Field(..., description="문서 ID")
    summary: str = Field(..., description="문서 요약")
    action_items: list[str] = Field(..., description="해야 할 일 목록")
    deadlines: list[str] = Field(default_factory=list, description="마감일 목록")
    important_info: dict = Field(default_factory=dict, description="중요 정보")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")


class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 에러 정보")


class EligibilityUserProfile(BaseModel):
    """신청자 조건 입력 정보 (간단 버전)"""

    # 거주지
    is_seoul_resident: bool = Field(..., description="서울특별시 거주 여부")

    # 가구 정보
    household_type: Literal["single", "two", "three_plus"] = Field(
        ..., description="세대 구성 유형 (1인가구/2인가구/3인 이상)"
    )
    household_size: Optional[int] = Field(
        None, description="세대원 수 (선택 입력)", ge=1
    )

    # 나이/세대주
    age: Optional[int] = Field(None, description="신청자 나이", ge=18, le=120)
    is_head_of_household: Optional[bool] = Field(
        None, description="세대주 여부"
    )

    # 소득/자산 - 가구 연 소득 구간 (세전, 대략적인 범위)
    income_level: Literal[
        "under_30m",
        "between_30m_50m",
        "over_50m",
        "unknown",
    ] = Field(
        ...,
        description=(
            "가구 연 소득 구간: "
            "under_30m(3,000만 원 미만), "
            "between_30m_50m(3,000만~5,000만 원), "
            "over_50m(5,000만 원 이상), "
            "unknown(잘 모름)"
        ),
    )
    has_high_price_car: Optional[bool] = Field(
        None, description="4천만 원 이상 차량 보유 여부"
    )

    # 특별 자격 (복수 선택 가능)
    special_qualifications: list[
        Literal[
            "basic_support",
            "disabled",
            "single_parent",
            "national_merit",
            "north_korean_defector",
            "elderly_parent_support",
            "none",
        ]
    ] = Field(
        default_factory=list,
        description="특별 자격 태그 목록 (없으면 'none' 포함 가능)",
    )

    # 공공임대 중복 여부
    is_current_public_rental: Optional[bool] = Field(
        None, description="현재 공공임대 거주 여부"
    )
    is_other_waiting_list: Optional[bool] = Field(
        None,
        description="다른 영구/국민/행복주택 예비입주자 여부",
    )


class EligibilityResult(BaseModel):
    """신청 가능성 평가 결과"""

    status: Literal[
        "eligible",
        "likely",
        "ineligible",
        "unknown",
    ] = Field(..., description="신청 가능성 상태")
    status_message: str = Field(
        ..., description="사람이 이해하기 쉬운 한글 설명"
    )
    estimated_score: Optional[int] = Field(
        None, description="예상 배점 (대략적인 값)", ge=0
    )
    score_reference: Optional[str] = Field(
        None, description="당락 기준/참고 점수 설명"
    )
    checklist: list[str] = Field(
        default_factory=list,
        description="지금 해야 할 행동 체크리스트",
    )

