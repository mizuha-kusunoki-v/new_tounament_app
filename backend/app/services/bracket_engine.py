"""Pure bracket-progression logic for the shuffle-teams double-elimination format.

No DB / FastAPI imports here on purpose: every function operates on plain
player-id values (any hashable) and an injected ``random.Random`` instance,
so the whole module is deterministic under test and reusable from the API
layer without pulling in SQLAlchemy sessions.

See C:\\Users\\KSeki\\.claude\\plans\\ancient-tumbling-jellyfish.md for the
design rationale, in particular the pool-size-3 deadlock fix below: a naive
"odd pool -> one player waits, odd team count -> one team byes" rule has a
fixed point at pool size 3 that never terminates.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Generic, Literal, TypeVar

PlayerId = TypeVar("PlayerId")
TeamPair = tuple[PlayerId, PlayerId]
MatchPair = tuple[TeamPair, TeamPair]

MIN_PARTICIPANTS = 4


@dataclass
class TeamsFormed(Generic[PlayerId]):
    teams: list[TeamPair]
    new_waiting: PlayerId | None


@dataclass
class MatchesFormed(Generic[PlayerId]):
    matches: list[MatchPair]
    bye_team: TeamPair | None


RoundOutcomeKind = Literal["terminal", "defer", "in_progress"]


@dataclass
class RoundOutcome(Generic[PlayerId]):
    kind: RoundOutcomeKind
    champion_team: TeamPair | None = None
    excluded_player: PlayerId | None = None
    carry_pool: list[PlayerId] = field(default_factory=list)
    teams: list[TeamPair] = field(default_factory=list)
    matches: list[MatchPair] = field(default_factory=list)
    bye_team: TeamPair | None = None
    new_waiting: PlayerId | None = None


def form_teams(pool: list[PlayerId], rng: random.Random) -> TeamsFormed[PlayerId]:
    """Randomly pair up players into 2-person teams.

    If ``pool`` has an odd length, one randomly chosen player is left
    unpaired (``new_waiting``) and carried over to the next round instead of
    being forced onto a team.
    """
    shuffled = list(pool)
    rng.shuffle(shuffled)

    new_waiting: PlayerId | None = None
    if len(shuffled) % 2 == 1:
        new_waiting = shuffled.pop()

    teams = [(shuffled[i], shuffled[i + 1]) for i in range(0, len(shuffled), 2)]
    return TeamsFormed(teams=teams, new_waiting=new_waiting)


def form_matches(teams: list[TeamPair], rng: random.Random) -> MatchesFormed[PlayerId]:
    """Randomly pair up teams into matches.

    If ``teams`` has an odd length, one randomly chosen team is given a bye
    (auto-advances without playing).
    """
    shuffled = list(teams)
    rng.shuffle(shuffled)

    bye_team: TeamPair | None = None
    if len(shuffled) % 2 == 1:
        bye_team = shuffled.pop()

    matches = [(shuffled[i], shuffled[i + 1]) for i in range(0, len(shuffled), 2)]
    return MatchesFormed(matches=matches, bye_team=bye_team)


def resolve_round(
    pool: list[PlayerId],
    waiting: PlayerId | None,
    more_players_possible: bool,
    rng: random.Random,
) -> RoundOutcome[PlayerId]:
    """Decide what happens next for one bracket (WB or LB) given its current pool.

    ``pool`` is the set of individual players eligible to be paired this
    round (fresh winners, or new losers merging in). ``waiting`` is a player
    carried over from a previous round who still needs a partner.
    ``more_players_possible`` must be True whenever this bracket could still
    receive additional players later (e.g. LB while WB is still running) --
    it gates BOTH the pool-size-2 and pool-size-3 terminal rules. Without
    this gate, a bracket that happens to reduce to exactly 2 players while
    more losers are still due to drop in later would crown a champion
    prematurely and silently strand those future arrivals with no one left
    to play -- committing to a champion is only safe once no one else can
    ever join.
    """
    merged = list(pool) + ([waiting] if waiting is not None else [])

    if len(merged) in (2, 3):
        if more_players_possible:
            # Defer: keep everyone as individuals, try again once more players arrive.
            return RoundOutcome(kind="defer", carry_pool=merged)
        if len(merged) == 2:
            return RoundOutcome(kind="terminal", champion_team=(merged[0], merged[1]))
        shuffled = list(merged)
        rng.shuffle(shuffled)
        champion = (shuffled[0], shuffled[1])
        excluded = shuffled[2]
        return RoundOutcome(kind="terminal", champion_team=champion, excluded_player=excluded)

    if len(merged) < 2:
        # No one left to play (should not occur given valid callers); treat as a no-op defer.
        return RoundOutcome(kind="defer", carry_pool=merged)

    teams_formed = form_teams(merged, rng)
    matches_formed = form_matches(teams_formed.teams, rng)

    return RoundOutcome(
        kind="in_progress",
        teams=teams_formed.teams,
        matches=matches_formed.matches,
        bye_team=matches_formed.bye_team,
        new_waiting=teams_formed.new_waiting,
    )


def merge_losers_into_lb(carry_pool: list[PlayerId], new_losers: list[PlayerId]) -> list[PlayerId]:
    """Merge LB survivors carried over from the previous LB round with newly
    dropped WB losers into a single pool for the next resolve_round call."""
    return list(carry_pool) + list(new_losers)


def form_grand_final(wb_champion: TeamPair, lb_champion: TeamPair) -> tuple[PlayerId, PlayerId, PlayerId, PlayerId]:
    """The 4 grand-final players: 2 from the WB champion team, 2 from the LB champion team."""
    return (wb_champion[0], wb_champion[1], lb_champion[0], lb_champion[1])


def bracket_reset_teams(
    four_players: tuple[PlayerId, PlayerId, PlayerId, PlayerId], rng: random.Random
) -> tuple[TeamPair, TeamPair]:
    """Reshuffle the 4 grand-final players into 2 brand-new random teams for the reset match."""
    shuffled = list(four_players)
    rng.shuffle(shuffled)
    return (shuffled[0], shuffled[1]), (shuffled[2], shuffled[3])
