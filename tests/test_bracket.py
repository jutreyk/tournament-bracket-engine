import pytest
from app.models.schemas import Participant
from app.core.bracket import BracketEngine

def test_single_elimination_generation():
    participants = [
        Participant(id="p1", name="Alpha Team", seed=1),
        Participant(id="p2", name="Beta Squad", seed=2),
        Participant(id="p3", name="Gamma Force", seed=3),
        Participant(id="p4", name="Delta Legion", seed=4),
    ]

    tournament = BracketEngine.generate_single_elimination("test-1", "Summer Championship", participants)
    assert tournament.id == "test-1"
    assert len(tournament.matches) == 3  # 2 semifinals + 1 final

    # Check semifinal match seeds (1 vs 4, 2 vs 3)
    semifinals = [m for m in tournament.matches if m.round_index == 1]
    assert len(semifinals) == 2
    
    m1 = semifinals[0]
    assert m1.participant1.id == "p1"
    assert m1.participant2.id == "p4"

def test_match_advancement_and_completion():
    participants = [
        Participant(id="p1", name="Alpha Team", seed=1),
        Participant(id="p2", name="Beta Squad", seed=2),
    ]

    tournament = BracketEngine.generate_single_elimination("test-2", "Duel Finals", participants)
    match = tournament.matches[0]
    
    # Update score
    updated = BracketEngine.update_match_score(tournament, match.id, 2, 1)
    assert updated.matches[0].winner_id == "p1"
    assert updated.is_completed is True
