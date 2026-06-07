import os
import sqlite3
import threading
import uuid
from hmac import compare_digest
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "120"))
API_KEY = os.getenv("API_KEY", "")
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
MEMORY_DB_PATH = os.getenv("MEMORY_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "conversations.sqlite3"))

_DB_LOCK = threading.Lock()

app = FastAPI(title="Ollama Proxy API", version="1.0.0")


def ensure_db() -> None:
    os.makedirs(os.path.dirname(os.path.abspath(MEMORY_DB_PATH)), exist_ok=True)
    with sqlite3.connect(MEMORY_DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id, id)"
        )
        connection.commit()


def save_message(conversation_id: str, role: str, content: str) -> None:
    with _DB_LOCK:
        with sqlite3.connect(MEMORY_DB_PATH) as connection:
            connection.execute(
                "INSERT INTO conversation_messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content),
            )
            connection.commit()


def load_history(conversation_id: str) -> List[Dict[str, str]]:
    with _DB_LOCK:
        with sqlite3.connect(MEMORY_DB_PATH) as connection:
            cursor = connection.execute(
                """
                SELECT role, content
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, MAX_HISTORY_MESSAGES),
            )
            rows = cursor.fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def clear_history(conversation_id: str) -> int:
    with _DB_LOCK:
        with sqlite3.connect(MEMORY_DB_PATH) as connection:
            cursor = connection.execute(
                "DELETE FROM conversation_messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            connection.commit()
            return cursor.rowcount


@app.on_event("startup")
def startup() -> None:
    ensure_db()


def verify_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY no configurada en el servidor.")
    if not x_api_key or not compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="No autorizado: API Key invalida.")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: Optional[str] = Field(default=None, description="Shortcut para enviar una sola pregunta.")
    messages: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Lista de mensajes con formato chat.",
    )
    conversation_id: Optional[str] = Field(default=None, description="Identificador de la conversacion del usuario.")
    remember: bool = Field(default=True, description="Guardar contexto de esta conversacion.")
    model: str = Field(default=DEFAULT_MODEL, description="Modelo de Ollama a usar.")
    stream: bool = Field(default=False, description="Mantener en false para respuestas JSON completas.")


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "ollama-proxy",
        "ollama_base_url": OLLAMA_BASE_URL,
        "default_model": DEFAULT_MODEL,
        "memory_db": MEMORY_DB_PATH,
        "max_history_messages": MAX_HISTORY_MESSAGES,
    }


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, _: None = Depends(verify_api_key)) -> Dict[str, Any]:
    removed = clear_history(conversation_id)
    return {"ok": True, "conversation_id": conversation_id, "removed_messages": removed}


@app.post("/chat")
async def chat(req: ChatRequest, _: None = Depends(verify_api_key)) -> Dict[str, Any]:
    if not req.prompt and not req.messages:
        raise HTTPException(status_code=400, detail="Debes enviar 'prompt' o 'messages'.")

    conversation_id = req.conversation_id or str(uuid.uuid4())

    payload: Dict[str, Any] = {
        "model": req.model,
        "stream": req.stream,
    }

    if req.messages:
        current_messages = [m.model_dump() for m in req.messages]
    else:
        current_messages = [{"role": "user", "content": req.prompt}]

    history_messages = load_history(conversation_id) if req.remember else []
    payload["messages"] = history_messages + current_messages

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

    assistant_content = data.get("message", {}).get("content")
    if req.remember:
        if req.messages:
            for message in current_messages:
                save_message(conversation_id, message["role"], message["content"])
        else:
            save_message(conversation_id, "user", req.prompt or "")
        if assistant_content:
            save_message(conversation_id, "assistant", assistant_content)

    return {
        "ok": True,
        "conversation_id": conversation_id,
        "model": req.model,
        "data": data,
    }
