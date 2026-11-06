import math
import uuid
from enum import Enum
from typing import Optional, List, Dict, Set
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

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
    bracket_type: str = "winner"
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
    participants: List[Participant]
    matches: List[Match]
    is_completed: bool = False

class BracketEngine:
    @staticmethod
    def generate(tournament_id: str, name: str, participants: List[Participant]) -> Tournament:
        n = len(participants)
        if n < 2:
            raise ValueError("Минимум 2 участника")
        sorted_p = sorted(participants, key=lambda p: p.seed)
        size = 2 ** math.ceil(math.log2(n))
        total_rounds = int(math.log2(size))

        rounds_map = {}
        all_matches = []

        final = Match(id=f"{tournament_id}-R{total_rounds}-M1", round_index=total_rounds)
        rounds_map[total_rounds] = [final]
        all_matches.append(final)

        for r in range(total_rounds - 1, 0, -1):
            num_m = 2 ** (total_rounds - r)
            curr = []
            nxt = rounds_map[r + 1]
            for m in range(num_m):
                match = Match(
                    id=f"{tournament_id}-R{r}-M{m+1}",
                    round_index=r,
                    next_match_id=nxt[m // 2].id
                )
                curr.append(match)
                all_matches.append(match)
            rounds_map[r] = curr

        for i, m in enumerate(rounds_map[1]):
            p1_idx = i
            p2_idx = size - 1 - i
            if p1_idx < n:
                m.participant1 = sorted_p[p1_idx]
            if p2_idx < n:
                m.participant2 = sorted_p[p2_idx]
            if m.participant1 and not m.participant2:
                m.winner_id = m.participant1.id
                m.status = MatchStatus.COMPLETED
                BracketEngine._advance(m, all_matches)

        return Tournament(id=tournament_id, name=name, participants=participants, matches=all_matches)

    @staticmethod
    def update_score(tournament: Tournament, match_id: str, s1: int, s2: int) -> Tournament:
        match = next((m for m in tournament.matches if m.id == match_id), None)
        if not match:
            raise KeyError(f"Матч {match_id} не найден")
        if not match.participant1 or not match.participant2:
            raise ValueError("Матч еще не готов к проведению")

        match.score1 = s1
        match.score2 = s2
        if s1 > s2:
            match.winner_id = match.participant1.id
            match.status = MatchStatus.COMPLETED
        elif s2 > s1:
            match.winner_id = match.participant2.id
            match.status = MatchStatus.COMPLETED
        else:
            match.status = MatchStatus.IN_PROGRESS
            return tournament

        BracketEngine._advance(match, tournament.matches)
        finals = [m for m in tournament.matches if m.next_match_id is None]
        if all(f.status == MatchStatus.COMPLETED for f in finals):
            tournament.is_completed = True
        return tournament

    @staticmethod
    def _advance(match: Match, all_matches: List[Match]):
        if not match.next_match_id or not match.winner_id:
            return
        nxt = next((m for m in all_matches if m.id == match.next_match_id), None)
        if not nxt:
            return
        winner = match.participant1 if match.winner_id == match.participant1.id else match.participant2
        if nxt.participant1 is None:
            nxt.participant1 = winner
        elif nxt.participant2 is None:
            nxt.participant2 = winner

class WSManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, room: str, ws: WebSocket):
        await ws.accept()
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(ws)

    def disconnect(self, room: str, ws: WebSocket):
        if room in self.rooms:
            self.rooms[room].discard(ws)

    async def broadcast(self, room: str, message: dict):
        if room in self.rooms:
            dead = set()
            for ws in self.rooms[room]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.add(ws)
            for ws in dead:
                self.rooms[room].discard(ws)

ws_hub = WSManager()
db: Dict[str, Tournament] = {}

app = FastAPI(title="Tournament Bracket Engine")

class CreateTournamentRequest(BaseModel):
    name: str = "Championship 2026"
    participants: Optional[List[Participant]] = None

@app.post("/api/v1/tournaments", status_code=201)
async def create_tournament(req: Optional[CreateTournamentRequest] = None):
    name = req.name if req and req.name else "Championship 2026"
    participants = req.participants if req and req.participants else [
        Participant(id="p1", name="Команда 1", seed=1),
        Participant(id="p2", name="Команда 2", seed=2),
        Participant(id="p3", name="Команда 3", seed=3),
        Participant(id="p4", name="Команда 4", seed=4)
    ]
    t_id = f"tour-{str(uuid.uuid4())[:8]}"
    tournament = BracketEngine.generate(t_id, name, participants)
    db[t_id] = tournament
    return tournament

@app.get("/api/v1/tournaments/{tournament_id}")
async def get_tournament(tournament_id: str):
    if tournament_id not in db:
        raise HTTPException(status_code=404, detail="Турнир не найден")
    return db[tournament_id]

@app.post("/api/v1/tournaments/{tournament_id}/matches/{match_id}/score")
async def record_score(tournament_id: str, match_id: str, score1: int, score2: int):
    if tournament_id not in db:
        raise HTTPException(status_code=404, detail="Турнир не найден")
    tournament = db[tournament_id]
    try:
        updated = BracketEngine.update_score(tournament, match_id, score1, score2)
        db[tournament_id] = updated
        await ws_hub.broadcast(tournament_id, {
            "event": "SCORE_UPDATE",
            "match_id": match_id,
            "score1": score1,
            "score2": score2,
            "tournament": updated.model_dump()
        })
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.websocket("/ws/tournaments/{tournament_id}")
async def live_stream(websocket: WebSocket, tournament_id: str):
    await ws_hub.connect(tournament_id, websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_hub.disconnect(tournament_id, websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
