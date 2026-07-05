"""End-to-end fuzz test of the DB-backed orchestration layer (tournament_service).

Unlike test_bracket_engine.py's fuzz test (pure logic, no DB), this exercises
the real SQLAlchemy session, round persistence, and flush timing -- this is
exactly the layer where a real bug was found during development: a missing
db.flush() after creating a round's final Match row meant a same-transaction
follow-up query (checking whether both brackets had crowned a champion, to
create the grand final) could see stale state depending on which order
pending matches happened to be resolved in. This test resolves matches in a
randomized order (not just "first pending") across many seeds/sizes to catch
any other order-dependent staleness bugs.
"""

import random

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import BracketRound, Match, Participant, Tournament
from app.models.enums import TournamentFormat
from app.services import tournament_service


def _pending_playable_matches(db, tournament_id):
    return (
        db.query(Match)
        .join(Match.bracket_round)
        .filter(BracketRound.tournament_id == tournament_id, Match.team_b_id.isnot(None), Match.winner_team_id.is_(None))
        .all()
    )


def _run_tournament(n: int, seed: int, max_iterations: int, format: TournamentFormat) -> None:
    rng = random.Random(seed)
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    tournament = Tournament(
        name=f"n={n} seed={seed} format={format.value}",
        format=format,
        public_slug=f"pub-{seed}",
        manage_token=f"mgr-{seed}",
    )
    db.add(tournament)
    db.commit()
    for i in range(n):
        db.add(Participant(tournament_id=tournament.id, display_name=f"P{i}"))
    db.commit()

    tournament_service.start_tournament(db, tournament, rng)

    iterations = 0
    while tournament.status.value != "COMPLETE":
        iterations += 1
        assert iterations <= max_iterations, f"n={n} seed={seed}: stalled after {iterations} iterations"
        pending = _pending_playable_matches(db, tournament.id)
        assert pending, f"n={n} seed={seed}: no pending matches but tournament not complete ({tournament.status})"
        match = rng.choice(pending)
        tournament_service.report_match_result(db, tournament, match, match.team_a_id, rng)

    assert tournament.overall_champion_player_ids is not None
    assert len(tournament.overall_champion_player_ids) == 2

    if format == TournamentFormat.SINGLE_ELIMINATION:
        no_losers_rounds = db.query(BracketRound).filter_by(tournament_id=tournament.id, bracket="LOSERS").count()
        no_gf_rounds = db.query(BracketRound).filter_by(tournament_id=tournament.id, bracket="GRAND_FINAL").count()
        assert no_losers_rounds == 0, f"n={n} seed={seed}: single elimination must never create an LB round"
        assert no_gf_rounds == 0, f"n={n} seed={seed}: single elimination must never create a grand final round"


@pytest.mark.parametrize("n", list(range(4, 21)))
def test_service_fuzz_random_resolution_order_double_elimination(n):
    for seed in range(10):
        _run_tournament(n, seed * 97 + n, max_iterations=n * 6 + 30, format=TournamentFormat.DOUBLE_ELIMINATION)


@pytest.mark.parametrize("n", list(range(4, 21)))
def test_service_fuzz_random_resolution_order_single_elimination(n):
    for seed in range(10):
        _run_tournament(n, seed * 97 + n, max_iterations=n * 6 + 30, format=TournamentFormat.SINGLE_ELIMINATION)
