# POOM 백엔드 — 팀 공유 문서 (통합본)

코드는 GitHub 저장소로 공유하며, 문서는 본 파일 하나로 전달한다.
구성: 빠른 시작 → 역할별 안내 → API 명세 v2 → DB 스키마 v2 → AI 프롬프트 규칙 → 시연 가이드.

---

## 0. 빠른 시작

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
# 브라우저: http://127.0.0.1:8000/docs  (Swagger에서 전 API 클릭 실행 가능)
pytest -q   # 8건 통과가 정상 — 5단계 시연 리허설이 테스트로 코드화되어 있음
```

## 1. 역할별 안내

**프론트엔드** — 인증은 `X-User-Id` 헤더(가입 응답의 user_id). 채팅은 `GET /messages` 3~5초 폴링.
채팅방 진입 시 `GET /relay-digest` 1회 호출(자동 생성은 서버가 판단). 다이제스트 각 항목의
`source_ids`는 원문 메시지로 점프하는 링크로 렌더링한다. 상세는 아래 2장.

**백엔드 B (AI)** — 교체 지점은 `app/engines/digest.py`의 `OpenAIProvider.generate()` 하나다.
아래 4장의 프롬프트 규칙대로 LangChain 체인을 연결해 dict를 반환하면, 키 이름 차이 흡수(어댑터)·
근거 검증(환각 게이트)·장애 시 Mock 폴백이 이미 동작한다. 전환은 환경변수 `LLM_PROVIDER=openai`.

**기획·발표** — 시연은 `/demo/seed` 1회 + `/demo/time`(가상 시각 전진)으로 5단계를 재현한다(5장).
크레딧 질의 대응 논리는 별도 설명서(PDF) 참조.

---

## 2. # 핵심 REST API 명세서 v2 (수정판)

팀 초안의 경로·네이밍(`/api/v1`, projects, worker, relay-digest)을 유지하되,
에스크로 단계 누락·다이제스트 구조·데모 방식의 결함을 수정한 판이다.
DB 스키마 v2와 정합하며, 명세된 동작은 전부 서버 코드로 구현·테스트되어 있다.

## 공통 규약 (초안에 누락 — 신설)

- **인증**: 모든 보호 엔드포인트는 헤더 `X-User-Id: <id>` 를 요구한다 (해커톤 간이 방식, 추후 JWT 교체).
- **오류**: `401` 인증 없음 · `403` 권한 없음(비참여자, 상태 조회 제한) · `404` 대상 없음 ·
  `400` 규칙 위반(잔액 부족, 이중 정산, 상태 전이 불가 — `detail`에 사유).

---

## ① 유저 및 Timezone Status API

`POST /api/v1/auth/signup` — (초안 누락) 가입 + **SIGNUP_BONUS 100c 지급**. body: name, email, timezone, preferred_language, work_start, work_end

`GET /api/v1/users/{user_id}/status`

- **[수정] 판정 로직** — 초안의 "timezone과 simulated_last_active_at 기반"은 오류다.
  WORKING / SLEEPING / STARTING_SOON은 **근무·수면 시간창**(work_start~end, sleep_start~end 기본 23~07)과
  현지 시각으로 판정한다. last_active는 상태의 근거가 아니라 "마지막 활동 N시간 전" 표시용 보조 정보다.
- **[추가] 권한** — 본인 또는 협업 관계가 있는 상대만 조회 가능(403). 수면 패턴 노출은 프라이버시 사안이다.
- Response `200`:

```json
{
  "user_id": 2, "name": "Alex", "timezone": "America/Los_Angeles",
  "local_time": "03:45 AM",
  "status": "SLEEPING",
  "status_label": "수면 중 (답장이 늦어질 수 있습니다)",
  "next_response_utc": "2026-08-18T16:00:00Z",
  "last_active_hours_ago": 4.5
}
```

- `status_label`은 **조회자**의 preferred_language로 생성한다(초안의 `_ko` 고정 접미사 제거).
- **[추가] `next_response_utc`** — 다음 근무 시작 = 예상 응답 가능 시각. 채팅 헤더의 핵심 정보다.

---

## ② 매칭 & 크레딧 협업 API

`GET /api/v1/matching` — (초안 누락) 내 필요 역량 ↔ 상대 주특기 교차 매칭, **오늘 근무 겹침 시간(overlap_hours)** 내림차순.

`POST /api/v1/projects` — 협업 요청 생성. body: worker_id, title, agreed_credits(**기본값 없음 — 합의값을 명시**). 상태 `MATCHED`.

`POST /api/v1/projects/{project_id}/accept` — **[신설 · 필수]** 작업자 수락.

- 초안에는 수락 단계가 없어 일방 생성만으로 계약이 성립하고, **에스크로가 발생할 시점 자체가 없다.**
- 수락 순간 의뢰자 크레딧이 **HOLD(잠금)** 되고 상태가 `IN_PROGRESS`로 전이된다. 잔액 부족 시 `400`.
- Response: `{ "status": "IN_PROGRESS", "escrow_held": 60 }`

`POST /api/v1/projects/{project_id}/complete` — 완료 확인. **양측 모두 확인되는 순간 RELEASE(지급)**.

- **[수정] 응답에서 상대방 잔액 제거** — 초안의 `requester_balance`/`worker_balance` 동시 노출은
  타인 잔액 공개로 프라이버시 위반이다. 정산 사실과 **호출자 본인 잔액만** 반환한다.

```json
{ "project_id": 1, "status": "COMPLETED", "settled": true,
  "released_credits": 60, "my_balance": 160 }
