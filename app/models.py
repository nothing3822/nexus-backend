from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


def gen_id():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id            = Column(String, primary_key=True, default=gen_id)
    name          = Column(String(100), nullable=True)
    username      = Column(String(50), unique=True, nullable=False, index=True)
    email         = Column(String(255), unique=True, nullable=True)
    password_hash = Column(Text, nullable=True)
    avatar_base64 = Column(Text, nullable=True)
    bio           = Column(String(300), default="")
    custom_status = Column(String(100), nullable=True)
    email_public       = Column(Boolean, default=False)
    searchable         = Column(Boolean, default=True)
    profile_setup_done = Column(Boolean, default=False)
    notifications_on   = Column(Boolean, default=True)
    is_guest      = Column(Boolean, default=False)
    is_active     = Column(Boolean, default=True)
    status        = Column(String(20), default="offline")
    last_seen     = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    messages         = relationship("Message", back_populates="sender")
    room_memberships = relationship("RoomMember", back_populates="user")
    invite_links     = relationship("InviteLink", back_populates="creator", foreign_keys="InviteLink.created_by")


class Room(Base):
    __tablename__ = "rooms"

    id          = Column(String, primary_key=True, default=gen_id)
    name        = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)
    room_type   = Column(String(20), default="group")
    avatar_url  = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True)
    created_by  = Column(String, ForeignKey("users.id"))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    members      = relationship("RoomMember", back_populates="room", cascade="all, delete-orphan")
    messages     = relationship("Message", back_populates="room", cascade="all, delete-orphan")
    invite_links = relationship("InviteLink", back_populates="room", foreign_keys="InviteLink.room_id")


class RoomMember(Base):
    __tablename__ = "room_members"

    id        = Column(String, primary_key=True, default=gen_id)
    room_id   = Column(String, ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    user_id   = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role      = Column(String(20), default="member")
    is_muted  = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("Room", back_populates="members")
    user = relationship("User", back_populates="room_memberships")


class Message(Base):
    __tablename__ = "messages"

    id           = Column(String, primary_key=True, default=gen_id)
    room_id      = Column(String, ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    sender_id    = Column(String, ForeignKey("users.id"), index=True)
    content      = Column(Text, nullable=True)
    message_type = Column(String(20), default="text")
    file_url     = Column(Text, nullable=True)
    reply_to_id  = Column(String, ForeignKey("messages.id"), nullable=True)
    is_pinned    = Column(Boolean, default=False)
    is_deleted   = Column(Boolean, default=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    edited_at    = Column(DateTime(timezone=True), nullable=True)

    sender        = relationship("User", back_populates="messages")
    room          = relationship("Room", back_populates="messages")
    reply_to      = relationship("Message", remote_side="Message.id")
    read_receipts = relationship("ReadReceipt", back_populates="message", cascade="all, delete-orphan")


class ReadReceipt(Base):
    __tablename__ = "read_receipts"

    id         = Column(String, primary_key=True, default=gen_id)
    message_id = Column(String, ForeignKey("messages.id", ondelete="CASCADE"))
    user_id    = Column(String, ForeignKey("users.id"))
    read_at    = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", back_populates="read_receipts")


class InviteLink(Base):
    __tablename__ = "invite_links"

    id             = Column(String, primary_key=True, default=gen_id)
    code           = Column(String(32), unique=True, nullable=False, index=True)
    room_id        = Column(String, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=True)
    target_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_by     = Column(String, ForeignKey("users.id"))
    password_hash  = Column(String(255), nullable=True)
    is_one_time    = Column(Boolean, default=True)
    max_uses       = Column(Integer, nullable=True)
    use_count      = Column(Integer, default=0)
    is_active      = Column(Boolean, default=True)
    expires_at     = Column(DateTime(timezone=True), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    room    = relationship("Room", back_populates="invite_links", foreign_keys=[room_id])
    creator = relationship("User", back_populates="invite_links", foreign_keys=[created_by])


class Connection(Base):
    __tablename__ = "connections"

    id          = Column(String, primary_key=True, default=gen_id)
    sender_id   = Column(String, ForeignKey("users.id"), index=True)
    receiver_id = Column(String, ForeignKey("users.id"), index=True)
    status      = Column(String(20), default="pending")
    dm_room_id  = Column(String, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class Block(Base):
    __tablename__ = "blocks"

    id         = Column(String, primary_key=True, default=gen_id)
    blocker_id = Column(String, ForeignKey("users.id"), index=True)
    blocked_id = Column(String, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(String, primary_key=True, default=gen_id)
    user_id    = Column(String, ForeignKey("users.id"), index=True)
    type       = Column(String(50))
    title      = Column(String(200))
    body       = Column(String(500))
    is_read    = Column(Boolean, default=False)
    ref_id     = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
