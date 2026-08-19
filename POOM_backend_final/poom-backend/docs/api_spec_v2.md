# 핵심 REST API 명세서 v2 (수정판)

팀 초안의 경로·네이밍(`/api/v1`, projects, worker, relay-digest)을 유지하되,
에스크로 단계 누락·다이제스트 구조·데모 방식의 결함을 수정한 판이다.
DB 스키마 v2와 정합하며, 명세된 동작은 전부 서버 코드로 구현·테스트되어 있다.

> **이 문서가 계약의 기준본(canonical)이다.** 서버 코드는 이 문서와 1:1로 일치한다.
> 내부 구현은 Collab/provider 네이밍을 유지하지만, 외부로 나가는 경로와 JSON 키는
> 전부 `app/contract.py` 경계에서 이 문서의 v2 네이밍으로 변환된다.
> 경로·키를 바꾸면 같은 커밋에서 이 문서와 `팀공유_README_먼저보기.md`를 함께 갱신한다.

## 공통 규약 (초안에 누락 — 신설)

- **베이스 경로**: 모든 엔드포인트는 `/api/v1` 프리픽스를 갖는다. 예외는 인프라용 `GET /health` 하나다.
- **인증**: 모든 보호 엔드포인트는 헤더 `X-User-Id: <id>` 를 요구한다 (해커톤 간이 방식, 추후 JWT 교체).
  `POST /api/v1/auth/signup`, `POST /api/v1/auth/login`, 데모 API는 무인증이다.
- **오류**: `401` 인증 없음 · `403` 권한 없음(비참여자, 상태 조회 제한) · `404` 대상 없음 ·
  `400` 규칙 위반(잔액 부족, 이중 정산, 상태 전이 불가 — `detail`에 사유).
- **식별자**: user_id · project_id는 32자 hex 문자열. message_id · digest_id는 정수.
- **시각**: 모든 datetime은 UTC ISO8601(offset 포함)로 내보낸다.
- **프로젝트 상태**: `MATCHED` → `IN_PROGRESS` → `COMPLETED` / `CANCELLED`.

---

## ① 유저 및 Timezone Status API

`POST /api/v1/auth/signup` — (초안 누락) 가입 + **SIGNUP_BONUS 100c 지급**.

- body: `name`, `email`, `country`(선택), `timezone`(기본 Asia/Seoul),
  `preferred_language`(기본 ko), `work_start`(기본 9), `work_end`(기본 18)
- Response `200`: `{ "user_id": "…", "note": "…" }` · 이메일 중복은 `400`.

`POST /api/v1/auth/login` — (초안 누락) **비밀번호 없는 해커톤 간이 로그인.**
이메일로 계정을 찾아, 프론트가 이후 `X-User-Id` 헤더에 넣을 값을 돌려준다.

- body: `email`
- Response `200`: `{ "user_id": "…", "name": "지호", "preferred_language": "ko" }`
  — 로그인 직후 화면 인사말과 언어 설정에 바로 쓸 수 있도록 이름·언어를 함께 준다.
- 등록되지 않은 이메일은 `404`(`detail`에 사유).
- 비밀번호가 없으므로 신원 증명이 아니다. 실서비스 전환 시 signup·login·`get_current_user`를
  한 벌로 Supabase Auth(JWT)로 교체한다.

`GET /api/v1/users/{user_id}/status`

- **[수정] 판정 로직** — 초안의 "timezone과 simulated_last_active_at 기반"은 오류다.
  WORKING / SLEEPING / STARTING_SOON은 **근무·수면 시간창**(work_start~end, sleep_start~end 기본 23~07)과
  현지 시각으로 판정한다. last_active는 상태의 근거가 아니라 "마지막 활동 N시간 전" 표시용 보조 정보다.
- **[추가] 권한** — 본인 또는 협업 관계가 있는 상대만 조회 가능(403). 수면 패턴 노출은 프라이버시 사안이다.
- Response `200`:

