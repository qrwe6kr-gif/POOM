# CLAUDE.md — POOM 백엔드 작업 규칙

## 프로젝트
해커톤 3일 MVP. 시차 협업 메신저 + AI Relay 다이제스트 + 크레딧 정산.
FastAPI 단일 서버, SQLAlchemy(로컬 SQLite / 배포 PostgreSQL), 테스트는 pytest.

## 명령어
- 실행: python -m uvicorn app.main:app --reload  → http://127.0.0.1:8000/docs
- 테스트: pytest -q  (전 건 통과가 기준선. 실패 상태로 턴을 끝내지 않는다)

## 불변 규칙 — 위반 금지, 이유 포함
1. [시간 관문] 시간 계산은 반드시 app/timeutil.py의 get_now(actor)를 경유한다.
   datetime.now() 직접 호출 금지. 이유: 계정별 가상 시각(데모 모드)이 이 단일 관문에
   의존하며, 우회 호출이 하나라도 생기면 심사 시연의 시간 이동이 깨진다.
2. [원장] users에 잔액 컬럼을 만들지 않는다. 잔액은 credit_transactions 합산으로만 읽는다.
   원장은 append-only(UPDATE/DELETE 금지)이고 hold/release/refund는 협업당 각 1회
   (UNIQUE 제약). ledger.py 함수 내부의 db.flush()는 세션이 autoflush=False라서
   필수다 — 제거하면 연쇄 호출에서 직전 거래가 보이지 않는 버그가 재발한다.
3. [환각 게이트] engines/digest.py의 finalize()가 근거(source_ids) 검증을 수행한다.
   이 게이트를 우회·약화하는 변경 금지. LLM 출력 형태 차이는 normalize()가 흡수한다 —
   새 출력 형태 지원이 필요하면 게이트를 풀지 말고 normalize()를 확장한다.
4. [데모 라우터] app/routers/demo.py는 심사 시연 전용 무인증 기능이다. 삭제하지 말되,
   일반 기능이 demo에 의존하게 만들지 않는다. 해커톤 기간에는 배포에도 포함한다.
5. [계약-문서 동기화] API 경로·JSON 키를 바꾸면 같은 커밋에서 docs/api_spec_v2.md와
   팀공유_README_먼저보기.md를 함께 갱신한다. 프론트는 문서만 보고 개발한다.

## 작업 규약
- 모든 변경 후 pytest -q 통과 확인. 테스트가 깨지는 리팩터링은 테스트 수정을 포함해
  한 커밋으로 완결한다.
- 커밋은 작업 단위로 분리하고 메시지는 conventional commit(feat/fix/refactor/docs) 형식.
- 확신이 없는 설계 판단은 임의로 진행하지 말고 멈춰서 질문한다.

## 로드맵 (예정 작업 — 새 코드 작성 시 이 방향과 충돌하지 않게)
1. API 경로를 팀 명세 v2(/api/v1/projects, worker 네이밍)로 통일하는 리팩터링
2. CORS 추가 + 이메일 간이 로그인
3. Dockerfile + Railway/Render 배포 (PostgreSQL 전환)
4. curl 기반 8단계 시연 리허설
