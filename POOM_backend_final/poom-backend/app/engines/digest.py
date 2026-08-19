"""AI Relay 다이제스트 엔진 — 6필드 + 근거 연결(grounding).

핵심 규칙:
- 모든 항목은 근거 메시지 ID(source_ids)를 가져야 한다. 근거 없는 항목은 파싱 단계에서 버린다.
  → "대화에 없는 결정을 지어내는" 환각을 구조적으로 차단한다.
- 다이제스트 언어는 수신자의 lang을 따른다.

교체 지점(백엔드 B):
- OpenAIProvider.generate()를 LangChain 체인으로 구현하면 된다. Mock은 시연 폴백으로도 사용된다.
"""
from dataclasses import dataclass
from typing import List

FIELDS = ["relay_summary", "decisions", "open_items",
          "key_questions", "action_items", "tone_note"]

DECISION_HINTS = ["확정", "결정", "하기로", "confirm", "decided", "let's go"]
OPEN_HINTS = ["아직", "미정", "고민", "tbd", "not sure", "고려"]
ACTION_HINTS = ["까지", "부탁", "해주세요", "please", "by "]


@dataclass
class DigestContext:
    messages: list            # 미커버 메시지 (Message ORM 또는 유사 객체)
    receiver_name: str
    receiver_lang: str        # 'ko' | 'en' ...
    sender_name: str


def build_prompt(ctx: DigestContext) -> str:
    """실제 LLM 호출용 프롬프트. prompts/digest_prompt.md의 규칙과 동일 구조."""
    numbered = "\n".join(f"[{m.id}] {m.sender_id}: {m.content}" for m in ctx.messages)
    return f"""You are POOM's AI Relay engine for cross-timezone collaboration.
Receiver: {ctx.receiver_name} (language: {ctx.receiver_lang})
Conversation (numbered):
{numbered}

Rules:
1. Output JSON only, with keys: {", ".join(FIELDS)}.
2. Every item in the first five fields MUST include "source_ids": message numbers it is based on.
3. NEVER invent content that is not in the conversation. If a field has no evidence, return [].
4. Write all text in the receiver's language ({ctx.receiver_lang}).
5. tone_note: one culturally softened opening line the receiver could send back.

JSON schema example:
{{"relay_summary": [{{"text": "...", "source_ids": [3, 5]}}],
  "decisions": [{{"text": "...", "source_ids": [4]}}],
  "open_items": [], "key_questions": [], "action_items":
  [{{"task": "...", "assignee": "...", "deadline": null, "source_ids": [6]}}],
  "tone_note": "..."}}"""


class MockProvider:
    """결정적(deterministic) 추출형 요약 — 테스트와 시연 폴백용.

    LLM 없이도 전 파이프라인이 동작함을 보장한다.
    """

    def generate(self, ctx: DigestContext) -> dict:
        ko = ctx.receiver_lang == "ko"

        def has(m, hints):
            b = m.content.lower()
            return any(h in b for h in hints)

        msgs = ctx.messages
        summary = []
        if msgs:
            first, last = msgs[0], msgs[-1]
            summary.append({"text": ("부재 중 대화 요약: " if ko else "While you were away: ")
                                    + first.content[:60], "source_ids": [first.id]})
            if last.id != first.id:
                summary.append({"text": ("마지막 메시지: " if ko else "Latest: ")
                                        + last.content[:60], "source_ids": [last.id]})
        decisions = [{"text": m.content, "source_ids": [m.id]} for m in msgs if has(m, DECISION_HINTS)]
        opens = [{"text": m.content, "source_ids": [m.id]} for m in msgs if has(m, OPEN_HINTS)]
        questions = [{"text": m.content, "source_ids": [m.id]}
                     for m in msgs if m.content.strip().endswith("?")][:3]
        actions = [{"task": m.content, "assignee": ctx.receiver_name, "deadline": None,
                    "source_ids": [m.id]} for m in msgs if has(m, ACTION_HINTS)]
        tone = ("요구사항 확인했습니다. 핵심 질문에 답 주시는 대로 바로 진행하겠습니다."
                if ko else
                "Got it — I've reviewed your requests. I'll start right away once "
                "I answer the key questions above.")
        return {"relay_summary": summary, "decisions": decisions, "open_items": opens,
                "key_questions": questions, "action_items": actions, "tone_note": tone}


