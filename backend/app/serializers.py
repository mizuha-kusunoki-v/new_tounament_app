"""Builds API response schemas from ORM objects, resolving participant ids to
display names/eliminated-flags along the way."""

from __future__ import annotations

import uuid

from app.models import Tournament
from app.schemas.tournament import (
    MatchOut,
    ParticipantOut,
    RoundOut,
    TeamOut,
    TournamentManageStateOut,
    TournamentStateOut,
)


def _participant_out(participants_by_id: dict[uuid.UUID, object], participant_id: uuid.UUID | None) -> ParticipantOut | None:
    if participant_id is None:
        return None
    return ParticipantOut.model_validate(participants_by_id[participant_id])


def build_tournament_state(tournament: Tournament, *, include_manage_token: bool) -> TournamentStateOut | TournamentManageStateOut:
    participants_by_id = {p.id: p for p in tournament.participants}

    rounds_out = []
    for round_ in sorted(tournament.rounds, key=lambda r: (r.bracket.value, r.round_number)):
        teams_by_id = {t.id: t for t in round_.teams}

        def _team_out(team_id: uuid.UUID | None) -> TeamOut | None:
            if team_id is None:
                return None
            team = teams_by_id[team_id]
            return TeamOut(
                id=team.id,
                player_one=ParticipantOut.model_validate(participants_by_id[team.player_one_id]),
                player_two=ParticipantOut.model_validate(participants_by_id[team.player_two_id]),
            )

        matches_out = [
            MatchOut(
                id=m.id,
                kind=m.kind,
                team_a=_team_out(m.team_a_id),
                team_b=_team_out(m.team_b_id),
                winner_team_id=m.winner_team_id,
                sequence_in_round=m.sequence_in_round,
            )
            for m in sorted(round_.matches, key=lambda m: m.sequence_in_round)
        ]

        rounds_out.append(
            RoundOut(
                id=round_.id,
                bracket=round_.bracket,
                round_number=round_.round_number,
                status=round_.status,
                waiting_bye_participant=_participant_out(participants_by_id, round_.waiting_bye_participant_id),
                excluded_participant=_participant_out(participants_by_id, round_.excluded_participant_id),
                matches=matches_out,
            )
        )

    overall_champion = None
    if tournament.overall_champion_player_ids:
        overall_champion = [
            ParticipantOut.model_validate(participants_by_id[uuid.UUID(pid)])
            for pid in tournament.overall_champion_player_ids
        ]

    base_kwargs = dict(
        id=tournament.id,
        name=tournament.name,
        status=tournament.status,
        format=tournament.format,
        public_slug=tournament.public_slug,
        participants=[ParticipantOut.model_validate(p) for p in tournament.participants],
        rounds=rounds_out,
        overall_champion=overall_champion,
    )

    if include_manage_token:
        return TournamentManageStateOut(manage_token=tournament.manage_token, **base_kwargs)
    return TournamentStateOut(**base_kwargs)
