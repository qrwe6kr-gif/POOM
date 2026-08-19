"""POOM 도메인 모델.

원장 원칙: 잔액 컬럼은 존재하지 않는다. 잔액은 credit_transactions의 합으로만 계산한다.
크레딧 원천(ttype)이 곧 원천 태그다: signup_bonus / topup / hold / release / refund.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (JSON, Boolean, DateTime, ForeignKey, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .config import (SLEEP_END_DEFAULT, SLEEP_START_DEFAULT,
                     WORK_END_DEFAULT, WORK_START_DEFAULT)


def uid() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    country: Mapped[str] = mapped_column(String(40), default="")
    tz: Mapped[str] = mapped_column(String(64), default="Asia/Seoul")
    lang: Mapped[str] = mapped_column(String(8), default="ko")  # 다이제스트 언어
    work_start: Mapped[int] = mapped_column(Integer, default=WORK_START_DEFAULT)
    work_end: Mapped[int] = mapped_column(Integer, default=WORK_END_DEFAULT)
    sleep_start: Mapped[int] = mapped_column(Integer, default=SLEEP_START_DEFAULT)
    sleep_end: Mapped[int] = mapped_column(Integer, default=SLEEP_END_DEFAULT)
    is_pro: Mapped[bool] = mapped_column(Boolean, default=False)
    # 데모 모드: 이 계정의 '현재 시각'을 강제로 고정 (없으면 실제 시각)
    demo_now: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Skill(Base):
    __tablename__ = "user_skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(40))          # dev / design / sound / plan / marketing / translate
    level: Mapped[str] = mapped_column(String(20), default="junior")
    portfolio_url: Mapped[str] = mapped_column(String(300), default="")


class Need(Base):
    __tablename__ = "user_needs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(40))
    note: Mapped[str] = mapped_column(String(300), default="")


class Collab(Base):
    """협업 상태 머신: requested → agreed → completed / cancelled.

    agreed 진입 시 의뢰자 크레딧이 hold(잠금)된다.
    completed 진입(양측 확인) 시 release로 공급자에게 지급된다.
    """
    __tablename__ = "collabs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    provider_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(160))
    scope: Mapped[str] = mapped_column(Text, default="")
    credit_amount: Mapped[int] = mapped_column(Integer)     # 건당 확정 견적
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="requested")
    requester_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    agreed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collab_id: Mapped[str] = mapped_column(ForeignKey("collabs.id"))
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CreditTx(Base):
    """append-only 원장. UPDATE/DELETE 금지 — 정정도 새 행으로만."""
    __tablename__ = "credit_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(Integer)            # 부호 있는 값
    ttype: Mapped[str] = mapped_column(String(20))          # signup_bonus/topup/hold/release/refund
    collab_id: Mapped[Optional[str]] = mapped_column(ForeignKey("collabs.id"), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # 협업당 hold/release/refund 각 1회 — DB 수준에서 이중 집행 차단
    __table_args__ = (UniqueConstraint("collab_id", "ttype", name="uq_tx_collab_type"),)


class RelayDigest(Base):
    __tablename__ = "relay_digests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collab_id: Mapped[str] = mapped_column(ForeignKey("collabs.id"))
    for_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    lang: Mapped[str] = mapped_column(String(8))
    trigger: Mapped[str] = mapped_column(String(10))        # auto | manual
    covers_to_message_id: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)             # 6필드 + 항목별 source_ids
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)  # 수신자 답변 전송 시 '확인 완료'
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collab_id: Mapped[str] = mapped_column(ForeignKey("collabs.id"))
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    diligence: Mapped[int] = mapped_column(Integer)
    quality: Mapped[int] = mapped_column(Integer)
    communication: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("collab_id", "reviewer_id", name="uq_review_once"),)
