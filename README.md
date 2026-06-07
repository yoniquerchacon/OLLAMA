# Ollama Proxy API (Vercel + Python)

Este proyecto crea una API en FastAPI para reenviar peticiones a tu instancia local de Ollama.

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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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

La API incluye una interfaz para preguntar desde navegador:

- URL: `/ui`
- Ejemplo local: `http://127.0.0.1:8000/ui`
- Ejemplo Vercel: `https://ollama-proxy-api.vercel.app/ui`

En la interfaz pegas tu `API Key`, escribes el modelo (opcional) y la pregunta.

## Nota importante sobre Vercel

Una función en Vercel no puede conectarse directo a `127.0.0.1` de tu PC. Necesitas exponer Ollama con una URL pública (por ejemplo, Cloudflare Tunnel, Tailscale Funnel o Ngrok) y usar esa URL en `OLLAMA_BASE_URL`.
