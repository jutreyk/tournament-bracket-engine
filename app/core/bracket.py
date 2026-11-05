import math
import uuid
from typing import List, Optional
from app.models.schemas import Participant, Match, MatchStatus, TournamentType, Tournament

class BracketEngine:
    """Mathematical tournament bracket generator and state advancement engine."""
    
    @staticmethod
    def generate_single_elimination(tournament_id: str, name: str, participants: List[Participant]) -> Tournament:
        n = len(participants)
        if n < 2:
            raise ValueError("Tournament requires at least 2 participants")
            
        # Sort participants by seed
        sorted_participants = sorted(participants, key=lambda p: p.seed)
        
        # Round up to nearest power of 2
        bracket_size = 2 ** math.ceil(math.log2(n))
        total_rounds = int(math.log2(bracket_size))
        
        # Create standard bracket match nodes backwards from final
        matches_by_round = {}
        all_matches = []
        
        # Generate round matches from finals (round total_rounds - 1) down to round 0
        match_counter = 1
        
        # Finals round
        final_match = Match(
            id=f"{tournament_id}-R{total_rounds}-M1",
            round_index=total_rounds,
            bracket_type="winner",
            status=MatchStatus.PENDING
        )
        matches_by_round[total_rounds] = [final_match]
        all_matches.append(final_match)
        
        for r in range(total_rounds - 1, 0, -1):
            num_matches = 2 ** (total_rounds - r)
            current_round_matches = []
            next_round_matches = matches_by_round[r + 1]
            
            for m in range(num_matches):
                parent_match = next_round_matches[m // 2]
                new_match = Match(
                    id=f"{tournament_id}-R{r}-M{m+1}",
                    round_index=r,
                    bracket_type="winner",
                    status=MatchStatus.PENDING,
                    next_match_id=parent_match.id
                )
                current_round_matches.append(new_match)
                all_matches.append(new_match)
            matches_by_round[r] = current_round_matches
            
        # Seed first round matches (Standard 1 vs N, 2 vs N-1 seeding pattern)
        round_1_matches = matches_by_round[1]
        for i, match in enumerate(round_1_matches):
            p1_idx = i
            p2_idx = bracket_size - 1 - i
            
            if p1_idx < n:
                match.participant1 = sorted_participants[p1_idx]
            if p2_idx < n:
                match.participant2 = sorted_participants[p2_idx]
                
            # If by-pass (only one participant)
            if match.participant1 and not match.participant2:
                match.winner_id = match.participant1.id
                match.status = MatchStatus.COMPLETED
                BracketEngine._advance_winner(match, all_matches)

        return Tournament(
            id=tournament_id,
            name=name,
            tournament_type=TournamentType.SINGLE_ELIMINATION,
            participants=participants,
            matches=all_matches
        )

    @staticmethod
    def update_match_score(tournament: Tournament, match_id: str, score1: int, score2: int) -> Tournament:
        match = next((m for m in tournament.matches if m.id == match_id), None)
        if not match:
            raise KeyError(f"Match {match_id} not found")
            
        if not match.participant1 or not match.participant2:
            raise ValueError("Cannot score match with missing participants")
            
        match.score1 = score1
        match.score2 = score2
        
        if score1 > score2:
            match.winner_id = match.participant1.id
            match.status = MatchStatus.COMPLETED
        elif score2 > score1:
            match.winner_id = match.participant2.id
            match.status = MatchStatus.COMPLETED
        else:
            match.status = MatchStatus.IN_PROGRESS
            return tournament

        # Advance winner to next round
        BracketEngine._advance_winner(match, tournament.matches)
        
        # Check if final round is completed
        finals = [m for m in tournament.matches if m.next_match_id is None]
        if all(f.status == MatchStatus.COMPLETED for f in finals):
            tournament.is_completed = True
            
        return tournament

    @staticmethod
    def _advance_winner(completed_match: Match, all_matches: List[Match]):
        if not completed_match.next_match_id or not completed_match.winner_id:
            return
            
        next_match = next((m for m in all_matches if m.id == completed_match.next_match_id), None)
        if not next_match:
            return
            
        winner = (completed_match.participant1 
                  if completed_match.winner_id == completed_match.participant1.id 
                  else completed_match.participant2)
                  
        if next_match.participant1 is None:
            next_match.participant1 = winner
        elif next_match.participant2 is None:
            next_match.participant2 = winner
