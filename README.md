# Rural Voice Bridge — Project Root README
# ─────────────────────────────────────────
# Quick startup instructions for dev environment

## Backend (Python / FastAPI)
```powershell
cd backend
pip install -r requirements.txt
New-Item -ItemType Directory -Force -Path logs, temp | Out-Null
# Copy .env.example to .env and fill in your API keys (GROQ_API_KEY or GEMINI_API_KEY)
Copy-Item .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend (React / Vite)
```powershell
cd frontend
npm install
npm run dev
```

App opens at: http://localhost:3000
API Docs at:  http://localhost:8000/docs
