# ⚡ NEXUS CHAT — Complete Setup Guide
# Yeh file padhein, ek baar mein sab kuch kaam karega.

════════════════════════════════════════════════════════════
STEP 1 — BACKEND LOCALLY CHALAO
════════════════════════════════════════════════════════════

1a. Folder banao aur files daalo:
─────────────────────────────────
  nexus-backend/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── models.py
  │   ├── schemas.py
  │   ├── auth.py
  │   ├── database.py
  │   └── ws_manager.py
  ├── requirements.txt
  ├── .env
  └── Procfile

1b. Python environment banao:
──────────────────────────────
  cd nexus-backend
  python -m venv venv

  # Windows:
  venv\Scripts\activate

  # Mac/Linux:
  source venv/bin/activate

1c. Dependencies install karo:
────────────────────────────────
  pip install -r requirements.txt

1d. Server start karo:
───────────────────────
  uvicorn app.main:app --reload

  ✅ Ab backend chal raha hai: http://localhost:8000
  ✅ API docs dekhein: http://localhost:8000/docs


════════════════════════════════════════════════════════════
STEP 2 — FRONTEND LOCALLY CHALAO
════════════════════════════════════════════════════════════

2a. Folder banao:
──────────────────
  nexus-frontend/
  ├── src/
  │   ├── App.jsx
  │   └── main.jsx
  ├── index.html
  ├── package.json
  ├── vite.config.js
  └── .env

2b. .env file banao (copy from .env.example):
──────────────────────────────────────────────
  VITE_API_URL=http://localhost:8000
  VITE_WS_URL=ws://localhost:8000

2c. Dependencies install karo aur start karo:
──────────────────────────────────────────────
  cd nexus-frontend
  npm install
  npm run dev

  ✅ Frontend chal raha hai: http://localhost:5173

2d. Test karo:
──────────────
  - Browser mein http://localhost:5173 kholo
  - Sign Up karo (username + password)
  - Room banao
  - Doosre tab mein alag user se login karo
  - Dono mein message karo — real-time!


════════════════════════════════════════════════════════════
STEP 3 — DEPLOY KARO (Railway = Free, No Credit Card)
════════════════════════════════════════════════════════════

BACKEND DEPLOY:
────────────────

3a. railway.app par jaao → GitHub se login karo

3b. GitHub par nexus-backend folder push karo:
  cd nexus-backend
  git init
  git add .
  git commit -m "first commit"
  # GitHub mein new repo banao (nexus-backend)
  git remote add origin https://github.com/YOUR_USERNAME/nexus-backend.git
  git push -u origin main

3c. Railway mein:
  - "New Project" → "Deploy from GitHub repo"
  - nexus-backend select karo
  - Automatically detect karega

3d. Railway mein PostgreSQL add karo:
  - Project ke andar → "+ New" → "Database" → "PostgreSQL"
  - Phir Variables tab mein jaao:
    DATABASE_URL = (Railway khud fill karta hai PostgreSQL se)
    SECRET_KEY   = koi bhi random string likho (32+ chars)

3e. Deploy hone do (2-3 minute lagein ge)
  ✅ Railway aapko URL dega: https://nexus-backend-xxx.railway.app


FRONTEND DEPLOY:
─────────────────

3f. Vercel.com par jaao → GitHub se login

3g. nexus-frontend GitHub par push karo:
  cd nexus-frontend
  git init
  git add .
  git commit -m "first commit"
  # GitHub mein new repo banao (nexus-frontend)
  git remote add origin https://github.com/YOUR_USERNAME/nexus-frontend.git
  git push -u origin main

3h. Vercel mein:
  - "New Project" → nexus-frontend import karo
  - Environment Variables mein daalo:
    VITE_API_URL = https://nexus-backend-xxx.railway.app
    VITE_WS_URL  = wss://nexus-backend-xxx.railway.app
  - Deploy!

  ✅ Frontend URL milega: https://nexus-chat-xxx.vercel.app


════════════════════════════════════════════════════════════
STEP 4 — AAPKO USERS KAISE DIKHEN GE?
════════════════════════════════════════════════════════════

Option A — API Docs (Easiest):
────────────────────────────────
  https://nexus-backend-xxx.railway.app/docs

  Wahan /admin/stats endpoint hai → pehle user (aap) ko
  saare users, rooms, messages dikhen ge.

Option B — Direct API Call:
────────────────────────────
  Apne token se yeh URL kholo:
  https://nexus-backend-xxx.railway.app/admin/stats

  Response:
  {
    "total_users": 5,
    "total_rooms": 3,
    "total_messages": 47,
    "users": [
      { "username": "Arjun", "email": "arjun@gmail.com", "joined": "2024-01-15" },
      { "username": "Guest_A1B2C3", "email": null, "joined": "2024-01-15" }
    ]
  }

Option C — Railway Database GUI:
─────────────────────────────────
  Railway → PostgreSQL → Data tab
  Seedha users table dekhein — sab rows, sab columns.


════════════════════════════════════════════════════════════
INVITE LINK KAISE KAAM KAREGA?
════════════════════════════════════════════════════════════

1. Aap Room banao
2. Room mein 🔗 button dabao
3. Link generate hoga: https://nexus-chat-xxx.vercel.app/join/abc123
4. Yeh link kisi ko bhi bhejo
5. Wo link open kare → directly room join karega

Invite features:
  ✅ Expiry (1h / 24h / 7 days / never)
  ✅ Max uses (e.g. sirf 10 log join kar sakein)
  ✅ Password protected
  ✅ One-time (sirf ek baar use hoga)


════════════════════════════════════════════════════════════
COMMON ERRORS & SOLUTIONS
════════════════════════════════════════════════════════════

❌ "CORS error" frontend mein:
  → backend .env mein FRONTEND_URL set karo

❌ "WebSocket connection failed":
  → VITE_WS_URL check karo — wss:// (https ke saath)

❌ "Module not found":
  → pip install -r requirements.txt dobara chalao

❌ Railway deploy fail:
  → Procfile check karo: web: uvicorn app.main:app --host 0.0.0.0 --port $PORT

❌ Database error:
  → Railway mein DATABASE_URL environment variable check karo


════════════════════════════════════════════════════════════
FILE STRUCTURE SUMMARY
════════════════════════════════════════════════════════════

nexus-backend/
├── app/
│   ├── __init__.py      ← blank file (package)
│   ├── main.py          ← saare API routes + WebSocket
│   ├── models.py        ← database tables
│   ├── schemas.py       ← request/response validation
│   ├── auth.py          ← JWT + password
│   ├── database.py      ← DB connection
│   └── ws_manager.py    ← WebSocket manager
├── requirements.txt
├── .env                 ← SECRET_KEY + DATABASE_URL
├── Procfile             ← Railway ke liye
└── railway.json         ← Railway config

nexus-frontend/
├── src/
│   ├── App.jsx          ← complete React app
│   └── main.jsx         ← entry point
├── index.html
├── package.json
├── vite.config.js
└── .env                 ← VITE_API_URL + VITE_WS_URL
