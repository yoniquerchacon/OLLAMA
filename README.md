# Ollama Proxy API (Vercel + Python)

Este proyecto queda separado en backend y frontend:

- `backend`: API FastAPI que reenvia peticiones a Ollama
- `front end`: interfaz web para enviar preguntas

## Requisitos

- Python 3.10+
- Ollama corriendo en tu equipo

## 1) Instalar dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Configurar entorno

```bash
cp .env.example .env
```

Ajusta:

- `OLLAMA_BASE_URL`: URL de Ollama
  - Local: `http://127.0.0.1:11434`
  - Remoto/Vercel: usa una URL pública de túnel hacia tu máquina
- `DEFAULT_MODEL`: por ejemplo `llama3`
- `REQUEST_TIMEOUT`: segundos de espera
- `API_KEY`: clave secreta requerida para consumir `POST /chat`

## 3) Ejecutar local

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4) Endpoint principal

`POST /chat`

Header requerido:

- `X-API-Key: tu_clave_secreta`

Body de ejemplo:

```json
{
  "model": "llama3",
  "prompt": "Hola, ¿quién eres?",
  "stream": false
}
```

## 5) Interfaz web

La interfaz esta en `front end/index.html`.

- En Vercel queda en la raiz: `/`
- Usa el campo `API URL` para apuntar al backend (por defecto usa el mismo dominio)
- Envia consultas a `POST /chat` con `X-API-Key`

## 6) Memoria por conversación

El backend ahora guarda contexto por `conversation_id`.

- Cada navegador genera su propio `Conversation ID`
- Las preguntas nuevas reutilizan el historial anterior de esa conversación
- El boton `Nueva conversación` crea un contexto limpio

Importante:

- En local, la memoria se guarda en SQLite dentro de `backend/data/`
- En Vercel, si quieres memoria persistente de verdad entre reinicios y despliegues, necesitas un almacenamiento externo como Vercel KV, Postgres, Redis o Supabase
- La versión actual deja la base lista para eso, pero no usa un servicio externo todavia

## Nota importante sobre Vercel

Una función en Vercel no puede conectarse directo a `127.0.0.1` de tu PC. Necesitas exponer Ollama con una URL pública (por ejemplo, Cloudflare Tunnel, Tailscale Funnel o Ngrok) y usar esa URL en `OLLAMA_BASE_URL`.
