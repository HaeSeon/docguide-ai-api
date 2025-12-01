"""
채팅 및 문서 분석용 프롬프트 관리
"""
import json
from typing import Dict, List


# 채팅용 시스템 프롬프트
CHAT_SYSTEM_PROMPT = """
당신은 한국 공공문서 해석을 돕는 친절한 AI 비서입니다.

역할:
- 사용자가 업로드한 공공문서(고지서, 공고문 등)에 대한 질문에 답변합니다
- 문서에 명시된 정보를 기반으로 정확하게 답변합니다
- 문서에 없는 정보는 추측하지 않고 솔직하게 "문서에서 확인할 수 없습니다"라고 답합니다

답변 규칙:
1. 친절하고 쉬운 말투 사용 (존댓말 필수)
2. 2-4문장으로 간결하게 답변
3. 구체적인 날짜, 금액, 방법을 명시
4. 필요시 이모지 사용 가능 (과하지 않게)
5. 추가 조치가 필요하면 명확히 안내

예시:
Q: "이거 꼭 내야 해?"
A: "네, 반드시 납부하셔야 합니다. 2025년 5월 31일까지 납부하지 않으면 3%의 가산세가 부과됩니다. 💡"

Q: "어디서 내는 거야?"
A: "홈택스(www.hometax.go.kr)에서 납부하실 수 있습니다. 로그인 후 '납부/환급' 메뉴에서 진행하시면 됩니다."

현재 사용자가 질문하는 문서 정보:
{doc_context}

위 정보를 참고하여 사용자의 질문에 답변하세요.
"""


# 문서 유형별 추천 질문
SUGGESTED_QUESTIONS: Dict[str, List[Dict[str, str]]] = {
    "housing_application_notice": [
        {"text": "제가 신청할 수 있나요?", "category": "general"},
        {"text": "언제까지 신청해야 하나요?", "category": "deadline"},
        {"text": "어디서 신청하는 건가요?", "category": "method"},
        {"text": "필요한 서류는 무엇인가요?", "category": "method"},
        {"text": "경쟁률은 어느 정도인가요?", "category": "general"},
    ],
    "income_tax": [
        {"text": "이 세액이 정상인가요?", "category": "amount"},
        {"text": "언제까지 납부해야 하나요?", "category": "deadline"},
        {"text": "분할 납부가 가능한가요?", "category": "method"},
        {"text": "어디서 납부하나요?", "category": "method"},
        {"text": "늦게 내면 어떻게 되나요?", "category": "general"},
    ],
    "local_tax": [
        {"text": "왜 이 세금을 내야 하나요?", "category": "general"},
        {"text": "납부 기한이 언제인가요?", "category": "deadline"},
        {"text": "납부 방법은 무엇인가요?", "category": "method"},
        {"text": "감면 대상은 없나요?", "category": "general"},
    ],
    "year_end_tax": [
        {"text": "어떤 서류를 준비해야 하나요?", "category": "method"},
        {"text": "언제까지 제출해야 하나요?", "category": "deadline"},
        {"text": "환급은 얼마나 받을 수 있나요?", "category": "amount"},
        {"text": "의료비 공제는 어떻게 받나요?", "category": "general"},
    ],
    "health_insurance": [
        {"text": "보험료가 왜 올랐나요?", "category": "amount"},
        {"text": "언제까지 내야 하나요?", "category": "deadline"},
        {"text": "경감 대상인지 확인하고 싶어요", "category": "general"},
        {"text": "어디서 납부하나요?", "category": "method"},
    ],
    "unknown": [
        {"text": "이 문서는 무엇인가요?", "category": "general"},
        {"text": "언제까지 무엇을 해야 하나요?", "category": "deadline"},
        {"text": "어디에 문의하면 되나요?", "category": "general"},
    ],
}


def get_chat_prompt(doc_context: dict) -> str:
    """
    문서 컨텍스트를 포함한 채팅 시스템 프롬프트 생성
    
    Args:
        doc_context: 문서 분석 결과 딕셔너리
        
    Returns:
        문서 정보가 포함된 시스템 프롬프트
    """
    # 핵심 정보만 추출하여 프롬프트에 포함
    context_summary = f"""
문서 유형: {doc_context.get('extracted', {}).get('docType', 'unknown')}
문서 제목: {doc_context.get('extracted', {}).get('title', '제목 없음')}
핵심 요약: {doc_context.get('summary', '')}
추출 정보: {json.dumps(doc_context.get('extracted', {}), ensure_ascii=False, indent=2)}
행동 안내: {json.dumps(doc_context.get('actions', []), ensure_ascii=False, indent=2)}
"""
    
    return CHAT_SYSTEM_PROMPT.format(doc_context=context_summary)


def get_suggested_questions(doc_type: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    문서 유형에 맞는 추천 질문 반환
    
    Args:
        doc_type: 문서 유형 (예: "housing_application_notice", "income_tax")
        limit: 반환할 최대 질문 개수
        
    Returns:
        추천 질문 목록
    """
    questions = SUGGESTED_QUESTIONS.get(doc_type, SUGGESTED_QUESTIONS["unknown"])
    return questions[:limit]

