# 백엔드 산출물 목록 (DELIVERABLES)

본 저장소에 포함된 백엔드 산출물의 전체 목록과 버전 기준이다.
API 계약 문서는 **docs/api_spec_v2.md 하나로 일원화**되었다(구 api_spec.md는 폐기).
DB 스키마는 아직 두 계열(구현 기준 schema.sql / 팀 네이밍 docs/schema_v2.sql)로 존재한다.

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
| **API 명세 v2** | docs/api_spec_v2.md | **기준본(canonical)** — 서버가 노출하는 외부 계약이 이 문서와 1:1로 일치한다 |
| **DB 스키마 v2** | docs/schema_v2.sql | **팀 확정용(canonical)** — 팀 네이밍 기준 최신 |
| 크레딧 시스템 설명서 | docs/POOM_credit_brief.pdf | 팀 공유·심사 질의 대응용 |
| ~~구현 기준 명세~~ | api_spec.md | **폐기** — v2로 일원화. 기준본을 가리키는 안내문만 남아 있다 |
| 구현 기준 스키마 | schema.sql | 현재 코드 모델과 1:1 (참고용) |
| 프롬프트 규칙(패치판) | prompts/digest_prompt_patched.md | **백엔드 B 전달용 최신** — 팀 프롬프트 + 근거 규칙 |
| 프롬프트 규칙(원본) | prompts/digest_prompt.md | 참고용 |
| 실행·온보딩 안내 | README.md | 실행법 · 역할별 인수인계 · 보안 주의 |

주: **외부 계약(경로·요청/응답 JSON 키·상태 값)은 v2와 완전히 일치한다.**
내부 모델·DB 컬럼만 기존 네이밍(Collab/provider_id/credit_amount)을 유지하며, 변환은
`app/contract.py` 경계 한 곳에서만 일어난다. 내부 네이밍까지 맞추는 작업은 DB 스키마 변경을
동반하므로 PostgreSQL 전환(클라우드 배포) 시점에 docs/schema_v2.sql과 함께 처리한다.

## 3. 미착수 (남은 백엔드 업무)

1. LangChain 실연결 — app/engines/digest.py의 OpenAIProvider 구현 (백엔드 B와 협업 지점)
2. 클라우드 배포 — Dockerfile · Railway/Render 설정
