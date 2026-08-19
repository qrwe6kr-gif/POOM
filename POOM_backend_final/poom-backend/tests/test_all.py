# -*- coding: utf-8 -*-
"""엔진 단위 테스트 + 데모 리허설(5단계) 통합 테스트."""
import os
import pathlib
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST_DB = ROOT / "test_poom.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

from fastapi.testclient import TestClient  # noqa: E402

from app.engines import ledger  # noqa: E402
from app.engines.digest import MockProvider, DigestContext, finalize  # noqa: E402
from app.engines.relay import should_generate  # noqa: E402
from app.engines.status import compute_status, in_window  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
UTC = timezone.utc


def T(iso):
    return datetime.fromisoformat(iso).replace(tzinfo=UTC)


# ---------------- status engine ----------------

def test_in_window_wraps_midnight():
    assert in_window(23.5, 23, 7)
    assert in_window(3, 23, 7)
    assert not in_window(8, 23, 7)
    assert in_window(10, 9, 18)
    assert not in_window(18, 9, 18)


def test_status_states():
    # 서울 10:00 → 근무 중
    s = compute_status("Asia/Seoul", 9, 18, 23, 7, T("2026-08-20T01:00:00"))
    assert s.state == "working" and s.next_response_utc is None
    # LA 03:00 → 수면 중, 다음 응답 시각 존재
    s = compute_status("America/Los_Angeles", 9, 18, 23, 7, T("2026-08-20T10:00:00"))
    assert s.state == "sleeping" and s.next_response_utc is not None
    # 서울 07:30 → 출근 1.5시간 전 = soon
    s = compute_status("Asia/Seoul", 9, 18, 23, 7, T("2026-08-19T22:30:00"))
    assert s.state == "soon"
    # 서울 20:00 → away
    s = compute_status("Asia/Seoul", 9, 18, 23, 7, T("2026-08-20T11:00:00"))
    assert s.state == "away"


# ---------------- relay trigger ----------------

@dataclass
class Msg:
    id: int
    sender_id: str
    sent_at: datetime
    content: str = ""


def test_relay_trigger_conditions():
    t0 = T("2026-08-20T00:00:00")
    msgs = [Msg(1, "A", t0), Msg(2, "B", t0 + timedelta(minutes=5))]
    # 마지막 발화자가 나 → 발동 안 함
    fire, _ = should_generate("B", msgs, None, t0 + timedelta(hours=10))
    assert not fire
    # 상대가 마지막, 2시간 경과 → 미발동 / 4시간 → 발동
    fire, _ = should_generate("A", msgs, None, t0 + timedelta(hours=2))
    assert not fire
    fire, unc = should_generate("A", msgs, None, t0 + timedelta(hours=4))
    assert fire and len(unc) == 2
    # 이미 커버됨 → 미발동
    fire, _ = should_generate("A", msgs, 2, t0 + timedelta(hours=9))
    assert not fire


# ---------------- digest grounding ----------------

def test_digest_mock_and_grounding_gate():
    t0 = T("2026-08-20T00:00:00")
    msgs = [Msg(1, "us", t0, "Hi! Excited to start."),
            Msg(2, "kr", t0, "로고는 다크 네이비로 확정할게요"),
            Msg(3, "kr", t0, "폰트는 아직 고민 중이에요"),
            Msg(4, "kr", t0, "수요일까지 첫 시안 부탁드립니다"),
            Msg(5, "kr", t0, "SVG로 가능할까요?")]

    class R:
        name, preferred_language = "Alex", "en"

    raw = MockProvider().generate(DigestContext(msgs, R.name, R.preferred_language, "지호"))
    out = finalize(raw, {m.id for m in msgs}, R.preferred_language)
    assert any(2 in i["source_ids"] for i in out["decisions"])
    assert any(3 in i["source_ids"] for i in out["open_items"])
    assert any(4 in i["source_ids"] for i in out["action_items"])
    assert any(5 in i["source_ids"] for i in out["key_questions"])
    for key in ("relay_summary", "decisions", "open_items", "key_questions", "action_items"):
        for item in out[key]:
            assert item["source_ids"], f"ungrounded item in {key}"
    # 환각 게이트: 존재하지 않는 근거 id → 폐기
    bogus = {"decisions": [{"text": "fake", "source_ids": [999]}], "tone_note": ""}
    cleaned = finalize(bogus, {1, 2}, "en")
    assert cleaned["decisions"] == [] and cleaned["tone_note"]


