from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class TournamentType(str, Enum):
    SINGLE_ELIMINATION = "single_elimination"
    DOUBLE_ELIMINATION = "double_elimination"

class MatchStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Participant(BaseModel):
    id: str
    name: str
    seed: int

class Match(BaseModel):
    id: str
    round_index: int
    bracket_type: str = "winner"  # "winner" or "loser"
    participant1: Optional[Participant] = None
    participant2: Optional[Participant] = None
    score1: int = 0
    score2: int = 0
    winner_id: Optional[str] = None
    status: MatchStatus = MatchStatus.PENDING
    next_match_id: Optional[str] = None

class Tournament(BaseModel):
    id: str
    name: str
    tournament_type: TournamentType
    participants: List[Participant]
    matches: List[Match]
    is_completed: bool = False
