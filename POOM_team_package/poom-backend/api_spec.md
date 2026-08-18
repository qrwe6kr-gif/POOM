# POOM Backend — API 명세 (v0.1)

서버 실행 후 `/docs`(Swagger)에서 실시간 명세와 시험 호출이 가능하다. 본 문서는 팀 공유용 요약본이다.

## 인증
- 해커톤 간이 인증: 모든 보호 엔드포인트에 헤더 `X-User-Id: <user_id>` 를 넣는다.
- `user_id`는 `POST /auth/signup` 응답으로 받는다. (실서비스 전환 시 `app/deps.py`만 Supabase Auth로 교체)

## 엔드포인트 요약

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | /auth/signup | 가입 + 초기 지갑 100c 지급. body: name, email, country, tz(IANA), lang, work_start, work_end |
| GET | /me | 내 프로필(스킬·니즈 포함) |
| POST | /me/skills | 주특기 등록 {role, level, portfolio_url} |
| POST | /me/needs | 필요 역량 등록 {role, note} |
| GET | /users/{id} | 상대 프로필 |
| GET | /matching?role= | 내 니즈 ↔ 상대 스킬 매칭, **overlap_hours**(오늘 근무 겹침) 내림차순 |
| GET | /users/{id}/status | **Timezone Status** — state: working·sleeping·soon·away + next_response_utc. 협업 관계가 있는 상대만 조회 가능(403) |
| POST | /collabs | 협업 요청 {provider_id, title, scope, credit_amount(건당 확정 견적)} |
| POST | /collabs/{id}/accept | 공급자 수락 → **의뢰자 크레딧 hold(에스크로 잠금)** → agreed. 잔액 부족 시 400 |
| POST | /collabs/{id}/complete | 완료 확인. 양측 모두 확인되는 순간 **release(지급)** → completed |
| POST | /collabs/{id}/cancel | 취소. agreed 상태였다면 **refund(반환)** |
| GET | /collabs | 내 협업 목록 |
| POST | /collabs/{id}/messages | 메시지 전송 {body} |
| GET | /collabs/{id}/messages | 메시지 목록(폴링 3~5초 권장). 조회 시 수신분 자동 읽음 처리 |
| GET | /collabs/{id}/digest | **AI Relay 다이제스트** — 채팅방 진입 시 호출. 조건 충족 시 그 자리에서 자동 생성(지연 평가) |
| POST | /collabs/{id}/digest | 수동 "요약 받기" — 미커버 메시지가 있으면 즉시 생성 |
| GET | /me/credits | 잔액 + 거래 내역(원천 태그 포함) |
| POST | /collabs/{id}/reviews | 평가 제출 {diligence, quality, communication: 1..5, comment} |
| GET | /collabs/{id}/reviews | 양측 제출 시에만 공개(동시 공개) |
| POST | /demo/time | **데모 모드** — {user_ids: [...], now: ISO or null} 가상 시각 설정/해제 |
| POST | /demo/seed | 한국 개발자 ↔ 미국 디자이너 시연 시나리오 생성, 5단계 진행 가이드 반환 |

## 다이제스트 응답 형태

```json
{
  "generated": true,
  "id": 1, "lang": "en", "trigger": "auto", "covers_to_message_id": 6,
  "digest": {
    "relay_summary":  [{"text": "...", "source_ids": [1]}],
    "decisions":      [{"text": "로고는 다크 네이비로 확정할게요", "source_ids": [2]}],
    "open_items":     [{"text": "...", "source_ids": [3]}],
    "key_questions":  [{"text": "...?", "source_ids": [5]}],
    "action_items":   [{"task": "...", "assignee": "Alex", "deadline": null, "source_ids": [4]}],
    "tone_note":      "Good morning Alex! ..."
  }
}
```

- 프론트 규칙: 각 항목의 `source_ids`는 **원문 메시지로 점프하는 링크**로 렌더링한다
  (심사 즉석 검증 대응이자 UI/UX 포인트).
- 발동 조건(자동): 미커버 메시지 존재 ∧ 마지막 발화자 ≠ 나 ∧ 경과 ≥ 3시간.

## 오류 규약
- 401 인증 없음/불명 사용자 · 403 권한 없음(비참여자, 상태 조회 제한) · 404 대상 없음 · 400 규칙 위반(잔액 부족, 이중 정산, 상태 전이 불가 등 — detail에 사유)
