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
  models.py            # 도메인 모델 = docs/schema_v2.sql (잔액 컬럼 없음 — 원장 합산 원칙)
  engines/
    status.py          # Timezone Status — 순수 함수(근무/수면/출근예정/자리비움 + 예상 응답 시각)
    relay.py           # 릴레이 트리거 — 지연 평가(접속 시 조건 검사, 크론 없음)
    ledger.py          # 원장: HOLD/RELEASE/REFUND, 이중 정산 DB 제약으로 차단
    digest.py          # 6필드 다이제스트 + grounding 게이트 + Mock/OpenAI 프로바이더
  routers/
    users.py           # 가입(+100c)·프로필·매칭(겹침 시간 정렬)·상태(프라이버시 규칙)
    collabs.py         # /projects — 협업 상태 머신·메시지·다이제스트·크레딧·리뷰(동시 공개)
    demo.py            # 데모 모드(가상 시각)·시연 시드
docs/schema_v2.sql     # DB 스키마 기준본(canonical) — app/models.py와 컬럼 단위 1:1
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
# 배포 서버에서는 위 두 호출에 -H "X-Demo-Key: <DEMO_KEY>" 를 붙인다 (로컬은 불필요)
curl -X POST /api/v1/demo/time -d '{"user_ids": ["<kr>", "<us>"], "now": "2026-08-20T11:00:00Z"}'
# now: null 을 보내면 실시간으로 복귀
```

시연 리허설의 정답지는 `tests/test_all.py::test_demo_flow_end_to_end` — 매칭 → 합의(60c 잠금) →
시차 수면 → 부재 중 메시지 → 기상 즉시 다이제스트 자동 생성 → 지급(40c/160c) → 상호 평가 동시 공개까지
API 호출 순서 그대로 코드화되어 있다.

## 배포 (Railway 기준)

Railway는 Dockerfile 없이도(Nixpacks) 뜨지만, 저장소의 `Dockerfile`이 있으면 그것을 쓴다.
어느 쪽이든 시작 커맨드는 동일하다 — 플랫폼이 주입하는 `PORT`로 바인딩한다.

1. **레포 연결** — Railway에서 New Project → Deploy from GitHub repo → 이 저장소 선택.
   루트 디렉터리를 `poom-backend`로 지정한다(레포 루트가 아니라면).
2. **PostgreSQL 추가** — 같은 프로젝트에 New → Database → Add PostgreSQL.
   붙이면 `DATABASE_URL`이 서비스에 **자동 주입**된다. 값을 직접 적을 필요는 없다.
   Railway가 주는 `postgres://` 접두사는 `app/config.py`가 `postgresql+psycopg://`로
   자동 변환하므로 그대로 두면 된다.
3. **환경변수 설정** — Variables 탭에 아래 둘만 추가한다.

   | 키 | 값 | 비고 |
   |---|---|---|
   | `FRONTEND_ORIGIN` | 프론트 배포 도메인 (예: `https://poom.vercel.app`) | CORS 허용 목록에 추가된다. `http://localhost:3000`은 코드에 이미 있다 |
   | `LLM_PROVIDER` | `mock` | 실제 LLM 연결 전까지는 mock. 시연은 mock으로도 전부 동작한다 |
   | `DEMO_KEY` | 임의의 긴 문자열 | `/api/v1/demo/*` 보호. 설정하면 `X-Demo-Key` 헤더 일치를 요구한다. **배포에는 반드시 설정** |

   `DATABASE_URL`은 2단계에서 자동으로 들어온다. `OPENAI_API_KEY`는 실제 모델을 붙일 때만 넣는다.
4. **배포 확인** — 첫 배포에서 `init_db()`가 PostgreSQL에 테이블을 생성한다
   (별도 마이그레이션 명령 없음). 아래 curl 3종으로 확인한다.

### 배포 직후 검증 (curl 3종)

`$BASE`를 배포 도메인으로 두고 순서대로 실행한다.

```bash
BASE=https://<your-app>.up.railway.app
DEMO_KEY=<Variables에 넣은 값>

# 1) 살아 있는가
curl -s $BASE/health
# → {"ok":true}

# 2) DB 쓰기·읽기가 되는가 (시드 생성 — 유저 2명·프로젝트 1건·메시지 5건 + 60c HOLD)
curl -s -X POST $BASE/api/v1/demo/seed -H "X-Demo-Key: $DEMO_KEY"
# → {"kr_user_id":"...","us_user_id":"...","project_id":"...","virtual_now":"...","demo_steps":[...]}

# 3) AI Relay 다이제스트가 생성되는가 (위 응답의 us_user_id / project_id 사용)
curl -s -X POST $BASE/api/v1/projects/<project_id>/relay-digest -H "X-User-Id: <us_user_id>"
# → {"generated":true, "digest":{"summary":[...],"decisions":[...],...}, ...}
#    decisions가 비어 있지 않고 각 항목에 source_ids가 있으면 전 파이프라인 정상.
```

3번이 통과하면 원장(HOLD)·메시지·다이제스트 생성·근거 검증까지 한 번에 확인된 것이다.
CORS는 별도로 한 번 확인한다 — `FRONTEND_ORIGIN`을 설정한 뒤 그 도메인으로 preflight를 보내
`access-control-allow-origin`이 돌아오는지 본다.

```bash
curl -i -X OPTIONS $BASE/api/v1/me -H "Origin: https://poom.vercel.app" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: X-User-Id"
```

> 데모 라우터(`/api/v1/demo/*`)는 **해커톤 기간 한정으로 배포본에 포함**한다.
> 심사 시연에 필요하기 때문이며, 해커톤 종료 후에는 아래 '보안·배포 주의'대로 제거한다.

## 보안·배포 주의 (공개 저장소일 경우 필독)

- `/api/v1/demo/time`, `/api/v1/demo/seed`는 **시연 전용 백도어**다. 계정의 '현재 시각'을 바꾸고
  데이터를 생성할 수 있다. 해커톤 기간에는 심사 시연에 필요하므로 배포본에 포함하되,
  **배포 환경에는 `DEMO_KEY`를 반드시 설정**한다(설정 시 `X-Demo-Key` 헤더 일치 요구, 403).
  이는 최소 보호일 뿐이며 **해커톤 종료 후에는 라우터 등록 자체를 제거할 것**
  (`app/main.py`에서 `demo.router` 한 줄 제거로 차단된다).
- `X-User-Id` 헤더 인증은 해커톤용 간이 방식이며 위조가 가능하다. 공개 서비스 전에는
  `app/deps.py`의 `get_current_user`를 Supabase Auth(JWT 검증)로 반드시 교체할 것.
- 실제 LLM 키는 `.env`에만 두고 커밋하지 않는다(`.env.example` 참고).

## 확정 파라미터 (config.py)

| 항목 | 값 |
|---|---|
| 초기 지갑 | 100c (10c ≈ 표준 1시간 상당) |
| 견적 | 건당 확정, 수락 시 HOLD → 양측 완료 확인 시 RELEASE |
| 무응답 임계 | 3시간 (수신자 접속 시 지연 생성) |
| 다이제스트 | 6필드 + 항목별 source_ids(근거 필수), 수신자 모국어 |
| 상태 판정 | WORKING / SLEEPING / STARTING_SOON(출근 ≤3h) / AWAY |