```json
{
  "user_id": "4c60b48b…", "name": "Alex", "timezone": "America/Los_Angeles",
  "local_time": "03:45 AM",
  "status": "SLEEPING",
  "status_label": "비근무",
  "next_response_utc": "2026-08-18T16:00:00+00:00",
  "last_active_at": "2026-08-18T11:30:00+00:00",
  "last_active_hours_ago": 4.5
}
```

- **status 4값** — `WORKING` · `SLEEPING` · `STARTING_SOON`(출근 ≤3h) · **`AWAY`**.
  **[추가] `AWAY`** — 근무 시간도 수면 시간도 아닌 구간(예: 서울 20:00)이다. 초안·v2 초판이
  이 상태를 빠뜨렸으나 시간창 판정상 반드시 발생하므로 계약에 포함한다.
- `status_label`은 **조회자**의 preferred_language로 생성한다(초안의 `_ko` 고정 접미사 제거).

  | status | ko | en |
  |---|---|---|
  | WORKING | 업무 가능 | Available |
  | SLEEPING | 비근무 | Off hours |
  | STARTING_SOON | 근무 시작 예정 | Starting soon |
  | AWAY | 자리 비움 | Away |

- **[추가] `next_response_utc`** — 다음 근무 시작 = 예상 응답 가능 시각. 채팅 헤더의 핵심 정보다.
  status가 `WORKING`이면 `null`.
- `local_time`은 12시간제 `"HH:MM AM|PM"` 표기다.

`GET /api/v1/me` — 내 프로필 + `is_pro`.

`GET /api/v1/users/{user_id}` — 상대 프로필. 프로필 스키마는 공통이다:

```json
{ "user_id": "…", "name": "Alex", "country": "US", "timezone": "America/Los_Angeles",
  "preferred_language": "en", "work": [9, 18],
  "skills": [{"role": "design", "level": "mid", "portfolio_url": ""}],
  "needs":  [{"role": "dev", "note": "portfolio site"}] }
```

`POST /api/v1/me/skills` — 주특기 등록. body: `role`, `level`(기본 junior), `portfolio_url`(선택).

`POST /api/v1/me/needs` — 필요 역량 등록. body: `role`, `note`(선택).

`GET /api/v1/matching` — (초안 누락) 내 필요 역량 ↔ 상대 주특기 교차 매칭,
**오늘 근무 겹침 시간(overlap_hours)** 내림차순. 쿼리 `role`로 특정 역할만 필터.

```json
{ "results": [{ "user": { …프로필… }, "matched_role": "design", "overlap_hours": 1.5 }] }
```

needs 미등록 시 `{ "results": [], "note": "…" }`.

---

## ② 매칭 & 크레딧 협업 API

`POST /api/v1/projects` — 협업 요청 생성. 상태 `MATCHED`.

- body: `worker_id`, `title`, `scope`(선택), `agreed_credits`(**기본값 없음 — 합의값을 명시**),
  `deadline`(선택, ISO8601)
- Response: `{ "project_id": "…", "status": "MATCHED" }` · `agreed_credits ≤ 0`은 `400`.

`GET /api/v1/projects/{project_id}` — 협업방 단건 상세 — 협업방 헤더 렌더링용.

```json
{ "project_id": "…", "title": "로고+키비주얼", "scope": "모바일 메인 화면 시안",
  "status": "IN_PROGRESS", "agreed_credits": 60,
  "deadline": "2026-08-21T18:00:00+00:00",
  "participants": [{"user_id": "…", "name": "지호", "timezone": "Asia/Seoul",
                    "country": "KR", "role": "requester"},
                   {"user_id": "…", "name": "Alex", "timezone": "America/Los_Angeles",
                    "country": "US", "role": "worker"}],
  "my_role": "requester" }
```

`GET /api/v1/projects` — 내가 참여 중인 협업 목록.

```json
{ "projects": [{ "project_id": "…", "title": "…", "status": "IN_PROGRESS",
                 "agreed_credits": 60, "my_role": "worker", "partner_id": "…" }] }
```

`POST /api/v1/projects/{project_id}/accept` — **[신설 · 필수]** 작업자 수락.