```

`POST /api/v1/projects/{project_id}/cancel` — (초안 누락) 취소. IN_PROGRESS였다면 **REFUND(반환)**.

`GET /api/v1/me/credits` — (초안 누락) 잔액(원장 합산) + 거래 내역(SIGNUP_BONUS/TOPUP/HOLD/RELEASE/REFUND).

`POST · GET /api/v1/projects/{project_id}/reviews` — (초안 누락) 상호 평가. 양측 제출 시 동시 공개.

---

## ③ 채팅 & AI Relay 다이제스트 API

`POST /api/v1/projects/{project_id}/messages` — 메시지 전송.

`GET /api/v1/projects/{project_id}/messages` — (초안 누락) 폴링 조회(3~5초). 조회 시 수신분 읽음 처리.

`GET /api/v1/projects/{project_id}/relay-digest`

- 지연 평가: 접속 시 조건(미커버 메시지 ∧ 마지막 발화자 ≠ 나 ∧ 경과 ≥ 3h) 충족이면 **그 자리에서 생성**.
  GET에 생성 부수효과가 있음을 명세에 명시한다. 수동 "요약 받기"는 `POST /relay-digest`(경과 무관).
- **[수정] 다이제스트 필드는 문자열이 아니라 항목 배열이다.** 초안처럼 `"decisions": "…확정되었습니다."`
  단일 문자열로 평탄화하면 ① 결정이 여러 건일 때 표현 불가 ② **항목별 근거(source_ids)가 사라져
  원문 점프 검증(환각 방어)이 무너진다.** ③ `covers_to_message_id`가 없으면 접속마다 전체 대화를
  재요약(LLM 비용 폭발)하고 중복 생성을 막을 수 없다.

```json
{
  "digest_id": 101, "project_id": 1, "language": "en",
  "trigger": "auto", "generated": true,
  "unread_message_count": 8,
  "covers_to_message_id": 42,
  "digest": {
    "summary":       [{"text": "…", "source_ids": [35, 40], "verified": true}],
    "decisions":     [{"text": "메인 컬러는 #2563eb로 확정", "source_ids": [37], "verified": true}],
    "pending":       [{"text": "…", "source_ids": [39], "verified": true}],
    "key_questions": [{"text": "…?", "source_ids": [41], "verified": true}],
    "action_items":  [{"text": "Figma Header 프레임 내보내기", "source_ids": [40], "verified": true}],
    "tone_cushioned_message": "시차가 있어 푹 쉬고 오셨길 바랍니다! …"
  },
  "created_at": "2026-08-18T11:40:00Z"
}
```

- `verified: false`는 LLM이 근거를 제공하지 않은 항목(UI에 '미확인' 배지). 존재하지 않는 메시지를
  근거로 주장한 항목은 서버가 폐기한다.
- 프론트 규칙: `source_ids`는 해당 원문 메시지로 점프하는 링크로 렌더링한다.

---

## ④ [심사 시연 전용] 데모 API

`POST /api/v1/demo/time` — **[교체]** 초안의 `override-time`(hours_ago로 활동 시간 되돌리기)은
릴레이 트리거는 흉내 내지만 **SLEEPING 상태를 만들 수 없다** — 수면 판정은 활동 시각이 아니라
현지 '현재 시각' 기반이기 때문이다. 시연 시나리오 3단계("상태가 Sleep으로 전환")가 재현 불가능해진다.
대신 **가상 세계 시각**을 두 계정에 동일하게 설정·전진시키는 방식을 쓴다(상태·경과·트리거가 전부
일관되게 이동하며, 테스트로 검증되어 있다).

```json
{ "user_ids": [1, 2], "now": "2026-08-20T11:00:00Z" }   // null이면 실시간 복귀
```

`POST /api/v1/demo/seed` — 한국 개발자 ↔ 미국 서부 디자이너 시연 데이터 생성, 5단계 가이드 반환.

> 배포 시 데모 라우터는 제거하거나 관리자 인증을 건다(무인증 백도어).


---

## 3. DB 스키마 v2

```sql
-- =====================================================================
-- POOM DB 스키마 v2 (팀 초안 수정판)
-- 팀 초안의 테이블·컬럼 네이밍(projects, worker_id, sent_at 등)을 유지하되,
-- 원장 무결성·다이제스트 구조·시간대 처리의 결함을 수정하였다.
-- 변경 사유는 각 위치에 주석으로 명시한다.
-- =====================================================================

