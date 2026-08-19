# POOM Backend Starter

POOM + AI Relay(시차 단절 해소) 해커톤 백엔드. FastAPI 단일 서버 · 단일 저장소(api/ai 모듈 분리) 구조이며,
로컬은 SQLite, 배포는 PostgreSQL(Supabase)로 동작한다.

## 빠른 시작

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
pytest -q                            # 8건 = 엔진 검증 + 5단계 데모 리허설
```

## 구조

```
app/
  config.py            # 확정 파라미터(초기 100c, 임계 3h 등) — 합의값 변경은 여기서만
  timeutil.py          # get_now(actor): 모든 시간 계산의 단일 관문(데모 모드의 기반)
  contract.py          # 내부 표현 ↔ API 계약 v2의 유일한 변환 경계(응답 직렬화 시점)
  models.py            # 도메인 모델(잔액 컬럼 없음 — 원장 합산 원칙)
  engines/
    status.py          # Timezone Status — 순수 함수(근무/수면/출근예정/자리비움 + 예상 응답 시각)
    relay.py           # 릴레이 트리거 — 지연 평가(접속 시 조건 검사, 크론 없음)
    ledger.py          # 원장: hold/release/refund, 이중 정산 DB 제약으로 차단
    digest.py          # 6필드 다이제스트 + grounding 게이트 + Mock/OpenAI 프로바이더
  routers/
    users.py           # 가입(+100c)·프로필·매칭(겹침 시간 정렬)·상태(프라이버시 규칙)
    collabs.py         # /projects — 협업 상태 머신·메시지·다이제스트·크레딧·리뷰(동시 공개)
    demo.py            # 데모 모드(가상 시각)·시연 시드
schema.sql             # Supabase/PostgreSQL DDL (+ user_balances 뷰)
docs/api_spec_v2.md    # API 계약 기준본(canonical) — 코드가 이 문서와 1:1로 일치한다
prompts/digest_prompt.md  # 백엔드 B용 실프롬프트 규칙
tests/test_all.py      # 단위 + 데모 리허설 통합 테스트
```

## 팀 온보딩

**백엔드 B (AI 엔진)** — 교체 지점은 `app/engines/digest.py`의 `OpenAIProvider.generate()` 하나다.
`build_prompt()`와 `prompts/digest_prompt.md` 규칙대로 LangChain 체인을 연결하고 dict를 반환하면,
grounding 게이트(`finalize`)와 장애 시 Mock 폴백은 이미 동작한다. `LLM_PROVIDER=openai` 환경변수로 전환.

**프론트엔드** — 모든 경로에 `/api/v1` 프리픽스가 붙는다(예외: `GET /health`).
인증은 `X-User-Id` 헤더, 채팅은 `GET /api/v1/projects/{id}/messages` 3~5초 폴링.
채팅방 진입 시 `GET /api/v1/projects/{id}/relay-digest`를 한 번 호출하면 자동 생성 로직이
서버에서 처리된다. 다이제스트 항목의 `source_ids`는 원문 메시지 점프 링크로 렌더링한다.
전체 계약은 `docs/api_spec_v2.md`를 본다.

**Supabase 전환** — `schema.sql` 실행 → `DATABASE_URL` 교체 → 인증은 `app/deps.py`의
`get_current_user`만 JWT 검증으로 바꾸면 끝난다.

## 데모 모드 운용 (시연 필수)

시차를 5분 안에 보여주기 위한 '가상 세계 시각'. **두 계정에 동일한 시각을 설정하고 함께 전진**시킨다.

```bash
curl -X POST /api/v1/demo/seed               # 한↔미 시나리오 생성, 5단계 가이드 반환
curl -X POST /api/v1/demo/time -d '{"user_ids": ["<kr>", "<us>"], "now": "2026-08-20T11:00:00Z"}'
# now: null 을 보내면 실시간으로 복귀
```

시연 리허설의 정답지는 `tests/test_all.py::test_demo_flow_end_to_end` — 매칭 → 합의(60c 잠금) →
시차 수면 → 부재 중 메시지 → 기상 즉시 다이제스트 자동 생성 → 지급(40c/160c) → 상호 평가 동시 공개까지
API 호출 순서 그대로 코드화되어 있다.

## 보안·배포 주의 (공개 저장소일 경우 필독)

- `/api/v1/demo/time`, `/api/v1/demo/seed`는 **인증 없는 시연 전용 백도어**다. 계정의 '현재 시각'을 바꾸고
  데이터를 생성할 수 있으므로, 실제 배포 시에는 라우터 등록을 제거하거나 관리자 인증을 걸 것
  (`app/main.py`에서 `demo.router` 한 줄 제거로 차단된다).
- `X-User-Id` 헤더 인증은 해커톤용 간이 방식이며 위조가 가능하다. 공개 서비스 전에는
  `app/deps.py`의 `get_current_user`를 Supabase Auth(JWT 검증)로 반드시 교체할 것.
- 실제 LLM 키는 `.env`에만 두고 커밋하지 않는다(`.env.example` 참고).

## 확정 파라미터 (config.py)

| 항목 | 값 |
|---|---|
| 초기 지갑 | 100c (10c ≈ 표준 1시간 상당) |
| 견적 | 건당 확정, 합의 시 hold → 양측 완료 확인 시 release |
| 무응답 임계 | 3시간 (수신자 접속 시 지연 생성) |
| 다이제스트 | 6필드 + 항목별 source_ids(근거 필수), 수신자 모국어 |
| 상태 판정 | working / sleeping / soon(출근 ≤3h) / away |