- 초안에는 수락 단계가 없어 일방 생성만으로 계약이 성립하고, **에스크로가 발생할 시점 자체가 없다.**
- 수락 순간 의뢰자 크레딧이 **HOLD(잠금)** 되고 상태가 `IN_PROGRESS`로 전이된다. 잔액 부족 시 `400`.
- 호출자가 worker가 아니면 `403`, 상태가 `MATCHED`가 아니면 `400`.
- Response: `{ "project_id": "…", "status": "IN_PROGRESS", "escrow_held": 60 }`

`POST /api/v1/projects/{project_id}/complete` — 완료 확인. **양측 모두 확인되는 순간 RELEASE(지급)**.

- **[수정] 응답에서 상대방 잔액 제거** — 초안의 `requester_balance`/`worker_balance` 동시 노출은
  타인 잔액 공개로 프라이버시 위반이다. 정산 사실과 **호출자 본인 잔액만** 반환한다.
- `confirmed`는 양측 확인 진행 상황이다(한쪽만 눌린 상태를 UI에 표시하기 위함).
  미정산 상태에서는 `settled: false`, `released_credits: 0`, `status: "IN_PROGRESS"`.

```json
{ "project_id": "…", "status": "COMPLETED", "settled": true,
  "released_credits": 60, "my_balance": 160,
  "confirmed": { "requester": true, "worker": true } }
```

`POST /api/v1/projects/{project_id}/cancel` — (초안 누락) 취소. IN_PROGRESS였다면 **REFUND(반환)**.

- Response: `{ "project_id": "…", "status": "CANCELLED" }` · 이미 COMPLETED면 `400`.

`GET /api/v1/me/credits` — (초안 누락) 잔액(원장 합산) + 거래 내역.

```json
{ "balance": 40,
  "transactions": [{ "id": 1, "amount": 100, "type": "SIGNUP_BONUS", "project_id": null },
                   { "id": 3, "amount": -60, "type": "HOLD", "project_id": "…" }] }
```

`type`은 `SIGNUP_BONUS` · `TOPUP` · `HOLD` · `RELEASE` · `REFUND`.
잔액 컬럼은 존재하지 않는다 — 항상 이 원장의 합이다.

`POST · GET /api/v1/projects/{project_id}/reviews` — (초안 누락) 상호 평가. 양측 제출 시 동시 공개.

- POST body: `diligence`, `quality`, `communication`(각 1~5), `comment`(선택).
  COMPLETED 상태에서만 가능(`400`), 1인 1회(`400`).
- GET: 한쪽만 제출했으면 `{ "visible": false, "submitted": ["<user_id>"] }`,
  양측 제출 시 `{ "visible": true, "reviews": [ … ] }`.

---

## ③ 채팅 & AI Relay 다이제스트 API

`POST /api/v1/projects/{project_id}/messages` — 메시지 전송.

- body: `body` · Response: `{ "message_id": 42, "created_at": "…" }`
- 전송 시 **내게 온 미확인 다이제스트가 자동으로 `is_read: true`로 전환**된다(아래 확인 완료 규칙).

`GET /api/v1/projects/{project_id}/messages` — (초안 누락) 폴링 조회(3~5초). 조회 시 수신분 읽음 처리.

```json
{ "messages": [{ "message_id": 42, "sender_id": "…", "body": "…",
                 "created_at": "2026-08-18T11:30:00+00:00", "mine": false }] }
```

`GET /api/v1/projects/{project_id}/relay-digest`

- 지연 평가: 접속 시 조건(미커버 메시지 ∧ 마지막 발화자 ≠ 나 ∧ 경과 ≥ 3h) 충족이면 **그 자리에서 생성**.
  GET에 생성 부수효과가 있음을 명세에 명시한다. 수동 "요약 받기"는 `POST /api/v1/projects/{project_id}/relay-digest`(경과 무관).
