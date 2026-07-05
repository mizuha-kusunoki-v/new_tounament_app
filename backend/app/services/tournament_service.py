"""Orchestration layer: wires the pure bracket_engine logic to the DB models.

Persistence design notes (see the plan doc for full rationale):
- A bracket round that resolves as "terminal" (pool==2, or pool==3 with a
  forced exclusion) is persisted as a normal BracketRound whose ONLY match is
  a synthetic kind=TEAM_BYE match with team_b_id=None, winner_team_id set
  immediately to the champion team. This is the unique, unambiguous shape
  that identifies "this round crowned the bracket champion" (a genuine
  team-count-odd bye inside an in_progress round always coexists with at
  least one other real match in the same round, so there's no shape clash --
  see bracket_engine.resolve_round's pool dispatch for why).
- A bracket round that resolves as "defer" (not enough players yet, more may
  still arrive) is persisted as status=PENDING with pending_carry_player_ids
  holding the waiting individuals; no teams/matches exist yet. The same row
  is reused/updated in place once enough players accumulate.
- Grand Final (and its reset) reuse the exact same BracketRound/Team/Match
  shapes under bracket=GRAND_FINAL, round_number 1 (initial) and 2 (reset).
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Bracket, BracketRound, Match, MatchKind, Participant, RoundStatus, Team, Tournament
from app.models.enums import TournamentFormat, TournamentStatus
from app.services import bracket_engine as engine


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TournamentError(ValueError):
    """Raised for invalid tournament operations (bad state, bad input)."""


# ---------------------------------------------------------------------------
# Round lookups
# ---------------------------------------------------------------------------


def _get_latest_round(db: Session, tournament_id: uuid.UUID, bracket: Bracket) -> BracketRound | None:
    return (
        db.query(BracketRound)
        .filter(BracketRound.tournament_id == tournament_id, BracketRound.bracket == bracket)
        .order_by(BracketRound.round_number.desc())
        .first()
    )


def _get_round_by_number(
    db: Session, tournament_id: uuid.UUID, bracket: Bracket, round_number: int
) -> BracketRound | None:
    return (
        db.query(BracketRound)
        .filter(
            BracketRound.tournament_id == tournament_id,
            BracketRound.bracket == bracket,
            BracketRound.round_number == round_number,
        )
        .first()
    )


def is_terminal_round(round_: BracketRound) -> bool:
    """A round is 'terminal' (crowned this bracket's champion, no further
    rounds will be created) iff it consists of exactly one synthetic bye
    match. See module docstring for why this shape is unambiguous."""
    matches = round_.matches
    return len(matches) == 1 and matches[0].kind == MatchKind.TEAM_BYE and matches[0].team_b_id is None


def _get_terminal_round(db: Session, tournament_id: uuid.UUID, bracket: Bracket) -> BracketRound | None:
    for round_ in (
        db.query(BracketRound)
        .filter(BracketRound.tournament_id == tournament_id, BracketRound.bracket == bracket)
        .order_by(BracketRound.round_number.desc())
        .all()
    ):
        if round_.status == RoundStatus.COMPLETE and is_terminal_round(round_):
            return round_
    return None


def get_champion(round_: BracketRound) -> tuple[uuid.UUID, uuid.UUID]:
    team = next(t for t in round_.teams if t.id == round_.matches[0].team_a_id)
    return (team.player_one_id, team.player_two_id)


def _round_fully_reported(round_: BracketRound) -> bool:
    return all(m.winner_team_id is not None for m in round_.matches)


# ---------------------------------------------------------------------------
# Core round-advancement (shared by WB and LB)
# ---------------------------------------------------------------------------


def _apply_outcome(
    db: Session,
    tournament: Tournament,
    bracket: Bracket,
    round_number: int,
    existing_pending: BracketRound | None,
    outcome: engine.RoundOutcome,
) -> None:
    if outcome.kind == "defer":
        if existing_pending is not None:
            existing_pending.pending_carry_player_ids = [str(p) for p in outcome.carry_pool]
        else:
            db.add(
                BracketRound(
                    tournament_id=tournament.id,
                    bracket=bracket,
                    round_number=round_number,
                    status=RoundStatus.PENDING,
                    pending_carry_player_ids=[str(p) for p in outcome.carry_pool],
                )
            )
        return

    if existing_pending is not None:
        round_ = existing_pending
        round_.pending_carry_player_ids = None
    else:
        round_ = BracketRound(tournament_id=tournament.id, bracket=bracket, round_number=round_number)
        db.add(round_)
    db.flush()

    if outcome.kind == "terminal":
        round_.status = RoundStatus.COMPLETE
        round_.completed_at = _now()
        round_.excluded_participant_id = outcome.excluded_player
        if outcome.excluded_player is not None:
            _mark_eliminated(db, [outcome.excluded_player])
        team = Team(
            bracket_round_id=round_.id,
            player_one_id=outcome.champion_team[0],
            player_two_id=outcome.champion_team[1],
        )
        db.add(team)
        db.flush()
        db.add(
            Match(
                bracket_round_id=round_.id,
                kind=MatchKind.TEAM_BYE,
                team_a_id=team.id,
                team_b_id=None,
                winner_team_id=team.id,
                reported_at=_now(),
                sequence_in_round=0,
            )
        )
        db.flush()
        return

    # in_progress
    round_.status = RoundStatus.IN_PROGRESS
    round_.waiting_bye_participant_id = outcome.new_waiting
    team_lookup: dict[tuple, Team] = {}
    for pair in outcome.teams:
        t = Team(bracket_round_id=round_.id, player_one_id=pair[0], player_two_id=pair[1])
        db.add(t)
        db.flush()
        team_lookup[pair] = t

    seq = 0
    for team_a, team_b in outcome.matches:
        db.add(
            Match(
                bracket_round_id=round_.id,
                kind=MatchKind.NORMAL,
                team_a_id=team_lookup[team_a].id,
                team_b_id=team_lookup[team_b].id,
                sequence_in_round=seq,
            )
        )
        seq += 1

    if outcome.bye_team is not None:
        t = team_lookup[outcome.bye_team]
        db.add(
            Match(
                bracket_round_id=round_.id,
                kind=MatchKind.TEAM_BYE,
                team_a_id=t.id,
                team_b_id=None,
                winner_team_id=t.id,
                reported_at=_now(),
                sequence_in_round=seq,
            )
        )
    db.flush()


def advance_bracket(
    db: Session,
    tournament: Tournament,
    bracket: Bracket,
    extra_incoming: list[uuid.UUID],
    rng: random.Random,
) -> None:
    """Feed `extra_incoming` individuals into `bracket` and try to progress it.

    For WINNERS, `extra_incoming` is always that bracket's own just-completed
    round's winners (WB never receives outside arrivals). For LOSERS,
    `extra_incoming` is either newly dropped WB losers, or LB's own
    just-completed round's winners -- both funnel through this same function.
    """
    latest = _get_latest_round(db, tournament.id, bracket)

    if latest is not None and latest.status == RoundStatus.IN_PROGRESS:
        # Can't touch a round that's still being played. Queue new arrivals
        # (if any) right after it; they'll be picked up once it completes.
        if extra_incoming:
            queued_round_number = latest.round_number + 1
            queued = _get_round_by_number(db, tournament.id, bracket, queued_round_number)
            if queued is not None and queued.status == RoundStatus.PENDING:
                existing = queued.pending_carry_player_ids or []
                queued.pending_carry_player_ids = existing + [str(p) for p in extra_incoming]
            else:
                db.add(
                    BracketRound(
                        tournament_id=tournament.id,
                        bracket=bracket,
                        round_number=queued_round_number,
                        status=RoundStatus.PENDING,
                        pending_carry_player_ids=[str(p) for p in extra_incoming],
                    )
                )
        db.flush()
        return

    pool: list[uuid.UUID] = list(extra_incoming)
    round_number = 1
    existing_pending: BracketRound | None = None

    if latest is not None:
        if latest.status == RoundStatus.PENDING:
            pool += [uuid.UUID(p) for p in (latest.pending_carry_player_ids or [])]
            existing_pending = latest
            round_number = latest.round_number
        else:  # COMPLETE
            round_number = latest.round_number + 1
            if latest.waiting_bye_participant_id:
                pool.append(latest.waiting_bye_participant_id)
            further_pending = _get_round_by_number(db, tournament.id, bracket, round_number)
            if further_pending is not None and further_pending.status == RoundStatus.PENDING:
                pool += [uuid.UUID(p) for p in (further_pending.pending_carry_player_ids or [])]
                existing_pending = further_pending

    wb_finished = _get_terminal_round(db, tournament.id, Bracket.WINNERS) is not None
    more_players_possible = bracket == Bracket.LOSERS and not wb_finished

    outcome = engine.resolve_round(pool, None, more_players_possible, rng)
    _apply_outcome(db, tournament, bracket, round_number, existing_pending, outcome)


# ---------------------------------------------------------------------------
# Winner/loser extraction from a completed round
# ---------------------------------------------------------------------------


def _mark_eliminated(db: Session, player_ids: list[uuid.UUID]) -> None:
    if not player_ids:
        return
    db.query(Participant).filter(Participant.id.in_(player_ids)).update(
        {Participant.is_eliminated: True}, synchronize_session=False
    )


def _winners_and_losers(round_: BracketRound) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
    teams_by_id = {t.id: t for t in round_.teams}
    winners: list[uuid.UUID] = []
    losers: list[uuid.UUID] = []
    for match in round_.matches:
        winner_team = teams_by_id[match.winner_team_id]
        winners += [winner_team.player_one_id, winner_team.player_two_id]
        if match.team_b_id is not None:
            loser_team_id = match.team_b_id if match.winner_team_id == match.team_a_id else match.team_a_id
            loser_team = teams_by_id[loser_team_id]
            losers += [loser_team.player_one_id, loser_team.player_two_id]
    return winners, losers


# ---------------------------------------------------------------------------
# Single elimination completion (no LB, no grand final -- the WB champion is
# the tournament champion the moment WB itself terminates)
# ---------------------------------------------------------------------------


def _maybe_complete_single_elimination(db: Session, tournament: Tournament) -> None:
    if tournament.status == TournamentStatus.COMPLETE:
        return
    wb_final = _get_terminal_round(db, tournament.id, Bracket.WINNERS)
    if wb_final is None:
        return
    _complete_tournament(db, tournament, get_champion(wb_final))


# ---------------------------------------------------------------------------
# Grand Final
# ---------------------------------------------------------------------------


def _maybe_create_grand_final(db: Session, tournament: Tournament, rng: random.Random) -> None:
    wb_final = _get_terminal_round(db, tournament.id, Bracket.WINNERS)
    lb_final = _get_terminal_round(db, tournament.id, Bracket.LOSERS)
    if wb_final is None or lb_final is None:
        return
    if _get_latest_round(db, tournament.id, Bracket.GRAND_FINAL) is not None:
        return  # already created

    wb_champion = get_champion(wb_final)
    lb_champion = get_champion(lb_final)

    gf_round = BracketRound(
        tournament_id=tournament.id, bracket=Bracket.GRAND_FINAL, round_number=1, status=RoundStatus.IN_PROGRESS
    )
    db.add(gf_round)
    db.flush()
    team_a = Team(bracket_round_id=gf_round.id, player_one_id=wb_champion[0], player_two_id=wb_champion[1])
    team_b = Team(bracket_round_id=gf_round.id, player_one_id=lb_champion[0], player_two_id=lb_champion[1])
    db.add_all([team_a, team_b])
    db.flush()
    db.add(
        Match(
            bracket_round_id=gf_round.id,
            kind=MatchKind.GRAND_FINAL,
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            sequence_in_round=0,
        )
    )
    db.flush()


def _handle_grand_final_round_complete(
    db: Session, tournament: Tournament, round_: BracketRound, rng: random.Random
) -> None:
    match = round_.matches[0]
    teams_by_id = {t.id: t for t in round_.teams}
    winner_team = teams_by_id[match.winner_team_id]
    winner_players = (winner_team.player_one_id, winner_team.player_two_id)
    loser_team_id = match.team_b_id if match.winner_team_id == match.team_a_id else match.team_a_id
    loser_team = teams_by_id[loser_team_id]

    if match.kind == MatchKind.GRAND_FINAL and match.winner_team_id == match.team_a_id:
        # WB champion (team_a by construction) won outright -- tournament over.
        _mark_eliminated(db, [loser_team.player_one_id, loser_team.player_two_id])
        _complete_tournament(db, tournament, winner_players)
        return

    if match.kind == MatchKind.GRAND_FINAL_RESET:
        _mark_eliminated(db, [loser_team.player_one_id, loser_team.player_two_id])
        _complete_tournament(db, tournament, winner_players)
        return

    # match.kind == GRAND_FINAL and LB champion (team_b) won -> bracket reset.
    team_a = teams_by_id[match.team_a_id]
    team_b = teams_by_id[match.team_b_id]
    four = engine.form_grand_final(
        (team_a.player_one_id, team_a.player_two_id), (team_b.player_one_id, team_b.player_two_id)
    )
    reset_team_a_pair, reset_team_b_pair = engine.bracket_reset_teams(four, rng)

    reset_round = BracketRound(
        tournament_id=tournament.id, bracket=Bracket.GRAND_FINAL, round_number=2, status=RoundStatus.IN_PROGRESS
    )
    db.add(reset_round)
    db.flush()
    reset_team_a = Team(
        bracket_round_id=reset_round.id, player_one_id=reset_team_a_pair[0], player_two_id=reset_team_a_pair[1]
    )
    reset_team_b = Team(
        bracket_round_id=reset_round.id, player_one_id=reset_team_b_pair[0], player_two_id=reset_team_b_pair[1]
    )
    db.add_all([reset_team_a, reset_team_b])
    db.flush()
    db.add(
        Match(
            bracket_round_id=reset_round.id,
            kind=MatchKind.GRAND_FINAL_RESET,
            team_a_id=reset_team_a.id,
            team_b_id=reset_team_b.id,
            sequence_in_round=0,
        )
    )
    db.flush()


def _complete_tournament(db: Session, tournament: Tournament, champion_players: tuple[uuid.UUID, uuid.UUID]) -> None:
    tournament.status = TournamentStatus.COMPLETE
    tournament.completed_at = _now()
    tournament.overall_champion_player_ids = [str(champion_players[0]), str(champion_players[1])]


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def start_tournament(db: Session, tournament: Tournament, rng: random.Random | None = None) -> None:
    if tournament.status != TournamentStatus.SETUP:
        raise TournamentError("Tournament has already been started")
    participants = db.query(Participant).filter(Participant.tournament_id == tournament.id).all()
    if len(participants) < engine.MIN_PARTICIPANTS:
        raise TournamentError(f"Need at least {engine.MIN_PARTICIPANTS} participants to start")

    rng = rng or random.Random()
    tournament.status = TournamentStatus.IN_PROGRESS
    tournament.started_at = _now()
    advance_bracket(db, tournament, Bracket.WINNERS, [p.id for p in participants], rng)
    db.commit()


def report_match_result(
    db: Session, tournament: Tournament, match: Match, winner_team_id: uuid.UUID, rng: random.Random | None = None
) -> None:
    if match.winner_team_id is not None:
        raise TournamentError("This match has already been reported")
    if winner_team_id not in (match.team_a_id, match.team_b_id):
        raise TournamentError("winner_team_id must be one of the match's two teams")

    rng = rng or random.Random()
    match.winner_team_id = winner_team_id
    match.reported_at = _now()
    db.flush()

    round_ = match.bracket_round
    if not _round_fully_reported(round_):
        db.commit()
        return

    round_.status = RoundStatus.COMPLETE
    round_.completed_at = _now()
    db.flush()

    if round_.bracket == Bracket.GRAND_FINAL:
        _handle_grand_final_round_complete(db, tournament, round_, rng)
    else:
        winners, losers = _winners_and_losers(round_)
        advance_bracket(db, tournament, round_.bracket, winners, rng)
        if round_.bracket == Bracket.WINNERS:
            if tournament.format == TournamentFormat.DOUBLE_ELIMINATION and losers:
                advance_bracket(db, tournament, Bracket.LOSERS, losers, rng)
            else:
                # Single elimination: a WB loss eliminates outright, no LB to catch it.
                _mark_eliminated(db, losers)
        elif round_.bracket == Bracket.LOSERS:
            # A second loss (this time in LB) eliminates these players outright.
            _mark_eliminated(db, losers)

        if tournament.format == TournamentFormat.DOUBLE_ELIMINATION:
            _maybe_create_grand_final(db, tournament, rng)
        else:
            _maybe_complete_single_elimination(db, tournament)

    db.commit()


def delete_tournament_cascade(db: Session, tournament: Tournament) -> None:
    """Delete a tournament and everything under it.

    Deliberately NOT a bare db.delete(tournament) relying on ORM cascades:
    Team.player_one_id/player_two_id, Match.team_a_id/team_b_id/winner_team_id,
    and BracketRound.waiting_bye_participant_id/excluded_participant_id are
    plain FK columns with no relationship() attached, so SQLAlchemy's cascade
    machinery doesn't know about them. Since none of these FKs have
    ondelete= set at the DB level either, a naive ORM delete can hit a
    Postgres FK violation depending on statement ordering. Deleting in this
    explicit order (matches -> teams -> bracket_rounds -> participants ->
    tournament) satisfies every FK dependency regardless of what the ORM's
    own cascade graph does or doesn't know about.
    """
    round_ids = [r.id for r in db.query(BracketRound.id).filter(BracketRound.tournament_id == tournament.id)]
    team_ids = (
        [t.id for t in db.query(Team.id).filter(Team.bracket_round_id.in_(round_ids))] if round_ids else []
    )

    if round_ids:
        db.query(Match).filter(Match.bracket_round_id.in_(round_ids)).delete(synchronize_session=False)
    if team_ids:
        db.query(Team).filter(Team.id.in_(team_ids)).delete(synchronize_session=False)
    if round_ids:
        db.query(BracketRound).filter(BracketRound.id.in_(round_ids)).delete(synchronize_session=False)
    db.query(Participant).filter(Participant.tournament_id == tournament.id).delete(synchronize_session=False)
    db.delete(tournament)
    db.commit()
