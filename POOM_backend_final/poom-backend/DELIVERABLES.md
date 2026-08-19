# 백엔드 산출물 목록 (DELIVERABLES)

본 저장소에 포함된 백엔드 산출물의 전체 목록과 버전 기준이다.
문서가 두 계열(구현 기준 / 팀 네이밍 기준)로 존재하므로, 어느 쪽이 기준인지 아래에 명시한다.

## 1. 실행 코드 (app/ · tests/) — 검증 완료

| 구성 | 내용 | 상태 |
|---|---|---|
| 크레딧 원장 | append-only + HOLD/RELEASE/REFUND, 이중 정산 DB 제약 차단, 잔액은 합산 | 테스트 통과 |
| Timezone Status 엔진 | 근무/수면/근무 시작 예정/자리 비움 + 예상 응답 시각, 순수 함수 | 테스트 통과 |
| AI Relay 트리거 | 지연 평가(접속 시 3시간 조건 검사, 크론 없음) + 수동 생성 | 테스트 통과 |
| 다이제스트 엔진 | 6필드 + 근거 연결(source_ids·verified), 팀 프롬프트 키 흡수 어댑터, 장애 폴백 | 테스트 통과 |
| 데모 인프라 | 가상 시각(/demo/time) + 시연 시드(/demo/seed, 한↔미 5단계) | 테스트 통과 |
| 테스트 | 단위 + 5단계 데모 리허설 통합 — 총 8건 | 전부 통과 |

## 2. 문서 — 기준 버전

| 문서 | 위치 | 기준 |
|---|---|---|
| **API 명세 v2** | docs/api_spec_v2.md | **팀 확정용(canonical)** — 팀 네이밍(/api/v1, projects, worker) 기준 최신 |
| **DB 스키마 v2** | docs/schema_v2.sql | **팀 확정용(canonical)** — 팀 네이밍 기준 최신 |
| 크레딧 시스템 설명서 | docs/POOM_credit_brief.pdf | 팀 공유·심사 질의 대응용 |
| 구현 기준 명세 | api_spec.md | 현재 코드가 실제로 노출하는 API (참고용) |
| 구현 기준 스키마 | schema.sql | 현재 코드 모델과 1:1 (참고용) |
| 프롬프트 규칙(패치판) | prompts/digest_prompt_patched.md | **백엔드 B 전달용 최신** — 팀 프롬프트 + 근거 규칙 |
| 프롬프트 규칙(원본) | prompts/digest_prompt.md | 참고용 |
| 실행·온보딩 안내 | README.md | 실행법 · 역할별 인수인계 · 보안 주의 |

주: 코드 내부 네이밍(collabs/provider)과 팀 문서 네이밍(projects/worker)이 상이하다.
팀이 v2 네이밍을 확정하는 즉시 코드 모델·경로를 v2로 리네이밍하여 일치시킨다(반나절 작업).

## 3. 미착수 (남은 백엔드 업무)

1. LangChain 실연결 — app/engines/digest.py의 OpenAIProvider 구현 (백엔드 B와 협업 지점)
2. 클라우드 배포 — Dockerfile · Railway/Render 설정
