from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey
from datetime import datetime, timezone
import uuid
from server.database import Base


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    device_id: Mapped[str] = mapped_column(String, unique=True)
    username: Mapped[str] = mapped_column(String, default=lambda: f"Anonymous-{uuid.uuid4().hex[:8]}"
                                          , unique=True)


class Match(Base):
    __tablename__ = "matches"
    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_a_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"))
    user_b_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"))
    left_name: Mapped[str] = mapped_column(String)
    right_name: Mapped[str] = mapped_column(String)
    created_at: Mapped[int] = mapped_column(Integer, default=lambda: int(datetime.now(timezone.utc).timestamp()))


class Message(Base):
    __tablename__ = "messages"

    msg_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    match_id: Mapped[str] = mapped_column(String, ForeignKey("matches.match_id"))
    sender_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"))
    content: Mapped[str] = mapped_column(String)
    ts: Mapped[int] = mapped_column(Integer, default=lambda: int(datetime.now(timezone.utc).timestamp()))
