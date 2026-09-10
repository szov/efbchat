import uuid
import asyncio
import time
from pydantic import BaseModel
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from server import models
from server.database import AsyncSessionLocal
from server.database import Base, engine
from server.helpers import get_or_create_user, add_match, add_message, get_history, infer_name, fetch_contacts


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def cleanup_pending():
        while True:
            await asyncio.sleep(10)
            now = time.time()
            for key in list(pending_matches):
                if now - pending_matches[key]["ts"] > 60:
                    del pending_matches[key]

            for room_id, room in list(rooms.items()):
                stale_at = room.get("stale_at")
                if stale_at and now - stale_at > 30:
                    for ws_key in ("p1_ws", "p2_ws"):
                        other_ws = room.get(ws_key)
                        if other_ws:
                            try:
                                await other_ws.send_json({"type": "disconnected"})
                            except Exception:
                                pass
                    del rooms[room_id]

    # have to create a task for a while loop, else it will be running forever and our server would never start.
    task = asyncio.create_task(cleanup_pending())
    yield
    task.cancel()


# Initialize app
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_connections: dict[str, WebSocket] = {}
pending_matches: dict[tuple[str, str], dict] = {}
rooms: dict[str, dict] = {}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket,
                             device_id: str = Query(...)) -> None:
    """
    Connects users and maintains their connection and handles the chat loop.

    :param websocket: WebSocket
    :param device_id: str
    :return:
    """
    print(f"{device_id} connected")
    await websocket.accept()

    # Add user to chat_connections
    chat_connections[device_id] = websocket

    # Check if this device is reconnecting to a stale room
    reconnected_room_id = None
    reconnected_partner = None
    for room_id, room in rooms.items():
        if room.get("stale_p1") and room["p1_user"].device_id == device_id:
            room["p1_ws"] = websocket
            room.pop("stale_p1", None)
            reconnected_partner = room["p2_user"]
            reconnected_room_id = room_id
            break
        elif room.get("stale_p2") and room["p2_user"].device_id == device_id:
            room["p2_ws"] = websocket
            room.pop("stale_p2", None)
            reconnected_partner = room["p1_user"]
            reconnected_room_id = room_id
            break

    if reconnected_room_id:
        rooms[reconnected_room_id].pop("stale_at", None)
        async with AsyncSessionLocal() as db:
            await websocket.send_json({"type": "paired", "matchId": reconnected_room_id})
            user = (await db.execute(
                select(models.User).where(models.User.device_id == device_id)
            )).scalar_one_or_none()
            if user:
                history = await get_history(db, user, reconnected_partner)
                await websocket.send_json({"type": "history", "messages": history})

        other_ws = rooms[reconnected_room_id]["p2_ws"] if websocket == rooms[reconnected_room_id]["p1_ws"] else rooms[reconnected_room_id]["p1_ws"]
        if other_ws:
            try:
                await other_ws.send_json({"type": "opponent_reconnected"})
            except Exception:
                pass

    # Message handling loop
    async with AsyncSessionLocal() as db:
        try:
            while True:
                msg = await websocket.receive_text()

                for room_id, room in rooms.items():
                    # Identify websockets
                    if websocket in (room.get("p1_ws"), room.get("p2_ws")):
                        other_ws = room["p2_ws"] if websocket == room["p1_ws"] else room["p1_ws"]
                        sender = room["p1_user"] if websocket == room["p1_ws"] else room["p2_user"]
                        saved = await add_message(db, room_id, sender, msg)
                        await websocket.send_json(
                            {"type": "chat", "sender": "You", "content": msg, "id": saved.msg_id, "ts": saved.ts})

                        display_name = room["p2_user"].username if sender == room["p1_user"] else room[
                            "p1_user"].username

                        if other_ws:
                            await other_ws.send_json(
                                {"type": "chat", "sender": display_name, "content": msg, "id": saved.msg_id,
                                 "ts": saved.ts})
                        break

        except WebSocketDisconnect:
            for did, ws in list(chat_connections.items()):
                if ws == websocket:
                    del chat_connections[did]
                    break

        for room_id, room in list(rooms.items()):
            if websocket in (room.get("p1_ws"), room.get("p2_ws")):
                if websocket == room["p1_ws"]:
                    room["p1_ws"] = None
                    room["stale_p1"] = True
                    other_ws = room.get("p2_ws")
                else:
                    room["p2_ws"] = None
                    room["stale_p2"] = True
                    other_ws = room.get("p1_ws")

                room["stale_at"] = time.time()

                if other_ws:
                    try:
                        await other_ws.send_json({"type": "opponent_reconnecting"})
                    except Exception:
                        pass
                break


