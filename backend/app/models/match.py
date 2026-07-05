import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MatchKind


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bracket_round_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bracket_rounds.id"))
    kind: Mapped[MatchKind] = mapped_column(Enum(MatchKind), default=MatchKind.NORMAL)

    team_a_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    team_b_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    winner_team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)

    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sequence_in_round: Mapped[int] = mapped_column(Integer, default=0)

    bracket_round: Mapped["BracketRound"] = relationship(back_populates="matches")
