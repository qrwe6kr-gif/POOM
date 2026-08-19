# 핵심 REST API 명세서 v2 (수정판)

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
  "last_active_at": "2026-08-18T11:30:00Z",
  "last_active_hours_ago": 4.5
}
```

- `status_label`은 **조회자**의 preferred_language로 생성한다(초안의 `_ko` 고정 접미사 제거).
- **[추가] `next_response_utc`** — 다음 근무 시작 = 예상 응답 가능 시각. 채팅 헤더의 핵심 정보다.

---

## ② 매칭 & 크레딧 협업 API

`GET /api/v1/matching` — (초안 누락) 내 필요 역량 ↔ 상대 주특기 교차 매칭, **오늘 근무 겹침 시간(overlap_hours)** 내림차순.

`POST /api/v1/projects` — 협업 요청 생성. body: worker_id, title, agreed_credits(**기본값 없음 — 합의값을 명시**), deadline(선택, ISO8601). 상태 `MATCHED`.

`GET /api/v1/projects/{project_id}` — 협업방 단건 상세(제목·작업 목표·마감일·참여자·내 역할) — 협업방 헤더 렌더링용.

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
  "created_at": "2026-08-18T11:40:00Z"
}
```

- `verified: false`는 LLM이 근거를 제공하지 않은 항목(UI에 '미확인' 배지). 존재하지 않는 메시지를
  근거로 주장한 항목은 서버가 폐기한다.
- 프론트 규칙: `source_ids`는 해당 원문 메시지로 점프하는 링크로 렌더링한다.
- `tone_cushioned_message`는 **'추천 답변'** — 수신자가 편집해 그대로 전송할 수 있는 답장 초안이며,
  답장 입력창에 프리필한다.
- **확인 완료 규칙** — 수신자가 협업방에 답변을 전송하면 해당 다이제스트는 `is_read: true`
  (확인 완료)로 전환된다. 별도 호출이 필요 없다.

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