class MatchEvent(BaseModel):
    device_id: str
    left: str
    right: str


@app.post("/bot/match")
async def receive_match(data: MatchEvent) -> dict:
    """
    Once players match, they will POST this endpoint once the OCR detection goes off. they will then be assigned a room.
    The manual testing button will trigger also this. (temp)
    :param data:
    :return: The status update as well as dependent room id
    """

    # Standardize the names and sort them. this is done so when matching later on, it will match 1:1 instead of having
    # names accidentally opposite.
    key = tuple(sorted([data.left.strip().lower(), data.right.strip().lower()]))

    async with AsyncSessionLocal() as db:
        if key in pending_matches:
            other = pending_matches.pop(key)
            my_ws = chat_connections.get(data.device_id)
            other_ws = chat_connections.get(other["device_id"])

            if not my_ws or not other_ws:
                return {"status": "chat_not_connected"}

            # Ensure both users exist and fetch their rows
            user1 = await get_or_create_user(db, data.device_id)
            user2 = await get_or_create_user(db, other["device_id"])

            # Allocate and randomize room id and place both users in there
            room_id = str(uuid.uuid4())[:8]
            rooms[room_id] = {
                "p1_ws": my_ws, "p1_user": user1,
                "p2_ws": other_ws, "p2_user": user2,
            }

            # Send pairing signal
            await my_ws.send_json({"type": "paired", "matchId": room_id, "partner_id": user2.user_id})
            await other_ws.send_json({"type": "paired", "matchId": room_id, "partner_id": user1.user_id})

            # Register match into database
            await add_match(db, user1, user2, room_id, data.left, data.right)

            # Check the anonymity rule
            observed_names = {data.left, data.right}
            await infer_name(db, data.device_id, observed_names)
            await infer_name(db, other["device_id"], observed_names)

            await db.refresh(user1)
            await db.refresh(user2)

            # Get message history between both players
            history1 = await get_history(db, user1, user2)
            history2 = await get_history(db, user2, user1)

            # Send the history signal
            await my_ws.send_json({"type": "history", "messages": history1})
            await other_ws.send_json({"type": "history", "messages": history2})

            # Return the status and room_id
            return {"status": "paired", "room_id": room_id}

        else:
            # Append to pending_matches if not already there, the user they connected with will call this once more and connect them.
            pending_matches[key] = {"device_id": data.device_id, "ts": time.time()}
            return {"status": "waiting"}


@app.get('/contacts')
async def get_contacts(device_id: str = Query(...)):
    """
    Returns all contacts for that specific user
    :param device_id:
    :return:
    """
    async with AsyncSessionLocal() as db:
        return await fetch_contacts(db, device_id)


@app.get('/history')
async def get_history_endpoint(device_id: str = Query(...), partner_id: str = Query(...)):
    """
    Returns the history of chats between two users
    :param device_id:
    :param partner_id:
    :return:
    """
    async with AsyncSessionLocal() as db:
        user = (await db.execute(
            select(models.User).where(models.User.device_id == device_id)
        )).scalar_one_or_none()
        partner = (await db.execute(
            select(models.User).where(models.User.user_id == partner_id)
        )).scalar_one_or_none()
        if not user or not partner:
            return []
        return await get_history(db, user, partner)