-- 1. 사용자
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Seoul',
    preferred_language VARCHAR(10) NOT NULL DEFAULT 'ko',

    -- [추가] Timezone Status 엔진의 데이터 원천.
    -- timezone만으로는 '근무 중/수면 중/근무 시작 예정' 판정이 불가능하다.
    work_start  SMALLINT NOT NULL DEFAULT 9,
    work_end    SMALLINT NOT NULL DEFAULT 18,
    sleep_start SMALLINT NOT NULL DEFAULT 23,
    sleep_end   SMALLINT NOT NULL DEFAULT 7,

    -- [수정] simulated_last_active_at → 용도 분리.
    -- last_active_at: 실제 접속 기록(프레즌스). demo_now: 데모 모드의 '가상 현재 시각'.
    -- 상태 판정·무응답 경과·다이제스트 트리거가 전부 '현재 시각' 기반이므로,
    -- 시각 하나를 옮기면 전 시스템이 일관되게 시간 이동한다 (검증된 방식).
    last_active_at TIMESTAMPTZ,
    demo_now       TIMESTAMPTZ,

    -- [제거] credit_balance INT DEFAULT 100
    -- 잔액 컬럼과 거래 테이블이 공존하면 진실이 둘이 되어 반드시 어긋난다.
    -- 잔액은 아래 user_balances 뷰(거래 합산)로만 읽는다. 초기 100c는
    -- 가입 시 SIGNUP_BONUS 거래 1행을 넣는 것으로 지급한다.
    created_at TIMESTAMPTZ DEFAULT now()
);

-- [분리] primary_skill/needed_skill 단일 컬럼 → 테이블.
-- 확정 기획이 "주특기 1개 이상"이므로 단일 컬럼은 요구사항 위반이다.
-- MVP에서 1인 1스킬만 쓸 경우 각 테이블에 1행만 넣으면 된다.
CREATE TABLE user_skills (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    skill VARCHAR(100) NOT NULL,               -- e.g., 'Backend', 'UI/UX Design'
    level VARCHAR(20) NOT NULL DEFAULT 'junior',
    portfolio_url VARCHAR(300) NOT NULL DEFAULT ''
);
CREATE INDEX idx_skills_skill ON user_skills(skill);

CREATE TABLE user_needs (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    skill VARCHAR(100) NOT NULL,
    note VARCHAR(300) NOT NULL DEFAULT ''
);