# ---------------- ledger ----------------

def test_ledger_hold_release_refund():
    from app.db import SessionLocal
    from app.models import Project, User
    db = SessionLocal()
    now = datetime.now(UTC)
    a = User(name="a", email="a@t.t"); b = User(name="b", email="b@t.t")
    db.add_all([a, b]); db.flush()
    ledger.grant_signup_bonus(db, a.id, now)
    ledger.grant_signup_bonus(db, b.id, now)
    db.commit()
    assert ledger.balance(db, a.id) == 100

    c = Project(requester_id=a.id, worker_id=b.id, title="t", agreed_credits=60)
    db.add(c); db.flush()
    ledger.hold(db, c, now); db.commit()
    assert ledger.balance(db, a.id) == 40
    # 이중 hold / 초과 hold 차단
    try:
        ledger.hold(db, c, now); assert False
    except ValueError:
        db.rollback()
    ledger.release(db, c, now); db.commit()
    assert ledger.balance(db, b.id) == 160
    try:
        ledger.release(db, c, now); assert False
    except ValueError:
        db.rollback()
    try:
        ledger.refund(db, c, now); assert False
    except ValueError:
        db.rollback()

    c2 = Project(requester_id=a.id, worker_id=b.id, title="t2", agreed_credits=40)
    db.add(c2); db.flush()
    ledger.hold(db, c2, now)
    ledger.refund(db, c2, now); db.commit()
    assert ledger.balance(db, a.id) == 40
    # 잔액 부족 hold 차단
    c3 = Project(requester_id=a.id, worker_id=b.id, title="t3", agreed_credits=999)
    db.add(c3); db.flush()
    try:
        ledger.hold(db, c3, now); assert False
    except ValueError:
        db.rollback()
    db.close()


# ---------------- demo rehearsal: 5-step end-to-end (API 계약 v2) ----------------

V1 = "/api/v1"


def H(uid):
    return {"X-User-Id": uid}


