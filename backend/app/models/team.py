import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bracket_round_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bracket_rounds.id"))
    player_one_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"))
    player_two_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"))

    bracket_round: Mapped["BracketRound"] = relationship(back_populates="teams")