-- 2. 협업(프로젝트)
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    requester_id INT NOT NULL REFERENCES users(id),
    worker_id    INT NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    -- [수정] DEFAULT 100 제거 — 견적은 '건당 확정 합의값'이므로 기본값이 있으면 안 된다.
    agreed_credits INT NOT NULL CHECK (agreed_credits > 0),
    -- [수정] 시작 상태는 MATCHED. 흐름: MATCHED → IN_PROGRESS(수락 = HOLD 발생)
    --        → COMPLETED(양측 확인 = RELEASE) / CANCELLED(REFUND).
    --        초안에는 취소 상태가 없어 환불 경로가 표현 불가였다.
    status VARCHAR(30) NOT NULL DEFAULT 'MATCHED',
    requester_completed BOOLEAN NOT NULL DEFAULT FALSE,
    worker_completed    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_projects_requester ON projects(requester_id);
CREATE INDEX idx_projects_worker    ON projects(worker_id);

-- 3. 채팅 메시지
-- [주의] 시차가 제품 본체인 서비스에서 naive TIMESTAMP는 치명적이다 → 전 컬럼 TIMESTAMPTZ.
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id),
    sender_id  INT NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT now(),
    read_at TIMESTAMPTZ                          -- [추가] 미읽음 표시·릴레이 판정 재료
);
CREATE INDEX idx_messages_project ON messages(project_id, id);

-- 4. AI Relay 다이제스트
CREATE TABLE ai_relay_digests (
    id SERIAL PRIMARY KEY,
    project_id   INT NOT NULL REFERENCES projects(id),
    recipient_id INT NOT NULL REFERENCES users(id),
    language VARCHAR(10) NOT NULL DEFAULT 'ko',
    trigger_type VARCHAR(10) NOT NULL DEFAULT 'auto',   -- auto | manual

    -- [추가·필수] 어느 메시지까지 요약했는지. 이 값이 없으면
    -- ① 접속할 때마다 전체 대화를 재요약(비용 폭발) ② 중복 생성 방지 불가.
    covers_to_message_id INT NOT NULL REFERENCES messages(id),

    -- [수정] 6개 TEXT 컬럼 → JSONB 단일 payload.
    -- TEXT로 평탄화하면 항목별 근거(source_ids)가 사라져
    -- "AI가 결정을 지어내면?"에 대한 방어(원문 점프 검증)가 불가능해진다.
    -- payload 형식: { "summary": [...], "decisions": [{"text","source_ids","verified"}], ... }
    payload JSONB NOT NULL,

    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_digest_lookup ON ai_relay_digests(project_id, recipient_id, id DESC);

-- 5. 크레딧 원장
-- [교체] from/to + status('ESCROWED'→'TRANSFERRED') 구조의 문제:
--   ① 거래 행을 UPDATE로 변조 — 원장은 append-only여야 감사·분쟁 대응이 된다.
--   ② 이중 정산을 막는 제약이 없다.
-- 에스크로의 상태 변화는 갱신이 아니라 '새 행'으로 표현한다:
--   HOLD(잠금, 의뢰자 -N) → RELEASE(지급, 작업자 +N) 또는 REFUND(반환, 의뢰자 +N).
CREATE TABLE credit_transactions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),   -- 이 거래가 반영되는 계정
    amount  INT NOT NULL,                        -- 부호 있는 값 (HOLD는 음수)
    tx_type VARCHAR(20) NOT NULL,                -- SIGNUP_BONUS | TOPUP | HOLD | RELEASE | REFUND
    project_id INT REFERENCES projects(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    -- 프로젝트당 HOLD/RELEASE/REFUND 각 1회 — 이중 지급을 DB 수준에서 차단
    CONSTRAINT uq_tx_project_type UNIQUE (project_id, tx_type)
);
CREATE INDEX idx_tx_user ON credit_transactions(user_id);

-- 잔액 뷰 — 애플리케이션은 반드시 이 뷰(또는 동일 합산)로만 잔액을 읽는다.
CREATE VIEW user_balances AS
    SELECT u.id AS user_id, COALESCE(SUM(t.amount), 0)::INT AS balance
    FROM users u LEFT JOIN credit_transactions t ON t.user_id = u.id
    GROUP BY u.id;