def test_demo_flow_end_to_end():
    base = "2026-08-20T00:00:00+00:00"           # KST 09:00 / LA(PDT) 전날 17:00

    kr = client.post(f"{V1}/auth/signup", json={
        "name": "지호", "email": "kr@poom.dev", "country": "KR",
        "timezone": "Asia/Seoul", "preferred_language": "ko"}).json()["user_id"]
    us = client.post(f"{V1}/auth/signup", json={
        "name": "Alex", "email": "us@poom.dev", "country": "US",
        "timezone": "America/Los_Angeles", "preferred_language": "en"}).json()["user_id"]

    assert client.post(f"{V1}/me/needs", json={"role": "design"},
                       headers=H(kr)).status_code == 200
    assert client.post(f"{V1}/me/skills", json={"role": "design", "level": "mid"},
                       headers=H(us)).status_code == 200

    # 가상 세계 시각 T0 고정 (두 계정 동일)
    client.post(f"{V1}/demo/time", json={"user_ids": [kr, us], "now": base})

    # [1] 매칭 — 겹침 시간과 함께 Alex 발견
    m = client.get(f"{V1}/matching", headers=H(kr)).json()["results"]
    assert m and m[0]["user"]["user_id"] == us and m[0]["overlap_hours"] >= 0.5

    # 견적 60c 합의 → hold
    pid = client.post(f"{V1}/projects",
                      json={"worker_id": us, "title": "로고+키비주얼",
                            "agreed_credits": 60}, headers=H(kr)).json()["project_id"]
    r = client.post(f"{V1}/projects/{pid}/accept", headers=H(us)).json()
    assert r["status"] == "IN_PROGRESS" and r["escrow_held"] == 60
    assert client.get(f"{V1}/me/credits", headers=H(kr)).json()["balance"] == 40

    # 대화 5건 (마지막 4건은 KR 발신 — 결정/미결정/액션/질문 포함)
    for uid, body in [(us, "Hi! Excited to start."),
                      (kr, "로고는 다크 네이비로 확정할게요"),
                      (kr, "폰트는 아직 고민 중이에요"),
                      (kr, "수요일까지 첫 시안 부탁드립니다"),
                      (kr, "최종본은 SVG로 가능할까요?")]:
        client.post(f"{V1}/projects/{pid}/messages", json={"body": body}, headers=H(uid))
    client.get(f"{V1}/projects/{pid}/messages", headers=H(us))   # US가 읽음

    # [2] +11h — LA 04:00 수면 중
    t1 = "2026-08-20T11:00:00+00:00"
    client.post(f"{V1}/demo/time", json={"user_ids": [kr, us], "now": t1})
    st = client.get(f"{V1}/users/{us}/status", headers=H(kr)).json()
    assert st["status"] == "SLEEPING" and st["next_response_utc"]
    assert st["status_label"] == "비근무"              # 조회자(KR)의 언어로 생성
    assert st["timezone"] == "America/Los_Angeles"
    assert st["local_time"] == "04:00 AM"

    # [3] 수면 중 추가 메시지
    client.post(f"{V1}/projects/{pid}/messages",
                json={"body": "추가: 배경은 흰색으로 확정했어요"}, headers=H(kr))

    # 프라이버시: 제3자는 상태 조회 불가
    stranger = client.post(f"{V1}/auth/signup", json={
        "name": "S", "email": "s@poom.dev", "timezone": "Asia/Seoul"}).json()["user_id"]
    assert client.get(f"{V1}/users/{us}/status", headers=H(stranger)).status_code == 403

    # [4] +17h — LA 10:00 기상, 접속 순간 다이제스트 자동 생성 (지연 평가)
    t2 = "2026-08-20T17:00:00+00:00"
    client.post(f"{V1}/demo/time", json={"user_ids": [kr, us], "now": t2})
    d = client.get(f"{V1}/projects/{pid}/relay-digest", headers=H(us)).json()
    assert d["generated"] is True and d["language"] == "en" and d["trigger"] == "auto"
    assert d["project_id"] == pid and d["unread_message_count"] == 6
    pl = d["digest"]
    assert len(pl["decisions"]) >= 2          # 네이비 확정 + 흰색 확정
    assert pl["summary"] and pl["pending"] and pl["key_questions"] and pl["action_items"]
    assert pl["tone_cushioned_message"]
    for key in ("summary", "decisions", "pending", "key_questions", "action_items"):
        for item in pl[key]:
            assert item["source_ids"]
    # 중복 생성 방지
    d2 = client.get(f"{V1}/projects/{pid}/relay-digest", headers=H(us)).json()
    assert d2["generated"] is False and d2["digest_id"] == d["digest_id"]

    # [5] 완료 → 지급 → 상호 평가 동시 공개
    client.post(f"{V1}/projects/{pid}/messages", json={"body": "Got it! Draft by Wed."},
                headers=H(us))
    # 답변 전송 시 다이제스트 '확인 완료'(is_read) 전환
    assert client.get(f"{V1}/projects/{pid}/relay-digest",
                      headers=H(us)).json()["is_read"] is True
    r1 = client.post(f"{V1}/projects/{pid}/complete", headers=H(us)).json()
    assert r1["settled"] is False and r1["released_credits"] == 0
    assert r1["status"] == "IN_PROGRESS" and r1["confirmed"]["worker"] is True
    r = client.post(f"{V1}/projects/{pid}/complete", headers=H(kr)).json()
    assert r["settled"] is True and r["status"] == "COMPLETED"
    assert r["project_id"] == pid and r["released_credits"] == 60 and r["my_balance"] == 40
    credits_us = client.get(f"{V1}/me/credits", headers=H(us)).json()
    assert credits_us["balance"] == 160
    assert {t["type"] for t in credits_us["transactions"]} == {"SIGNUP_BONUS", "RELEASE"}

    # 협업방 헤더 · 목록 (v2 키)
    det = client.get(f"{V1}/projects/{pid}", headers=H(kr)).json()
    assert det["project_id"] == pid and det["status"] == "COMPLETED"
    assert det["agreed_credits"] == 60 and det["my_role"] == "requester"
    lst = client.get(f"{V1}/projects", headers=H(us)).json()["projects"]
    assert lst[0]["project_id"] == pid and lst[0]["my_role"] == "worker"

    client.post(f"{V1}/projects/{pid}/reviews", headers=H(us),
                json={"diligence": 5, "quality": 5, "communication": 5})
    assert client.get(f"{V1}/projects/{pid}/reviews", headers=H(us)).json()["visible"] is False
    client.post(f"{V1}/projects/{pid}/reviews", headers=H(kr),
                json={"diligence": 5, "quality": 4, "communication": 5})
    assert client.get(f"{V1}/projects/{pid}/reviews", headers=H(kr)).json()["visible"] is True


