import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Bracket, RoundStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BracketRound(Base):
    __tablename__ = "bracket_rounds"
    __table_args__ = (UniqueConstraint("tournament_id", "bracket", "round_number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tournament_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tournaments.id"))
    bracket: Mapped[Bracket] = mapped_column(Enum(Bracket))
    round_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[RoundStatus] = mapped_column(Enum(RoundStatus), default=RoundStatus.PENDING)

    waiting_bye_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("participants.id"), nullable=True
    )
    excluded_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("participants.id"), nullable=True
    )
    # Only set while status==PENDING: individuals stuck at pool size 2 or 3
    # waiting for more players to arrive (see bracket_engine.resolve_round's
    # "defer" outcome) before a real round can be formed for them.
    pending_carry_player_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tournament: Mapped["Tournament"] = relationship(back_populates="rounds")
    teams: Mapped[list["Team"]] = relationship(back_populates="bracket_round", cascade="all, delete-orphan")
    matches: Mapped[list["Match"]] = relationship(back_populates="bracket_round", cascade="all, delete-orphan")
