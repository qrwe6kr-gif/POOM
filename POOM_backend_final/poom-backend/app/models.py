"""POOM 도메인 모델 — docs/schema_v2.sql(팀 확정 스키마 v2)과 1:1로 대응한다.

원장 원칙: 잔액 컬럼은 존재하지 않는다. 잔액은 credit_transactions의 합으로만 계산한다.
크레딧 원천(tx_type)이 곧 원천 태그다: SIGNUP_BONUS / TOPUP / HOLD / RELEASE / REFUND.

id 타입 주의 — 스키마 v2는 SERIAL(정수)이지만 코드는 32자 hex 문자열을 쓴다.
외부 계약(docs/api_spec_v2.md)이 문자열 id로 확정돼 있고, 스키마 v2의 운영 메모도
Supabase Auth 도입 시 UUID 매핑을 예고하므로 문자열 쪽을 유지한다.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (JSON, Boolean, CheckConstraint, DateTime, ForeignKey,
                        Index, Integer, String, Text, UniqueConstraint)
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
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    country: Mapped[str] = mapped_column(String(40), default="")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Seoul")
    preferred_language: Mapped[str] = mapped_column(String(10), default="ko")  # 다이제스트 언어
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
    skill: Mapped[str] = mapped_column(String(100))        # dev / design / sound / plan / marketing / translate
    level: Mapped[str] = mapped_column(String(20), default="junior")
    portfolio_url: Mapped[str] = mapped_column(String(300), default="")
    __table_args__ = (Index("idx_skills_skill", "skill"),)


class Need(Base):
    __tablename__ = "user_needs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    skill: Mapped[str] = mapped_column(String(100))
    note: Mapped[str] = mapped_column(String(300), default="")


class Project(Base):
    """협업 상태 머신: MATCHED → IN_PROGRESS → COMPLETED / CANCELLED.

    IN_PROGRESS 진입(작업자 수락) 시 의뢰자 크레딧이 HOLD(잠금)된다.
    COMPLETED 진입(양측 확인) 시 RELEASE로 작업자에게 지급된다.
    """
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    worker_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    scope: Mapped[str] = mapped_column(Text, default="")
    agreed_credits: Mapped[int] = mapped_column(Integer)    # 건당 확정 견적 — 기본값 없음
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="MATCHED")
    requester_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    worker_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    agreed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("agreed_credits > 0", name="ck_projects_agreed_credits_positive"),
        Index("idx_projects_requester", "requester_id"),
        Index("idx_projects_worker", "worker_id"),
    )


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("idx_messages_project", "project_id", "id"),)


class CreditTx(Base):
    """append-only 원장. UPDATE/DELETE 금지 — 정정도 새 행으로만."""
    __tablename__ = "credit_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(Integer)            # 부호 있는 값 (HOLD는 음수)
    tx_type: Mapped[str] = mapped_column(String(20))        # SIGNUP_BONUS/TOPUP/HOLD/RELEASE/REFUND
    project_id: Mapped[Optional[str]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # 프로젝트당 HOLD/RELEASE/REFUND 각 1회 — DB 수준에서 이중 집행 차단
    __table_args__ = (
        UniqueConstraint("project_id", "tx_type", name="uq_tx_project_type"),
        Index("idx_tx_user", "user_id"),
    )


class RelayDigest(Base):
    __tablename__ = "ai_relay_digests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    language: Mapped[str] = mapped_column(String(10), default="ko")
    trigger_type: Mapped[str] = mapped_column(String(10), default="auto")   # auto | manual
    covers_to_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"))
    payload: Mapped[dict] = mapped_column(JSON)             # 6필드 + 항목별 source_ids
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)  # 수신자 답변 전송 시 '확인 완료'
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("idx_digest_lookup", "project_id", "recipient_id", "id"),)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    diligence: Mapped[int] = mapped_column(Integer)
    quality: Mapped[int] = mapped_column(Integer)
    communication: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("project_id", "reviewer_id", name="uq_review_once"),
        CheckConstraint("diligence BETWEEN 1 AND 5", name="ck_reviews_diligence"),
        CheckConstraint("quality BETWEEN 1 AND 5", name="ck_reviews_quality"),
        CheckConstraint("communication BETWEEN 1 AND 5", name="ck_reviews_communication"),
    )