def test_demo_seed_endpoint():
    r = client.post(f"{V1}/demo/seed").json()
    assert r["project_id"] and len(r["demo_steps"]) == 5
    d = client.post(f"{V1}/projects/{r['project_id']}/relay-digest",
                    headers=H(r["us_user_id"])).json()
    assert d["generated"] is True and d["digest"]["decisions"]
    assert d["digest"]["tone_cushioned_message"]


def test_team_prompt_shape_is_accepted():
    """팀 프롬프트(다른 키 이름 + 문자열 배열) 출력도 파이프라인을 통과해야 한다."""
    from app.engines.digest import finalize
    team = {"summary": "s", "decisions": ["d"], "pending": ["p"],
            "key_questions": ["q?"], "action_items": ["a"],
            "tone_cushioned_message": "hi"}
    out = finalize(team, {1, 2}, "ko")
    assert out["relay_summary"][0]["text"] == "s"
    assert out["open_items"][0]["text"] == "p"
    assert out["tone_note"] == "hi"
    assert out["decisions"][0]["verified"] is False       # 근거 미제공 → 미확인 표시
    # 근거를 제공하면 verified=True, 허위 근거는 폐기
    good = {"decisions": [{"text": "d", "source_ids": [1]},
                          {"text": "fake", "source_ids": [999]}], "tone_note": "x"}
    o2 = finalize(good, {1, 2}, "ko")
    assert len(o2["decisions"]) == 1 and o2["decisions"][0]["verified"] is True


# ---------------- CORS ----------------

def test_cors_preflight_allows_frontend_origin():
    """Next.js 개발 서버의 preflight 통과 + 커스텀 헤더 X-User-Id 허용."""
    r = client.options(f"{V1}/me", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-User-Id"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "x-user-id" in r.headers["access-control-allow-headers"].lower()
    # 헤더 인증 방식이므로 credentials는 켜지 않는다
    assert "access-control-allow-credentials" not in r.headers


# ---------------- 이메일 간이 로그인 ----------------

def test_email_login_returns_same_user():
    """signup으로 만든 계정이 이메일만으로 다시 조회되고, 미등록 이메일은 404."""
    email = "login@poom.dev"
    uid = client.post(f"{V1}/auth/signup", json={
        "name": "로그인테스트", "email": email,
        "timezone": "Asia/Seoul", "preferred_language": "ko"}).json()["user_id"]
    r = client.post(f"{V1}/auth/login", json={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == uid
    assert body["name"] == "로그인테스트" and body["preferred_language"] == "ko"
    # 받은 user_id가 실제로 인증에 쓰인다
    assert client.get(f"{V1}/me", headers=H(body["user_id"])).json()["user_id"] == uid
    # 미등록 이메일
    bad = client.post(f"{V1}/auth/login", json={"email": "nobody@poom.dev"})
    assert bad.status_code == 404 and bad.json()["detail"]


# ---------------- 배포: DATABASE_URL 정규화 ----------------

def test_database_url_normalized_for_psycopg():
    """Railway류의 postgres:// 를 SQLAlchemy 2 + psycopg(v3) 형태로 바꾼다."""
    from app.config import _normalize_db_url
    target = "postgresql+psycopg://u:p@host:5432/db"
    assert _normalize_db_url("postgres://u:p@host:5432/db") == target
    assert _normalize_db_url("postgresql://u:p@host:5432/db") == target
    assert _normalize_db_url(target) == target          # 이미 정규형이면 그대로
    assert _normalize_db_url("sqlite:///./poom.db") == "sqlite:///./poom.db"


# ---------------- 데모 라우터 보호 ----------------

def test_demo_key_protects_demo_router():
    """DEMO_KEY가 설정된 동안만 X-Demo-Key를 요구하고, 해제하면 다시 무인증이다."""
    noop = {"user_ids": [], "now": None}     # 부수효과 없는 호출로 게이트만 확인
    os.environ["DEMO_KEY"] = "s3cret"
    try:
        assert client.post(f"{V1}/demo/time", json=noop).status_code == 403
        assert client.post(f"{V1}/demo/time", json=noop,
                           headers={"X-Demo-Key": "wrong"}).status_code == 403
        ok = client.post(f"{V1}/demo/time", json=noop, headers={"X-Demo-Key": "s3cret"})
        assert ok.status_code == 200 and ok.json()["ok"] is True
    finally:
        os.environ.pop("DEMO_KEY", None)
    # 미설정 상태에서는 헤더 없이도 통과 (로컬 개발·기존 테스트 경로)
    assert client.post(f"{V1}/demo/time", json=noop).status_code == 200