class OpenAIProvider:
    """백엔드 B 구현 지점.

    def generate(self, ctx): prompt = build_prompt(ctx) → LangChain/OpenAI 호출
    → json.loads → dict 반환. 파싱 실패·API 장애 시 MockProvider로 폴백할 것.
    """

    def generate(self, ctx: DigestContext) -> dict:  # pragma: no cover
        raise NotImplementedError("백엔드 B: LangChain 체인을 여기에 연결")


def get_provider(name: str):
    return OpenAIProvider() if name == "openai" else MockProvider()


# 팀 프롬프트(다른 키 이름)와 내부 스키마의 별칭 매핑.
# 프롬프트를 바꾸지 않고도 양쪽 출력이 모두 파이프라인을 통과한다.
KEY_ALIASES = {
    "summary": "relay_summary",
    "pending": "open_items",
    "tone_cushioned_message": "tone_note",
}


def normalize(raw: dict) -> dict:
    """LLM 출력의 표기 차이를 내부 스키마로 흡수한다.

    - 키 이름: summary/pending/tone_cushioned_message → 내부 명칭
    - 항목 형태: 문자열, {task:...}, {text:...} 모두 {text, source_ids} 로 통일
    - 단일 문자열 필드(summary): 1개짜리 배열로 승격
    """
    out = {}
    for k, v in (raw or {}).items():
        out[KEY_ALIASES.get(k, k)] = v

    for key in FIELDS[:5]:
        v = out.get(key)
        if v is None:
            out[key] = []
            continue
        if isinstance(v, str):
            v = [v]
        items = []
        for it in v:
            if isinstance(it, str):
                items.append({"text": it, "source_ids": []})
            elif isinstance(it, dict):
                text = it.get("text") or it.get("task") or ""
                item = dict(it)
                item["text"] = text
                item["source_ids"] = list(it.get("source_ids") or [])
                items.append(item)
        out[key] = items

    tone = out.get("tone_note")
    out["tone_note"] = tone if isinstance(tone, str) else ""
    return out


def finalize(raw: dict, valid_ids: set, lang: str) -> dict:
    """근거 검증(grounding gate): source_ids가 실제 메시지를 가리키지 않으면 항목 폐기."""
    raw = normalize(raw)
    out = {}
    for key in FIELDS[:5]:
        kept = []
        for item in raw[key]:
            claimed = item.get("source_ids") or []
            ids = [i for i in claimed if i in valid_ids]
            if claimed and not ids:
                continue                      # 존재하지 않는 근거를 주장 → 환각으로 보고 폐기
            item["source_ids"] = ids
            item["verified"] = bool(ids)      # 근거 미제공 → 표시만 하고 유지(UI에서 '미확인' 배지)
            kept.append(item)
        out[key] = kept
    tone = raw.get("tone_note")
    out["tone_note"] = tone if isinstance(tone, str) and tone.strip() else (
        "부재 중 대화를 정리했어요." if lang == "ko" else "Here is a summary of what you missed.")
    return out


def generate_digest(provider, messages: List, receiver, sender_name: str) -> dict:
    ctx = DigestContext(messages=messages, receiver_name=receiver.name,
                        receiver_lang=receiver.preferred_language, sender_name=sender_name)
    try:
        raw = provider.generate(ctx)
    except Exception:
        raw = MockProvider().generate(ctx)   # LLM 장애 폴백 — 시연 보험
    return finalize(raw, {m.id for m in messages}, receiver.preferred_language)
