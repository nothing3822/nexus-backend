from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ════════════════════════════════════════════════════════════
# USER SCHEMAS
# ════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    bio: Optional[str] = None


class GuestCreate(BaseModel):
    username: Optional[str] = None


class UserUpdate(BaseModel):
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserOut(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_guest: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


# ════════════════════════════════════════════════════════════
# ROOM SCHEMAS
# ════════════════════════════════════════════════════════════

class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    room_type: str = "group"   # group | direct | temporary


class RoomOut(BaseModel):
    id: str
    name: Optional[str]
    description: Optional[str]
    room_type: str
    avatar_url: Optional[str]
    is_active: bool
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════
# MESSAGE SCHEMAS
# ════════════════════════════════════════════════════════════

class MessageOut(BaseModel):
    id: str
    room_id: str
    sender_id: str
    content: Optional[str]
    message_type: str
    file_url: Optional[str]
    reply_to_id: Optional[str]
    is_pinned: bool
    is_deleted: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════
# INVITE SCHEMAS
# ════════════════════════════════════════════════════════════

class InviteCreate(BaseModel):
    room_id: str
    expiry_hours: Optional[int] = 24    # None = never expire
    max_uses: Optional[int] = None      # None = unlimited
    password: Optional[str] = None
    is_one_time: bool = False


class InviteJoin(BaseModel):
    password: Optional[str] = None


class InviteOut(BaseModel):
    id: str
    code: str
    room_id: str
    created_by: str
    is_one_time: bool
    max_uses: Optional[int]
    use_count: int
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
