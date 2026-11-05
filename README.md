# tournament-bracket-engine

Full-stack tournament operations API and bracket engine built with **FastAPI**, **Pydantic v2**, and **WebSockets**. Features algorithmic single-elimination bracket generation, seed distribution, automated round advancement, and real-time live score broadcast.

## Architecture

- **Mathematical Seeding**: Automatically expands participant pools to the nearest power of 2 ($2^{\lceil \log_2 N \rceil}$), distributes top seeds according to standard 1-vs-$N$ competitive patterns, and handles by-passes.
- **Round Advancement**: Graph of match dependencies advancing winning nodes directly to parent matches upon score submission.
- **Real-Time WebSocket Hub**: Broadcasts live match updates to connected clients (`/ws/tournaments/{id}`).
- **Production Containerization**: Multi-stage `Dockerfile` and `docker-compose.yml`.

## API Spec

- `POST /api/v1/tournaments` — Generate a tournament bracket from seeded participants.
- `GET /api/v1/tournaments/{id}` — Retrieve full bracket state and match tree.
- `POST /api/v1/tournaments/{id}/matches/{match_id}/score` — Submit scores and trigger advancement.
- `WS /ws/tournaments/{id}` — Real-time live score push channel.

## Quickstart

```bash
# Run tests
python -m pytest

# Start API server
uvicorn app.main:app --reload --port 8000
```

## License

MIT © [Arkadiy Gazizov](https://arkadiygazizov.ru)