- **[수정] 다이제스트 필드는 문자열이 아니라 항목 배열이다.** 초안처럼 `"decisions": "…확정되었습니다."`
  단일 문자열로 평탄화하면 ① 결정이 여러 건일 때 표현 불가 ② **항목별 근거(source_ids)가 사라져
  원문 점프 검증(환각 방어)이 무너진다.** ③ `covers_to_message_id`가 없으면 접속마다 전체 대화를
  재요약(LLM 비용 폭발)하고 중복 생성을 막을 수 없다.

```json
{
  "digest_id": 101, "project_id": "…", "language": "en",
  "trigger": "auto", "generated": true, "is_read": false,
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
  "created_at": "2026-08-18T11:40:00+00:00"
}
```

- **응답 키 집합은 항상 동일하다.** 다이제스트가 아직 없으면 `digest_id`·`language`·`trigger`·
  `covers_to_message_id`·`digest`·`created_at`이 `null`, `is_read`·`generated`가 `false`로 채워져
  내려온다. 프론트에 키 존재 여부 분기가 필요 없다.
- `trigger`는 `"auto"`(지연 평가 발동) 또는 `"manual"`(POST 호출).
- `unread_message_count` — **이 응답이 다루는 미커버 메시지 수**. 생성된 경우 이번 다이제스트가
  커버한 메시지 수, 생성되지 않은 경우 아직 어떤 다이제스트에도 포함되지 않은 메시지 수다.
- `action_items` 항목은 `assignee`·`deadline` 보조 필드를 추가로 가질 수 있다(프롬프트 출력에 따름).
- `verified: false`는 LLM이 근거를 제공하지 않은 항목(UI에 '미확인' 배지). 존재하지 않는 메시지를
  근거로 주장한 항목은 서버가 폐기한다.
- 프론트 규칙: `source_ids`는 해당 원문 메시지로 점프하는 링크로 렌더링한다.
- `tone_cushioned_message`는 **'추천 답변'** — 수신자가 편집해 그대로 전송할 수 있는 답장 초안이며,
  답장 입력창에 프리필한다.
- **확인 완료 규칙** — 수신자가 협업방에 답변을 전송하면 해당 다이제스트는 `is_read: true`
  (확인 완료)로 전환된다. 별도 호출이 필요 없다.

`POST /api/v1/projects/{project_id}/relay-digest` — 수동 "요약 받기". 경과 시간 조건 없이
미커버 메시지가 있으면 생성한다. 미커버 메시지가 없으면 `generated: false`와
`"note": "no new messages"`를 붙여 직전 다이제스트를 그대로 반환한다.

---

## ④ [심사 시연 전용] 데모 API

`POST /api/v1/demo/time` — **[교체]** 초안의 `override-time`(hours_ago로 활동 시간 되돌리기)은
릴레이 트리거는 흉내 내지만 **SLEEPING 상태를 만들 수 없다** — 수면 판정은 활동 시각이 아니라
현지 '현재 시각' 기반이기 때문이다. 시연 시나리오 3단계("상태가 Sleep으로 전환")가 재현 불가능해진다.
대신 **가상 세계 시각**을 두 계정에 동일하게 설정·전진시키는 방식을 쓴다(상태·경과·트리거가 전부
일관되게 이동하며, 테스트로 검증되어 있다).

```json
{ "user_ids": ["<kr_id>", "<us_id>"], "now": "2026-08-20T11:00:00Z" }   // null이면 실시간 복귀
```

`POST /api/v1/demo/seed` — 한국 개발자 ↔ 미국 서부 디자이너 시연 데이터 생성, 5단계 가이드 반환.

```json
{ "kr_user_id": "…", "us_user_id": "…", "project_id": "…",
  "virtual_now": "…", "demo_steps": ["1) …", "…"] }
```

> 배포 시 데모 라우터는 제거하거나 관리자 인증을 건다(무인증 백도어).
> 단 해커톤 기간에는 심사 시연에 필요하므로 배포본에도 포함한다.

---

## ⑤ 인프라

`GET /health` — `{ "ok": true }`. **`/api/v1` 프리픽스 밖**의 유일한 엔드포인트로,
로드밸런서·배포 플랫폼(Railway/Render)의 헬스체크용이다.
