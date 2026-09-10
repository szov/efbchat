# eFootball Chat (efbchat)

Pairs two eFootball players into a private chat when they meet in matchmaking.

How it works: an OCR watcher reads both player names from the matchmaking
screen and POSTs them to the server. When two watchers report the same pair,
the server pairs their WebSocket connections into a room and stores the
match plus message history in SQLite. The Tauri overlay is the chat UI.

## Stack

- Server: FastAPI + WebSockets, SQLAlchemy + SQLite (`server/`)
- Match detection: OpenCV + EasyOCR screen watcher (`watcher/detect.py`)
- Overlay UI: Tauri + Svelte + Vite (`overlay/`)

## Run

Needs Python 3.14+ with `uv`, and Node for the overlay.

```bash
uv sync
uv run uvicorn server.main:app --port 8000
```

```bash
uv run python watcher/detect.py
```

```bash
cd overlay && npm install && npm run tauri dev
```

## Notes

- OCR watcher and overlay are Windows-only (uses `pywin32` window capture).
