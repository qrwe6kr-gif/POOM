from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
from app.schemas.relay import RelayDigestResponse, GridCards, ActionItem, SuggestedReply

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=settings.OPENAI_API_KEY
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """당신은 시차 협업 플랫폼 POOM의 AI 비동기 어시스턴트입니다.
수신자(아기 사자)가 부재 중 쌓인 대화를 빠르게 파악할 수 있도록 
1) 4분할 그리드 요약(진행상황, 결정사항, 미결정사항, 핵심질문)
2) 즉시 실행할 액션 아이템 목록(action_items)
3) 부드럽고 긍정적인 어조의 추천 답변(suggested_reply)
을 한국어로 명확히 작성하세요."""),
    ("human", "누적 대화 내역:\n{messages_text}")
])

structured_llm = llm.with_structured_output(RelayDigestResponse)
chain = prompt | structured_llm

def generate_relay_digest(messages: list) -> RelayDigestResponse:
    # LLM 키가 없거나 에러 발생 시 시연용 Fallback 반환
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("your_"):
        return RelayDigestResponse(
            digest_id="dig_landing_01",
            analyzed_count=len(messages),
            header_title=f"{len(messages)}개 메시지 분석 완료",
            header_subtitle="아기 사자가 놓친 대화의 맥락을 간결하게 정리했어요.",
            grid_cards=GridCards(
                progress_summary="랜딩페이지 메인 화면 제작 요청이 전달되었습니다.",
                decisions_made="모바일 화면을 우선 제작하고, 메인 컬러는 파란색(#2563eb)으로 결정했습니다.",
                pending_items="버튼 형태(라운드형 또는 사각형)가 아직 결정되지 않았습니다.",
                key_questions="버튼을 라운드형과 사각형 중 어떤 형태로 제작할지요?"
            ),
            action_items=[
                ActionItem(id="act_1", text="모바일 메인 화면 시안 제작", checked=False),
                ActionItem(id="act_2", text="내일 오전까지 초안 전달", checked=False)
            ],
            suggested_reply=SuggestedReply(
                text="요구사항을 확인했습니다. 모바일 화면을 먼저 제작하겠습니다. 버튼은 전체 디자인과 어울리도록 라운드형을 제안드립니다.",
                tag="톤 완충 적용"
            ),
            workflow_progress=75
        )

    formatted_text = "\n".join([f"[{m['sender_name']}]: {m['content']}" for m in messages])
    return chain.invoke({"messages_text": formatted_text})