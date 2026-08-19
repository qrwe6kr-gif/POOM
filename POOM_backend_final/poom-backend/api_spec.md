# POOM Backend — API 명세 (구 v0.1, 폐기)

**이 문서는 더 이상 유지되지 않는다. 계약의 기준본은 [docs/api_spec_v2.md](docs/api_spec_v2.md) 하나다.**

과거에는 코드가 노출하는 실제 경로(`/collabs`, `provider_id`, `credit_amount`)와
팀 확정 명세 v2(`/api/v1/projects`, `worker_id`, `agreed_credits`)가 달라서
"구현 기준"과 "팀 확정" 두 계열의 문서를 따로 두었다.

이제 **서버가 노출하는 외부 계약이 v2와 1:1로 일치**하므로 두 계열을 유지할 이유가 없다.
경로·요청/응답 JSON 키·상태 값은 전부 docs/api_spec_v2.md를 보면 된다.
(내부 모델·DB 컬럼은 여전히 Collab/provider_id를 쓰며, 변환은 `app/contract.py` 경계에서만 일어난다.)

서버 실행 후 `/docs`(Swagger)에서 실시간 명세와 시험 호출도 가능하다.
