import enum


class TournamentStatus(str, enum.Enum):
    SETUP = "SETUP"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"


class TournamentFormat(str, enum.Enum):
    SINGLE_ELIMINATION = "SINGLE_ELIMINATION"
    DOUBLE_ELIMINATION = "DOUBLE_ELIMINATION"


class Bracket(str, enum.Enum):
    WINNERS = "WINNERS"
    LOSERS = "LOSERS"
    GRAND_FINAL = "GRAND_FINAL"


class RoundStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"


class MatchKind(str, enum.Enum):
    NORMAL = "NORMAL"
    TEAM_BYE = "TEAM_BYE"
    GRAND_FINAL = "GRAND_FINAL"
    GRAND_FINAL_RESET = "GRAND_FINAL_RESET"
