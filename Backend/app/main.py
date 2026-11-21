from typing import Optional
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from .config import settings
from .db import Database
from .llm import AllProvidersUnavailableError, LLMGateway

app = FastAPI(title="Resilient AI Chat Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database(settings.database_url)
gateway = LLMGateway(settings)


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str
    system_prompt: Optional[str] = None

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed or len(trimmed) > 128:
            raise ValueError("session_id must be 1-128 non-empty characters")
        return trimmed

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed or len(trimmed) > 4000:
            raise ValueError("message must be 1-4000 characters after trimming")
        return trimmed


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/health")
def health():
    db.ping()
    return {
        "status": "ok",
        "keys_configured": len(settings.key_pool),
        "cache_enabled": settings.cache_enabled,
    }


@app.post("/chat")
def chat(
    req: ChatRequest,
    x_simulate_failure: Optional[str] = Header(default=None, alias="X-Simulate-Failure"),
):
    session_prompt = db.upsert_session_prompt(req.session_id, req.system_prompt)
    effective_system = session_prompt or settings.default_system_prompt

    history = db.get_messages(req.session_id)
    llm_messages = [{"role": "system", "content": effective_system}]
    for m in history:
        llm_messages.append({"role": m["role"], "content": m["content"]})
    llm_messages.append({"role": "user", "content": req.message})

    try:
        reply, metadata = gateway.complete(
            messages=llm_messages,
            simulate_failure_header=x_simulate_failure,
        )
    except AllProvidersUnavailableError:
        raise HTTPException(status_code=503, detail="all providers unavailable")

    db.save_turn(req.session_id, req.message, reply, metadata)

    return {
        "session_id": req.session_id,
        "reply": reply,
        "metadata": metadata,
    }


@app.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    messages = db.get_messages(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": session_id, "messages": messages}