from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json, secrets, base64

from app.database import engine, Base, get_db
from app import models, auth, ws_manager

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nexus Chat API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=false, allow_methods=["*"], allow_headers=["*"])
manager = ws_manager.ConnectionManager()


# ── Dependency: token → User object ──────────────────────────
def get_user(user_id: str = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found")
    return user


# ════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ════════════════════════════════════════════════════════════
class SignupData(BaseModel):
    name: str
    username: str
    email: str
    password: str

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar_base64: Optional[str] = None
    email_public: Optional[bool] = None
    searchable: Optional[bool] = None
    notifications_on: Optional[bool] = None
    profile_setup_done: Optional[bool] = None

class RoomCreate(BaseModel):
    name: str
    room_type: str = "group"

class InviteCreate(BaseModel):
    room_id: Optional[str] = None
    expiry_hours: Optional[int] = 24
    max_uses: Optional[int] = 1
    is_one_time: bool = True

class InviteJoin(BaseModel):
    password: Optional[str] = None

class MsgRead(BaseModel):
    message_id: str


# ════════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════════
@app.post("/auth/signup")
def signup(data: SignupData, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == data.username).first():
        raise HTTPException(400, "Username already taken")
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    user = models.User(
        name=data.name,
        username=data.username,
        email=data.email,
        password_hash=auth.hash_password(data.password),
        profile_setup_done=False,   # Pehli baar → settings tab
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = auth.create_token(str(user.id))
    return {
        "access_token": token, "token_type": "bearer",
        "user": _user_dict(user), "go_to_settings": True
    }

@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form.username).first()
    if not user or not auth.verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    user.status = "online"
    db.commit()
    token = auth.create_token(str(user.id))
    return {
        "access_token": token, "token_type": "bearer",
        "user": _user_dict(user), "go_to_settings": not user.profile_setup_done
    }

@app.post("/auth/logout")
def logout(db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    current_user.status = "offline"
    db.commit()
    return {"message": "Logged out"}


def _user_dict(user):
    return {
        "id": str(user.id),
        "name": user.name,
        "username": user.username,
        "email": user.email if user.email_public else None,
        "email_full": user.email,   # sirf apne liye
        "avatar_base64": user.avatar_base64,
        "bio": user.bio,
        "status": user.status,
        "email_public": user.email_public,
        "searchable": user.searchable,
        "notifications_on": user.notifications_on,
        "profile_setup_done": user.profile_setup_done,
        "is_guest": user.is_guest,
        "created_at": str(user.created_at),
    }


# ════════════════════════════════════════════════════════════
# USER / PROFILE
# ════════════════════════════════════════════════════════════
@app.get("/users/me")
def get_me(current_user: models.User = Depends(get_user)):
    return _user_dict(current_user)

@app.patch("/users/me")
def update_profile(data: ProfileUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    if data.name is not None:
        current_user.name = data.name
    if data.bio is not None:
        current_user.bio = data.bio
    if data.avatar_base64 is not None:
        current_user.avatar_base64 = data.avatar_base64
    if data.email_public is not None:
        current_user.email_public = data.email_public
    if data.searchable is not None:
        current_user.searchable = data.searchable
    if data.notifications_on is not None:
        current_user.notifications_on = data.notifications_on
    if data.profile_setup_done is not None:
        current_user.profile_setup_done = data.profile_setup_done
    db.commit()
    db.refresh(current_user)
    return _user_dict(current_user)

@app.get("/users/find/{username}")
def find_user(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.is_active == True,
        models.User.searchable == True,       # Search restriction
    ).first()
    if not user:
        raise HTTPException(404, "User not found or has disabled search")
    if str(user.id) == str(current_user.id):
        raise HTTPException(400, "Apne aap ko connect nahi kar sakte")
    blocked = db.query(models.Block).filter_by(blocker_id=str(current_user.id), blocked_id=str(user.id)).first()
    if blocked:
        raise HTTPException(403, "Aapne is user ko block kiya hua hai")
    existing = db.query(models.Connection).filter(
        ((models.Connection.sender_id == str(current_user.id)) & (models.Connection.receiver_id == str(user.id))) |
        ((models.Connection.sender_id == str(user.id)) & (models.Connection.receiver_id == str(current_user.id)))
    ).first()
    return {
        "id": str(user.id),
        "name": user.name,
        "username": user.username,
        "bio": user.bio,
        "status": user.status,
        "avatar_base64": user.avatar_base64,
        "connection_status": existing.status if existing else "none",
    }


# ════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ════════════════════════════════════════════════════════════
def create_notification(db, user_id, type_, title, body, ref_id=None):
    notif = models.Notification(user_id=user_id, type=type_, title=title, body=body, ref_id=ref_id)
    db.add(notif)
    db.commit()

@app.get("/notifications")
def get_notifications(db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    notifs = db.query(models.Notification).filter_by(user_id=str(current_user.id)).order_by(models.Notification.created_at.desc()).limit(50).all()
    return [{"id": n.id, "type": n.type, "title": n.title, "body": n.body, "is_read": n.is_read, "ref_id": n.ref_id, "created_at": str(n.created_at)} for n in notifs]

@app.get("/notifications/unread-count")
def unread_notif_count(db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    count = db.query(models.Notification).filter_by(user_id=str(current_user.id), is_read=False).count()
    return {"count": count}

@app.post("/notifications/read-all")
def read_all_notifications(db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    db.query(models.Notification).filter_by(user_id=str(current_user.id), is_read=False).update({"is_read": True})
    db.commit()
    return {"message": "All read"}


# ════════════════════════════════════════════════════════════
# ROOMS
# ════════════════════════════════════════════════════════════
@app.post("/rooms", status_code=201)
def create_room(data: RoomCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    room = models.Room(name=data.name, room_type=data.room_type, created_by=str(current_user.id))
    db.add(room)
    db.commit()
    db.refresh(room)
    db.add(models.RoomMember(room_id=str(room.id), user_id=str(current_user.id), role="admin"))
    db.commit()
    return {"id": room.id, "name": room.name, "room_type": room.room_type, "created_at": str(room.created_at)}

@app.get("/rooms")
def my_rooms(db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    memberships = db.query(models.RoomMember).filter_by(user_id=str(current_user.id)).all()
    room_ids = [m.room_id for m in memberships]
    rooms = db.query(models.Room).filter(models.Room.id.in_(room_ids), models.Room.is_active == True).all()
    return [{"id": r.id, "name": r.name, "room_type": r.room_type, "created_at": str(r.created_at)} for r in rooms]

@app.delete("/rooms/{room_id}")
def close_room(room_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    room = db.query(models.Room).filter_by(id=room_id).first()
    if not room or room.created_by != str(current_user.id):
        raise HTTPException(403, "Not authorized")
    room.is_active = False
    db.commit()
    return {"message": "Room closed"}


# ════════════════════════════════════════════════════════════
# MESSAGES
# ════════════════════════════════════════════════════════════
@app.get("/rooms/{room_id}/messages")
def get_messages(room_id: str, limit: int = 50, offset: int = 0, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    member = db.query(models.RoomMember).filter_by(room_id=room_id, user_id=str(current_user.id)).first()
    if not member:
        raise HTTPException(403, "Not a member")
    msgs = db.query(models.Message).filter(
        models.Message.room_id == room_id,
        models.Message.is_deleted == False
    ).order_by(models.Message.created_at.desc()).offset(offset).limit(limit).all()
    result = []
    for m in reversed(msgs):
        # Seen by kitno ne
        seen_count = db.query(models.ReadReceipt).filter_by(message_id=m.id).count()
        seen_by_me = db.query(models.ReadReceipt).filter_by(message_id=m.id, user_id=str(current_user.id)).first() is not None
        result.append({
            "id": m.id, "room_id": m.room_id, "sender_id": m.sender_id,
            "sender_username": m.sender.username if m.sender else "Unknown",
            "sender_name": m.sender.name if m.sender else "Unknown",
            "sender_avatar": m.sender.avatar_base64 if m.sender else None,
            "content": m.content, "message_type": m.message_type,
            "reply_to_id": m.reply_to_id, "is_pinned": m.is_pinned,
            "created_at": str(m.created_at),
            "seen_count": seen_count, "seen_by_me": seen_by_me,
        })
    return result

@app.post("/messages/{message_id}/seen")
def mark_seen(message_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    already = db.query(models.ReadReceipt).filter_by(message_id=message_id, user_id=str(current_user.id)).first()
    if not already:
        db.add(models.ReadReceipt(message_id=message_id, user_id=str(current_user.id)))
        db.commit()
    return {"ok": True}

@app.delete("/messages/{message_id}")
def delete_message(message_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    msg = db.query(models.Message).filter_by(id=message_id).first()
    if not msg or msg.sender_id != str(current_user.id):
        raise HTTPException(403, "Can only delete your own messages")
    msg.is_deleted = True
    msg.content = "This message was deleted"
    db.commit()
    return {"ok": True}


# ════════════════════════════════════════════════════════════
# INVITE LINKS
# ════════════════════════════════════════════════════════════
@app.post("/invites")
def create_invite(data: InviteCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    from datetime import datetime, timedelta
    expires_at = None
    if data.expiry_hours:
        expires_at = datetime.utcnow() + timedelta(hours=data.expiry_hours)
    invite = models.InviteLink(
        code=secrets.token_urlsafe(8),
        room_id=data.room_id,
        created_by=str(current_user.id),
        is_one_time=data.is_one_time,
        max_uses=data.max_uses,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return {"id": invite.id, "code": invite.code, "expires_at": str(invite.expires_at) if invite.expires_at else None, "is_one_time": invite.is_one_time}

@app.get("/invites/{code}/preview")
def preview_invite(code: str, db: Session = Depends(get_db)):
    invite = db.query(models.InviteLink).filter_by(code=code, is_active=True).first()
    if not invite:
        raise HTTPException(404, "Invite not found or expired")
    creator = db.query(models.User).filter_by(id=invite.created_by).first()
    room = db.query(models.Room).filter_by(id=invite.room_id).first() if invite.room_id else None
    return {
        "creator_username": creator.username if creator else "Unknown",
        "creator_name": creator.name if creator else "Unknown",
        "room_name": room.name if room else None,
        "is_one_time": invite.is_one_time,
        "expires_at": str(invite.expires_at) if invite.expires_at else None,
    }

@app.post("/invites/{code}/use")
def use_invite(code: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    from datetime import datetime
    invite = db.query(models.InviteLink).filter_by(code=code, is_active=True).first()
    if not invite:
        raise HTTPException(404, "Invite not found or already used")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        invite.is_active = False
        db.commit()
        raise HTTPException(410, "Invite link expired")
    if invite.max_uses and invite.use_count >= invite.max_uses:
        raise HTTPException(410, "Max uses reached")

    result = {}

    if invite.room_id:
        # Room join
        existing = db.query(models.RoomMember).filter_by(room_id=invite.room_id, user_id=str(current_user.id)).first()
        if not existing:
            db.add(models.RoomMember(room_id=invite.room_id, user_id=str(current_user.id)))
        result = {"type": "room", "room_id": invite.room_id}
    else:
        # Direct connect via invite
        sender_id = invite.created_by
        blocked = db.query(models.Block).filter(
            ((models.Block.blocker_id == sender_id) & (models.Block.blocked_id == str(current_user.id))) |
            ((models.Block.blocker_id == str(current_user.id)) & (models.Block.blocked_id == sender_id))
        ).first()
        if blocked:
            raise HTTPException(403, "Cannot connect")

        existing_conn = db.query(models.Connection).filter(
            ((models.Connection.sender_id == sender_id) & (models.Connection.receiver_id == str(current_user.id))) |
            ((models.Connection.sender_id == str(current_user.id)) & (models.Connection.receiver_id == sender_id))
        ).first()

        if existing_conn and existing_conn.status == "accepted":
            result = {"type": "dm", "room_id": existing_conn.dm_room_id}
        else:
            # Auto accept — invite se aa raha hai to trusted
            dm_room = models.Room(
                name=f"dm_{sender_id[:8]}_{current_user.id[:8]}",
                room_type="direct",
                created_by=sender_id,
            )
            db.add(dm_room)
            db.commit()
            db.refresh(dm_room)
            for uid in [sender_id, str(current_user.id)]:
                db.add(models.RoomMember(room_id=str(dm_room.id), user_id=uid))
            conn = models.Connection(sender_id=sender_id, receiver_id=str(current_user.id), status="accepted", dm_room_id=str(dm_room.id))
            db.add(conn)
            # Notification sender ko
            create_notification(db, sender_id, "connect_accepted", "New Connection!", f"{current_user.username} ne tumhara invite use kiya", str(dm_room.id))
            result = {"type": "dm", "room_id": str(dm_room.id)}

    invite.use_count += 1
    if invite.is_one_time:
        invite.is_active = False
    db.commit()
    return result


# ════════════════════════════════════════════════════════════
# CONNECT SYSTEM
# ════════════════════════════════════════════════════════════
@app.post("/connect/send/{username}")
def send_connect_request(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    target = db.query(models.User).filter_by(username=username).first()
    if not target:
        raise HTTPException(404, "User not found")
    if str(target.id) == str(current_user.id):
        raise HTTPException(400, "Apne aap ko connect nahi kar sakte")
    blocked = db.query(models.Block).filter(
        ((models.Block.blocker_id == str(target.id)) & (models.Block.blocked_id == str(current_user.id)))
    ).first()
    if blocked:
        raise HTTPException(403, "Ye user available nahi hai")
    existing = db.query(models.Connection).filter(
        ((models.Connection.sender_id == str(current_user.id)) & (models.Connection.receiver_id == str(target.id))) |
        ((models.Connection.sender_id == str(target.id)) & (models.Connection.receiver_id == str(current_user.id)))
    ).first()
    if existing:
        if existing.status == "accepted":
            raise HTTPException(400, "Pehle se connected hain")
        raise HTTPException(400, "Request already bheji ja chuki hai")
    conn = models.Connection(sender_id=str(current_user.id), receiver_id=str(target.id), status="pending")
    db.add(conn)
    # Notification
    create_notification(db, str(target.id), "connect_request", "Connect Request!", f"{current_user.username} ne connect request bheji", conn.id)
    db.commit()
    return {"message": f"{target.username} ko request bheji!"}

@app.post("/connect/accept/{connection_id}")
def accept_request(connection_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    conn = db.query(models.Connection).filter_by(id=connection_id).first()
    if not conn or conn.receiver_id != str(current_user.id):
        raise HTTPException(403, "Not authorized")
    conn.status = "accepted"
    dm_room = models.Room(name=f"dm_{conn.sender_id[:8]}_{conn.receiver_id[:8]}", room_type="direct", created_by=str(current_user.id))
    db.add(dm_room)
    db.commit()
    db.refresh(dm_room)
    for uid in [conn.sender_id, conn.receiver_id]:
        db.add(models.RoomMember(room_id=str(dm_room.id), user_id=uid))
    conn.dm_room_id = str(dm_room.id)
    # Notification sender ko
    create_notification(db, conn.sender_id, "connect_accepted", "Request Accept Ho Gayi!", f"{current_user.username} ne tumhari request accept kar li", str(dm_room.id))
    db.commit()
    return {"message": "Connected!", "room_id": str(dm_room.id)}

@app.post("/connect/reject/{connection_id}")
def reject_request(connection_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    conn = db.query(models.Connection).filter_by(id=connection_id).first()
    if not conn or conn.receiver_id != str(current_user.id):
        raise HTTPException(403, "Not authorized")
    db.delete(conn)
    db.commit()
    return {"message": "Reject kar di"}

@app.get("/connect/requests")
def pending_requests(db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    reqs = db.query(models.Connection).filter_by(receiver_id=str(current_user.id), status="pending").all()
    result = []
    for r in reqs:
        sender = db.query(models.User).filter_by(id=r.sender_id).first()
        result.append({"connection_id": r.id, "sender_id": r.sender_id, "sender_username": sender.username if sender else "?", "sender_name": sender.name if sender else "?", "sender_avatar": sender.avatar_base64 if sender else None})
    return result

@app.get("/connect/list")
def my_connections(db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    conns = db.query(models.Connection).filter(
        ((models.Connection.sender_id == str(current_user.id)) | (models.Connection.receiver_id == str(current_user.id))),
        models.Connection.status == "accepted"
    ).all()
    result = []
    for c in conns:
        other_id = c.receiver_id if c.sender_id == str(current_user.id) else c.sender_id
        other = db.query(models.User).filter_by(id=other_id).first()
        if other:
            result.append({"connection_id": c.id, "user_id": other_id, "username": other.username, "name": other.name, "bio": other.bio, "status": other.status, "avatar_base64": other.avatar_base64, "room_id": c.dm_room_id})
    return result

@app.post("/block/{username}")
def block_user(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    target = db.query(models.User).filter_by(username=username).first()
    if not target:
        raise HTTPException(404, "User not found")
    db.query(models.Connection).filter(
        ((models.Connection.sender_id == str(current_user.id)) & (models.Connection.receiver_id == str(target.id))) |
        ((models.Connection.sender_id == str(target.id)) & (models.Connection.receiver_id == str(current_user.id)))
    ).delete(synchronize_session=False)
    already = db.query(models.Block).filter_by(blocker_id=str(current_user.id), blocked_id=str(target.id)).first()
    if not already:
        db.add(models.Block(blocker_id=str(current_user.id), blocked_id=str(target.id)))
    db.commit()
    return {"message": f"{username} ko block kar diya"}

@app.post("/unblock/{username}")
def unblock_user(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    target = db.query(models.User).filter_by(username=username).first()
    if not target:
        raise HTTPException(404, "User not found")
    db.query(models.Block).filter_by(blocker_id=str(current_user.id), blocked_id=str(target.id)).delete()
    db.commit()
    return {"message": f"{username} ko unblock kar diya"}


# ════════════════════════════════════════════════════════════
# ADMIN STATS
# ════════════════════════════════════════════════════════════
@app.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db), current_user: models.User = Depends(get_user)):
    first_user = db.query(models.User).order_by(models.User.created_at).first()
    if not first_user or str(current_user.id) != str(first_user.id):
        raise HTTPException(403, "Admin only")
    return {
        "total_users": db.query(models.User).count(),
        "total_rooms": db.query(models.Room).count(),
        "total_messages": db.query(models.Message).count(),
        "users": [{"id": u.id, "name": u.name, "username": u.username, "email": u.email, "is_guest": u.is_guest, "status": u.status, "joined": str(u.created_at)} for u in db.query(models.User).order_by(models.User.created_at.desc()).all()]
    }


# ════════════════════════════════════════════════════════════
# WEBSOCKET
# ════════════════════════════════════════════════════════════
@app.websocket("/ws/{room_id}")
async def websocket_route(websocket: WebSocket, room_id: str, token: str, db: Session = Depends(get_db)):
    user = auth.get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, room_id, str(user.id))
    user.status = "online"
    db.commit()

    await manager.broadcast(room_id, {"type": "presence", "user_id": str(user.id), "username": user.username, "status": "online"}, exclude=websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            event = data.get("type")

            if event == "message":
                msg = models.Message(
                    room_id=room_id,
                    sender_id=str(user.id),
                    content=data.get("content", ""),
                    message_type=data.get("message_type", "text"),
                    reply_to_id=data.get("reply_to_id"),
                )
                db.add(msg)
                db.commit()
                db.refresh(msg)

                payload = {
                    "type": "message",
                    "id": msg.id,
                    "room_id": room_id,
                    "sender_id": str(user.id),
                    "sender_username": user.username,
                    "sender_name": user.name,
                    "sender_avatar": user.avatar_base64,
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "reply_to_id": msg.reply_to_id,
                    "created_at": str(msg.created_at),
                    "seen_count": 0,
                }
                await manager.broadcast(room_id, payload)

                # Notification — jo online nahi hain unhe
                members = db.query(models.RoomMember).filter_by(room_id=room_id).all()
                for m in members:
                    if m.user_id != str(user.id):
                        member_user = db.query(models.User).filter_by(id=m.user_id).first()
                        if member_user and member_user.notifications_on and not manager.is_user_online(m.user_id):
                            create_notification(db, m.user_id, "message", f"New message from {user.username}", msg.content[:100] if msg.content else "", room_id)

            elif event == "typing":
                await manager.broadcast(room_id, {"type": "typing", "user_id": str(user.id), "username": user.username, "is_typing": data.get("is_typing", False)}, exclude=websocket)

            elif event == "seen":
                message_id = data.get("message_id")
                if message_id:
                    already = db.query(models.ReadReceipt).filter_by(message_id=message_id, user_id=str(user.id)).first()
                    if not already:
                        db.add(models.ReadReceipt(message_id=message_id, user_id=str(user.id)))
                        db.commit()
                    await manager.broadcast(room_id, {"type": "seen", "message_id": message_id, "user_id": str(user.id), "username": user.username})

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id, str(user.id))
        user.status = "offline"
        db.commit()
        await manager.broadcast(room_id, {"type": "presence", "user_id": str(user.id), "username": user.username, "status": "offline"})


@app.get("/health")
def health():
    return {"status": "ok", "app": "Nexus Chat v2"}
