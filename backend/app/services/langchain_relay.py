from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
from app.schemas.common import DigestPayload, GroundedItem, ActionItemDto

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    api_key=settings.OPENAI_API_KEY
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are 'POOM SyncRelay AI', an intelligent async collaboration engine.
Given the unread chat history between cross-border makers, generate a structured digest in the recipient's native language ({preferred_language}).

Output strict JSON with these 6 keys:
1. "summary": Brief status update (1-2 sentences)
2. "decisions": Confirmed facts/decisions
3. "pending": Items that still require discussion
4. "key_questions": Urgent/key questions the recipient must answer
5. "action_items": Immediate actionable tasks for recipient
6. "tone_cushioned_message": A culturally polite REPLY DRAFT the recipient can edit and send back as-is.

GROUNDING RULES:
- Each entry in keys 1-5 must have "text" and "source_ids" (list of message numbers).
- Never state anything without evidence. If none, return []."""),
    ("human", "Chat History:\n{chat_history}")
])

structured_llm = llm.with_structured_output(DigestPayload)
chain = prompt | structured_llm

def generate_ai_digest(messages: List[Dict[str, Any]], lang: str = "ko") -> DigestPayload:
    # LLM 미연결 시 Mock Fallback (v2 Grounding 기준 완벽 준수)
    if not settings.OPENAI_API_KEY or settings.LLM_PROVIDER == "mock" or settings.OPENAI_API_KEY.startswith("your_"):
        return DigestPayload(
            summary=[GroundedItem(text="랜딩페이지 메인 화면 제작 요청이 전달되었습니다.", source_ids=[1, 2], verified=True)],
            decisions=[GroundedItem(text="모바일 화면을 우선 제작하고 메인 컬러는 파란색(#2563eb)으로 확정했습니다.", source_ids=[2, 3], verified=True)],
            pending=[GroundedItem(text="버튼 형태(라운드형 vs 사각형) 미결정 상태입니다.", source_ids=[4], verified=True)],
            key_questions=[GroundedItem(text="버튼을 라운드형과 사각형 중 어떤 형태로 제작할까요?", source_ids=[4], verified=True)],
            action_items=[
                ActionItemDto(text="모바일 메인 화면 시안 제작", source_ids=[1, 2], verified=True),
                ActionItemDto(text="내일 오전까지 초안 전달", source_ids=[5], verified=True, deadline="내일 오전")
            ],
            tone_cushioned_message="시차가 있어 푹 쉬고 오셨길 바랍니다! 요청주신 모바일 화면 우선 제작 건 확인했으며, 버튼은 라운드형으로 시안을 잡아 내일 오전까지 공유드리겠습니다."
        )

    formatted_lines = [f"[{m['id']}] {m['sender_id']}: {m['content']}" for m in messages]
    raw_payload: DigestPayload = chain.invoke({"chat_history": "\n".join(formatted_lines), "preferred_language": lang})

    # 환각 방어 게이트 (유효하지 않은 source_ids 필터링)
    valid_ids = {m["id"] for m in messages}
    def filter_items(items):
        res = []
        for it in items:
            it.source_ids = [sid for sid in it.source_ids if sid in valid_ids]
            it.verified = len(it.source_ids) > 0
            res.append(it)
        return res

    raw_payload.summary = filter_items(raw_payload.summary)
    raw_payload.decisions = filter_items(raw_payload.decisions)
    raw_payload.pending = filter_items(raw_payload.pending)
    raw_payload.key_questions = filter_items(raw_payload.key_questions)
    raw_payload.action_items = filter_items(raw_payload.action_items)

    return raw_payload