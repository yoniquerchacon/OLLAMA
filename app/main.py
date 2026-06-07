import os
from hmac import compare_digest
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "120"))
API_KEY = os.getenv("API_KEY", "")

app = FastAPI(title="Ollama Proxy API", version="1.0.0")


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
    model: str = Field(default=DEFAULT_MODEL, description="Modelo de Ollama a usar.")
    stream: bool = Field(default=False, description="Mantener en false para respuestas JSON completas.")


@app.get("/")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "ollama-proxy",
        "ollama_base_url": OLLAMA_BASE_URL,
        "default_model": DEFAULT_MODEL,
    }


@app.get("/ui", response_class=HTMLResponse)
def ui() -> str:
        return """
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Ollama Proxy UI</title>
    <style>
        :root {
            --bg: #f2efe8;
            --panel: #fffdf8;
            --text: #1f1f1f;
            --muted: #5b5b5b;
            --brand: #0f766e;
            --brand-2: #115e59;
            --line: #d7d1c7;
            --warn: #b45309;
            --error: #b91c1c;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
            color: var(--text);
            background:
                radial-gradient(circle at 10% 10%, #fff6dc 0%, transparent 40%),
                radial-gradient(circle at 90% 0%, #d9f2ee 0%, transparent 35%),
                var(--bg);
            min-height: 100vh;
            padding: 28px 16px;
        }
        .shell {
            max-width: 900px;
            margin: 0 auto;
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: 0 18px 50px rgba(23, 23, 23, 0.08);
            overflow: hidden;
        }
        .head {
            padding: 24px;
            border-bottom: 1px solid var(--line);
            background: linear-gradient(135deg, #fdf7e5, #ecfbf8);
        }
        h1 {
            margin: 0;
            font-size: 1.6rem;
            letter-spacing: 0.3px;
        }
        .sub {
            margin-top: 8px;
            color: var(--muted);
            font-size: 0.95rem;
        }
        .content {
            display: grid;
            gap: 14px;
            padding: 18px;
        }
        .row {
            display: grid;
            gap: 10px;
            grid-template-columns: 1fr;
        }
        @media (min-width: 760px) {
            .row.cols-2 {
                grid-template-columns: 1fr 1fr;
            }
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 6px;
            font-size: 0.92rem;
        }
        input, textarea, button {
            font: inherit;
        }
        input, textarea {
            width: 100%;
            border: 1px solid var(--line);
            background: #fff;
            border-radius: 10px;
            padding: 10px 12px;
            color: var(--text);
        }
        textarea {
            min-height: 130px;
            resize: vertical;
        }
        .actions {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn {
            border: 0;
            border-radius: 10px;
            padding: 10px 14px;
            font-weight: 700;
            background: var(--brand);
            color: #fff;
            cursor: pointer;
            transition: transform 0.1s ease, background 0.2s ease;
        }
        .btn:hover {
            background: var(--brand-2);
            transform: translateY(-1px);
        }
        .btn:disabled {
            opacity: 0.65;
            cursor: not-allowed;
            transform: none;
        }
        .status {
            font-size: 0.9rem;
            color: var(--muted);
        }
        .status.warn { color: var(--warn); }
        .status.error { color: var(--error); }
        pre {
            margin: 0;
            border-radius: 12px;
            background: #171717;
            color: #f5f5f5;
            border: 1px solid #2c2c2c;
            padding: 12px;
            white-space: pre-wrap;
            word-break: break-word;
            line-height: 1.45;
            font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
            min-height: 140px;
        }
        .footnote {
            font-size: 0.82rem;
            color: var(--muted);
        }
    </style>
</head>
<body>
    <main class="shell">
        <header class="head">
            <h1>Panel Ollama</h1>
            <p class="sub">Envias preguntas a tu API segura y obtienes respuesta del modelo en segundos.</p>
        </header>

        <section class="content">
            <div class="row cols-2">
                <div>
                    <label for="apiKey">API Key (header X-API-Key)</label>
                    <input id="apiKey" type="password" placeholder="Pega tu API key" autocomplete="off" />
                </div>
                <div>
                    <label for="model">Modelo</label>
                    <input id="model" type="text" value="" placeholder="llama3:8b" />
                </div>
            </div>

            <div>
                <label for="prompt">Pregunta</label>
                <textarea id="prompt" placeholder="Ejemplo: Explica en 4 lineas que es fine-tuning."></textarea>
            </div>

            <div class="actions">
                <button id="askBtn" class="btn">Preguntar</button>
                <span id="status" class="status">Listo para consultar.</span>
            </div>

            <div>
                <label for="answer">Respuesta</label>
                <pre id="answer">Aqui aparecera la respuesta...</pre>
            </div>

            <p class="footnote">Sugerencia: la API key se guarda solo en tu navegador (localStorage), no en el servidor.</p>
        </section>
    </main>

    <script>
        const apiKeyInput = document.getElementById("apiKey");
        const modelInput = document.getElementById("model");
        const promptInput = document.getElementById("prompt");
        const askBtn = document.getElementById("askBtn");
        const statusEl = document.getElementById("status");
        const answerEl = document.getElementById("answer");

        const storedKey = localStorage.getItem("ollama_proxy_api_key") || "";
        const storedModel = localStorage.getItem("ollama_proxy_model") || "";
        apiKeyInput.value = storedKey;
        modelInput.value = storedModel;

        function setStatus(text, cssClass = "") {
            statusEl.textContent = text;
            statusEl.className = cssClass ? `status ${cssClass}` : "status";
        }

        function getMessageFromApi(payload) {
            if (!payload || !payload.data) {
                return JSON.stringify(payload, null, 2);
            }
            const content = payload.data?.message?.content;
            if (content) {
                return content;
            }
            return JSON.stringify(payload, null, 2);
        }

        askBtn.addEventListener("click", async () => {
            const key = apiKeyInput.value.trim();
            const prompt = promptInput.value.trim();
            const model = (modelInput.value || "").trim();

            if (!key) {
                setStatus("Debes ingresar API Key.", "warn");
                return;
            }
            if (!prompt) {
                setStatus("Escribe una pregunta antes de enviar.", "warn");
                return;
            }

            localStorage.setItem("ollama_proxy_api_key", key);
            localStorage.setItem("ollama_proxy_model", model);

            askBtn.disabled = true;
            setStatus("Consultando Ollama...");
            answerEl.textContent = "Esperando respuesta...";

            try {
                const body = {
                    prompt,
                    stream: false,
                };
                if (model) {
                    body.model = model;
                }

                const response = await fetch("/chat", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-API-Key": key,
                    },
                    body: JSON.stringify(body),
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(JSON.stringify(data));
                }

                answerEl.textContent = getMessageFromApi(data);
                setStatus("Respuesta recibida.");
            } catch (error) {
                answerEl.textContent = String(error.message || error);
                setStatus("Error consultando la API.", "error");
            } finally {
                askBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
"""


@app.post("/chat")
async def chat(req: ChatRequest, _: None = Depends(verify_api_key)) -> Dict[str, Any]:
    if not req.prompt and not req.messages:
        raise HTTPException(status_code=400, detail="Debes enviar 'prompt' o 'messages'.")

    payload: Dict[str, Any] = {
        "model": req.model,
        "stream": req.stream,
    }

    if req.messages:
        payload["messages"] = [m.model_dump() for m in req.messages]
    else:
        payload["messages"] = [{"role": "user", "content": req.prompt}]

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
        "model": req.model,
        "data": data,
    }
