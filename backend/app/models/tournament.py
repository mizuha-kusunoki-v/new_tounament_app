import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TournamentFormat, TournamentStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[TournamentStatus] = mapped_column(
        Enum(TournamentStatus), default=TournamentStatus.SETUP
    )
    format: Mapped[TournamentFormat] = mapped_column(
        Enum(TournamentFormat), default=TournamentFormat.DOUBLE_ELIMINATION
    )
    public_slug: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    manage_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    overall_champion_player_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
    rounds: Mapped[list["BracketRound"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
