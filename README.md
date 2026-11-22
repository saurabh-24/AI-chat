# Chat Bot

A full-stack resilient AI chat application built with **FastAPI**, **LiteLLM**, **SQLite**, and **React (Vite)**. It provides multi-turn conversation memory, automatic API key failover, response caching, and per-message telemetry (resolution source, model, latency, and token usage).

---

## Live Deployment

- **Frontend (Vercel):** https://ai-chat-zeta.vercel.app
- **Backend (Render):** https://chat-bot-k1hz.onrender.com
- **Health Check:** https://chat-bot-k1hz.onrender.com/health

> *Note: Render's free tier spins down after 15 minutes of inactivity. The first request after an idle period may take 30–50 seconds to wake the server.*

---

## Architecture & Design Decisions

- **Automatic API Key Failover:** API keys are loaded from `LLM_API_KEYS` (indexed as `key_1`, `key_2`, etc.). On each live inference request, the backend tries keys sequentially. If a key encounters a retryable error (such as a `429` rate limit, timeout, or transient provider error), it automatically fails over to the next key and logs `fallback_attempts` and the winning `key_id` in the response metadata. If all keys fail, the API returns `503 Service Unavailable`.
- **Response Caching:** LiteLLM's local cache (with `orjson` serialization) caches identical prompt payloads. Repeated requests return immediately with `resolution_source: "LLM_CACHE"` and lower latency, reducing redundant upstream calls.
- **SQLite Session Persistence:** Conversations are stored in SQLite (`sessions` and `messages` tables) keyed by `session_id`. Each `/chat` request loads prior turns for multi-turn context and persists the new user/assistant messages alongside latency and token usage metrics.

---

## Running Locally

### Prerequisites
- Two Gemini API keys (comma-separated in `LLM_API_KEYS`)
- **Docker Desktop** (for Docker setup) **or** **Python 3.11+** and **Node.js 18+** (for manual setup)

### Option 1: With Docker
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Update `.env` with your keys and settings:
   ```env
   LLM_API_KEYS=your_gemini_key_1,your_gemini_key_2
   LLM_MODEL=gemini/gemini-flash-lite-latest
   DATABASE_URL=sqlite:////data/app.db
   CACHE_ENABLED=true
   ENABLE_FAILURE_SIMULATION=true
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
   ```
3. Build and launch both services:
   ```bash
   docker compose up --build
   ```
4. Access the app at **http://localhost:3000** and the backend health endpoint at **http://localhost:8000/health**.

### Option 2: Without Docker

**1. Start the Backend (FastAPI)**
```powershell
cd Backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:LLM_API_KEYS="your_gemini_key_1,your_gemini_key_2"
$env:LLM_MODEL="gemini/gemini-flash-lite-latest"
$env:DATABASE_URL="sqlite:///./app.db"
$env:CACHE_ENABLED="true"
$env:ENABLE_FAILURE_SIMULATION="true"
$env:ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173"

uvicorn app.main:app --reload --port 8000
```

**2. Start the Frontend (React + Vite)**
```powershell
cd Frontend
npm install
npm run dev
```
Open **http://localhost:3000** (or the local URL printed by Vite).

---

## Verification Guide

### 1. Health Check
```bash
curl -s https://chat-bot-k1hz.onrender.com/health
```
Expected response:
```json
{"status":"ok","keys_configured":2,"cache_enabled":true}
```

### 2. Multi-Turn Memory & Per-Message Token Usage
1. Open https://ai-chat-zeta.vercel.app.
2. Send `"My name is Alex."` and inspect the metadata badges beneath the reply (`LIVE_INFERENCE`, model name, latency in `ms`, and input/output token counts).
3. Send `"What is my name?"` to verify multi-turn context retention.

### 3. Cache Hit Verification (`LLM_CACHE`)
1. Click **+ New Session** (or refresh the page).
2. Send `"My name is Alex."` again and verify the resolution badge updates to **`LLM_CACHE`** with reduced latency.

### 4. Key Failover & Error Handling (`X-Simulate-Failure`)
Simulate a `429` error on `key_1` to trigger failover to `key_2`:
```bash
curl -s -X POST https://chat-bot-k1hz.onrender.com/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: key_1=429" \
  -d '{"session_id":"s-fail-test","message":"Say hello."}'
```
Verify the metadata shows `"key_id": "key_2"` and `"fallback_attempts": 1`.

Simulate all keys failing (`503 Service Unavailable`):
```bash
curl -s -i -X POST https://chat-bot-k1hz.onrender.com/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: *=429" \
  -d '{"session_id":"s-all-fail","message":"Say hello."}'
```

### 5. Inspect Persisted Session History
```bash
curl -s https://chat-bot-k1hz.onrender.com/sessions/s-fail-test/messages
```

### 6. Run Backend Tests
```powershell
cd Backend
pytest
```

---

## Environment Variables

| Variable | Service | Description |
|---|---|---|
| `LLM_API_KEYS` | Backend | Comma-separated Gemini API keys for automatic failover |
| `LLM_MODEL` | Backend | LiteLLM model identifier (e.g., `gemini/gemini-flash-lite-latest`) |
| `DATABASE_URL` | Backend | SQLite connection string (e.g., `sqlite:////tmp/app.db`) |
| `CACHE_ENABLED` | Backend | Enables or disables LiteLLM response caching (`true`/`false`) |
| `ENABLE_FAILURE_SIMULATION` | Backend | Enables `X-Simulate-Failure` header testing (`true`/`false`) |
| `ALLOWED_ORIGINS` | Backend | Comma-separated list of allowed CORS frontend origins |
| `VITE_API_BASE_URL` | Frontend | Base URL of the deployed FastAPI backend |

---

## Development Setup

- **Editor:** Visual Studio Code (Windows / PowerShell)
- **AI Assistance:** Gemini (architecture planning, deployment troubleshooting, and UI polish)

---

## Highlights & Bonus Features

- **Responsive Dark-Slate UI:** Clean chat interface with color-coded resolution pills (`LLM_CACHE` vs. `LIVE_INFERENCE`), typing indicator, and auto-scroll.
- **Quick-Prompt Chips:** One-click starter prompts on the empty state for quick testing and demos.
- **Session Controls:** Instant **+ New Session** reset and customizable system prompt controls directly in the header.