-- 6. [추가] 상호 평가 — 확정 기획의 핵심 기능(간단한 상호 평가)이 초안에 누락됨.
--    양측 제출 시 동시 공개(보복 평가 방지)는 애플리케이션에서 처리.
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    project_id  INT NOT NULL REFERENCES projects(id),
    reviewer_id INT NOT NULL REFERENCES users(id),
    diligence     INT NOT NULL CHECK (diligence BETWEEN 1 AND 5),
    quality       INT NOT NULL CHECK (quality BETWEEN 1 AND 5),
    communication INT NOT NULL CHECK (communication BETWEEN 1 AND 5),
    comment VARCHAR(300) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_review_once UNIQUE (project_id, reviewer_id)
);

-- 운영 메모
-- 1) HOLD 시 잔액 검사와 INSERT는 한 트랜잭션에서 수행하고, 동시성 대비로
--    의뢰자 기준 SELECT ... FOR UPDATE 패턴을 쓸 것.
-- 2) Supabase Auth 도입 시 users.id(SERIAL)는 auth.users(UUID)와 매핑 테이블로 연결.

```

---

## 4. # AI Relay 다이제스트 프롬프트 (근거 연결 반영판)

팀 프롬프트에 **source_ids(근거 메시지 번호)** 규칙만 추가한 버전이다.
키 이름은 서버 어댑터가 흡수하므로 그대로 두어도 되지만, 근거 규칙은 추가해야
심사 즉석 검증(원문 점프)과 환각 차단이 작동한다.

```
System: You are 'POOM SyncRelay AI', an intelligent async collaboration engine.
Given the unread chat history between cross-border makers, generate a structured
digest in the recipient's native language ({preferred_language}).

Chat History (each line is prefixed with its message number):
{chat_history}

Output strict JSON with these 6 keys:
1. "summary": Brief status update (1-2 sentences)
2. "decisions": Confirmed facts/decisions
3. "pending": Items that still require discussion
4. "key_questions": Urgent/key questions the recipient must answer
5. "action_items": Immediate actionable tasks for recipient
6. "tone_cushioned_message": A culturally polite, warm greeting that bridges timezone gaps

GROUNDING RULES (mandatory):
- Each entry in keys 2-5 must be an object:
  {"text": "...", "source_ids": [<message numbers this is based on>]}
- Never state anything that is not present in the chat history.
  If a key has no evidence, return an empty array [].
- Do not infer decisions from ambiguous wording. Only include a decision if a
  message explicitly confirms it.
```

## chat_history 포맷 (서버가 이 형태로 넣는다)
```
[1] alex: Hi! Excited to work on your logo.
[2] jiho: 로고 방향은 다크 네이비로 확정할게요
[3] jiho: 폰트는 아직 고민 중이에요
```

## 서버 측 처리 (app/engines/digest.py — 이미 구현됨)
- `normalize()` : summary/pending/tone_cushioned_message 등 키 이름 차이를 흡수하고,
  문자열 항목도 `{text, source_ids}` 형태로 통일한다.
- `finalize()` : 존재하지 않는 메시지 번호를 근거로 주장하면 **해당 항목 폐기**(환각 차단).
  근거를 아예 제공하지 않은 항목은 유지하되 `verified: false`로 표시한다(UI '미확인' 배지).


---

## 5. 시연 가이드 (5단계)

1. `POST /demo/seed` → 한국 개발자(지호)·미국 디자이너(Alex)·진행 중 협업(60c 잠금)·대화 5건 생성
2. `POST /demo/time` 으로 두 계정의 가상 시각을 +11h 전진 → `GET /users/{us}/status` = SLEEPING
3. 지호가 수면 중인 상대에게 추가 메시지 전송
4. 가상 시각을 +17h 지점으로 전진 → Alex로 `GET /relay-digest` → 접속 순간 다이제스트 자동 생성
   (6필드 · 영어 · 전 항목 근거 연결)
5. 양측 `POST /complete` → 60c 지급(잔액 40/160) → 리뷰 양측 제출 시 동시 공개

주의: `/demo/*`는 인증 없는 시연 전용 기능이므로 실제 배포 시 제거한다(`app/main.py`에서 한 줄).

## 6. 남은 백엔드 작업

① LangChain 실연결(백엔드 B 협업) ② 클라우드 배포(Dockerfile·호스팅 설정)
