from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, List
import uuid
from app.models.schemas import Tournament, Participant, TournamentType
from app.core.bracket import BracketEngine
from app.core.ws_manager import manager

app = FastAPI(
    title="Tournament Bracket Engine",
    description="Full-stack tournament management API with automated bracket generation and real-time WebSocket match broadcasting.",
    version="1.0.0"
)

# In-memory database
tournaments_db: Dict[str, Tournament] = {}

@app.post("/api/v1/tournaments", response_model=Tournament, status_code=201)
async def create_tournament(name: str, participants: List[Participant]):
    tournament_id = f"tour-{str(uuid.uuid4())[:8]}"
    tournament = BracketEngine.generate_single_elimination(tournament_id, name, participants)
    tournaments_db[tournament_id] = tournament
    return tournament

@app.get("/api/v1/tournaments/{tournament_id}", response_model=Tournament)
async def get_tournament(tournament_id: str):
    if tournament_id not in tournaments_db:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournaments_db[tournament_id]

@app.post("/api/v1/tournaments/{tournament_id}/matches/{match_id}/score", response_model=Tournament)
async def record_score(tournament_id: str, match_id: str, score1: int, score2: int):
    if tournament_id not in tournaments_db:
        raise HTTPException(status_code=404, detail="Tournament not found")
        
    tournament = tournaments_db[tournament_id]
    try:
        updated = BracketEngine.update_match_score(tournament, match_id, score1, score2)
        tournaments_db[tournament_id] = updated
        
        # Broadcast match score event via WebSockets
        await manager.broadcast(tournament_id, {
            "event": "MATCH_UPDATED",
            "match_id": match_id,
            "score1": score1,
            "score2": score2,
            "tournament": updated.model_dump()
        })
        return updated
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.websocket("/ws/tournaments/{tournament_id}")
async def tournament_live_stream(websocket: WebSocket, tournament_id: str):
    await manager.connect(tournament_id, websocket)
    try:
        while True:
            # Keep-alive ping/pong
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(tournament_id, websocket)
