from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import Bracket, MatchKind, RoundStatus, TournamentFormat, TournamentStatus


class ParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    display_name: str
    is_eliminated: bool


class TeamOut(BaseModel):
    id: uuid.UUID
    player_one: ParticipantOut
    player_two: ParticipantOut


class MatchOut(BaseModel):
    id: uuid.UUID
    kind: MatchKind
    team_a: TeamOut | None
    team_b: TeamOut | None
    winner_team_id: uuid.UUID | None
    sequence_in_round: int


class RoundOut(BaseModel):
    id: uuid.UUID
    bracket: Bracket
    round_number: int
    status: RoundStatus
    waiting_bye_participant: ParticipantOut | None
    excluded_participant: ParticipantOut | None
    matches: list[MatchOut]


class TournamentStateOut(BaseModel):
    id: uuid.UUID
    name: str
    status: TournamentStatus
    format: TournamentFormat
    public_slug: str
    participants: list[ParticipantOut]
    rounds: list[RoundOut]
    overall_champion: list[ParticipantOut] | None


class TournamentManageStateOut(TournamentStateOut):
    manage_token: str


class TournamentCreateIn(BaseModel):
    name: str
    format: TournamentFormat = TournamentFormat.DOUBLE_ELIMINATION


class TournamentCreatedOut(BaseModel):
    id: uuid.UUID
    name: str
    manage_token: str
    public_slug: str
    format: TournamentFormat


class ParticipantCreateIn(BaseModel):
    display_name: str


class MatchReportIn(BaseModel):
    winner_team_id: uuid.UUID
