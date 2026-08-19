"""확정 파라미터 — 팀 합의값은 전부 여기에서만 바꾼다."""
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./poom.db")

SIGNUP_BONUS = 100          # 신규 가입 초기 지갑 (c)
CREDIT_PER_HOUR = 10        # 참고 단가: 10c ≈ 표준 1시간 상당
RELAY_THRESHOLD_HOURS = 3   # 무응답 임계 (합의값)
SOON_HOURS = 3              # '근무 시작 예정' 판정 범위
SLEEP_START_DEFAULT = 23
SLEEP_END_DEFAULT = 7
WORK_START_DEFAULT = 9
WORK_END_DEFAULT = 18
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")  # mock | openai
# 프론트 배포 도메인. 로컬 개발 오리진(localhost:3000)은 코드에 상수로 두고,
# 배포 후 추가되는 도메인만 이 환경변수로 넣는다.
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")
