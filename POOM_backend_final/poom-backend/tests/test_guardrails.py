# -*- coding: utf-8 -*-
"""불변 규칙(CLAUDE.md)을 사람 기억이 아니라 테스트가 지키게 하는 가드레일.

기능 테스트가 아니다. "이렇게 짜면 안 된다"를 기계화한 것이라, 규칙을 어긴 코드는
리뷰를 기다리지 않고 여기서 먼저 걸린다.
"""
import pathlib
import re

APP = pathlib.Path(__file__).resolve().parents[1] / "app"

# 규칙 1의 유일한 예외 — 시간 관문 자신
TIME_GATE = APP / "timeutil.py"
DIRECT_NOW = re.compile(r"datetime\.(now|utcnow)\s*\(")

# 규칙 2 — users에 있으면 안 되는 컬럼 이름
BALANCE_LIKE = re.compile(r"balance|wallet|^credits?$", re.I)


def test_no_direct_datetime_now():
    """[불변 규칙 1] 시간 계산은 app/timeutil.py의 get_now(actor)를 경유한다.

    계정별 가상 시각(데모 모드)이 이 단일 관문에 의존한다. 우회 호출이 하나라도 생기면
    그 코드만 실제 시각으로 움직여 심사 시연의 시간 이동이 깨진다.

    한계: `from datetime import datetime as dt; dt.now()` 같은 별칭 우회는 잡지 못한다.
    정직하게 쓴 코드의 실수를 잡는 것이 목적이다.
    """
    offenders = []
    for path in sorted(APP.rglob("*.py")):
        if path == TIME_GATE:
            continue
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.split("#", 1)[0]          # 주석은 제외
            if DIRECT_NOW.search(line):
                offenders.append(f"  {path.relative_to(APP.parent)}:{lineno}: {raw.strip()}")
    assert not offenders, (
        "datetime.now()/utcnow() 직접 호출은 금지다 — app/timeutil.py의 get_now(actor)를 쓸 것.\n"
        "(데모 모드의 가상 시각이 이 관문 하나에 의존한다)\n" + "\n".join(offenders))


def test_no_balance_column():
    """[불변 규칙 2] users에 잔액 컬럼을 만들지 않는다.

    잔액 컬럼과 거래 테이블이 공존하면 진실이 둘이 되어 반드시 어긋난다.
    잔액은 credit_transactions 합산(ledger.balance)으로만 읽는다.
    """
    from app.models import User

    bad = [c.name for c in User.__table__.columns if BALANCE_LIKE.search(c.name)]
    assert not bad, (
        f"users에 잔액성 컬럼이 생겼다: {bad}. "
        "잔액은 credit_transactions 합산(app/engines/ledger.py의 balance)으로만 읽는다.")
