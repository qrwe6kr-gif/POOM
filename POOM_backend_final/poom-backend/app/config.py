"""확정 파라미터 — 팀 합의값은 전부 여기에서만 바꾼다."""
import os

def _normalize_db_url(url: str) -> str:
    """배포 플랫폼이 주는 PostgreSQL URL을 이 프로젝트의 드라이버에 맞춰 정규화한다.

    - Railway/Heroku류는 postgres:// 접두사를 주는데 SQLAlchemy 2는 이를 거부한다.
    - postgresql:// 는 받아주지만 기본 드라이버로 psycopg2를 찾는다.
      설치하는 드라이버는 psycopg(v3)이므로 두 경우 모두 postgresql+psycopg:// 로 맞춘다.
    - sqlite 등 그 밖의 URL은 그대로 둔다(로컬 동작 불변).
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = _normalize_db_url(os.getenv("DATABASE_URL", "sqlite:///./poom.db"))

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
# 로컬 개발 서버 오리진(기본 허용). 5173은 Vite, 3000은 Next.js/CRA 기본 포트다 —
# 프론트가 어느 쪽으로 뜨든 로컬 연동이 막히지 않게 둘 다 허용한다.
DEV_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")


def demo_key() -> str:
    """데모 라우터(/demo/*) 보호 키. 비어 있으면 무인증 — 로컬 개발·테스트 기본값이다.

    다른 설정과 달리 상수가 아니라 호출 시점에 읽는다. 테스트가 환경변수를 설정·해제해
    보호 켠 경로와 끈 경로를 모두 검증할 수 있어야 하기 때문이다.
    """
    return os.getenv("DEMO_KEY", "")
