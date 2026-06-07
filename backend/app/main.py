import os
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3:8b")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "120"))

app = FastAPI(title="Ollama Proxy API", version="1.0.0")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: Optional[str] = Field(default=None, description="Shortcut para enviar una sola pregunta.")
    messages: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Lista de mensajes con formato chat.",
    )
    conversation_id: Optional[str] = Field(default=None, description="Identificador opcional de la conversacion del usuario.")
    model: str = Field(default=DEFAULT_MODEL, description="Modelo de Ollama a usar.")
    stream: bool = Field(default=False, description="Mantener en false para respuestas JSON completas.")


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "ollama-proxy",
        "ollama_base_url": OLLAMA_BASE_URL,
        "default_model": DEFAULT_MODEL,
    }


@app.get("/models")
async def models() -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        detail = {
            "error": "Ollama respondió con error",
            "status_code": exc.response.status_code,
            "response": exc.response.text,
        }
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.RequestError as exc:
        detail = {
            "error": "No se pudo conectar con Ollama",
            "hint": "Si desplegas en Vercel, usa una URL pública (túnel) en OLLAMA_BASE_URL.",
            "base_url": OLLAMA_BASE_URL,
        }
        raise HTTPException(status_code=503, detail=detail) from exc

    models_list = [item.get("name") for item in data.get("models", []) if item.get("name")]
    return {"ok": True, "models": models_list, "raw": data}


@app.post("/chat")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    if not req.prompt and not req.messages:
        raise HTTPException(status_code=400, detail="Debes enviar 'prompt' o 'messages'.")

    payload: Dict[str, Any] = {
        "model": req.model,
        "stream": req.stream,
    }

    if req.messages:
        current_messages = [m.model_dump() for m in req.messages]
    else:
        current_messages = [{"role": "user", "content": req.prompt}]
    payload["messages"] = current_messages

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        detail = {
            "error": "Ollama respondió con error",
            "status_code": exc.response.status_code,
            "response": exc.response.text,
        }
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.RequestError as exc:
        detail = {
            "error": "No se pudo conectar con Ollama",
            "hint": "Si desplegas en Vercel, usa una URL pública (túnel) en OLLAMA_BASE_URL.",
            "base_url": OLLAMA_BASE_URL,
        }
        raise HTTPException(status_code=503, detail=detail) from exc

    return {
        "ok": True,
        "conversation_id": req.conversation_id,
        "model": req.model,
        "data": data,
    }
