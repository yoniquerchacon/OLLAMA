# Ollama Proxy API (Vercel + Python)

Este proyecto queda separado en backend y frontend:

- `backend`: API FastAPI que reenvia peticiones a Ollama
- `front end`: interfaz web tipo mensajeria para enviar preguntas

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
- `DEFAULT_MODEL`: por ejemplo `llama3:8b`
- `REQUEST_TIMEOUT`: segundos de espera
- `API_KEY`: variable reservada para configuraciones internas en Vercel
- `AUTO_SWITCH_MULTIMODAL`: si esta en `true`, cuando adjuntas imagenes y el modelo no es multimodal, el backend intenta cambiar automaticamente a uno compatible disponible en Ollama

## 3) Ejecutar local

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4) Endpoint principal

`POST /chat`

Body de ejemplo:

```json
{
  "model": "llama3:8b",
  "prompt": "Hola, ¿quién eres?",
  "stream": false
}
```

## 4.1) Endpoint con adjuntos

`POST /chat/attachments` (multipart/form-data)

Campos:

- `prompt`: texto del usuario
- `model`: nombre del modelo
- `conversation_id`: opcional
- `messages_json`: historial previo en formato JSON (opcional)
- `files`: multiples archivos

Soporta archivos:

- Imagenes: png, jpg/jpeg, webp
- Documentos: txt, md, json, csv, pdf, docx

Nota para imagenes:

- Si eliges un modelo de solo texto (por ejemplo `llama3:8b`) y adjuntas imagenes, Ollama responde error 400.
- Con `AUTO_SWITCH_MULTIMODAL=true`, el backend reintenta con un modelo multimodal instalado (por ejemplo `llama3.2-vision` o `llava`).

Limites base:

- maximo 8 archivos por mensaje
- maximo 8MB por archivo
- maximo 24MB por solicitud

## 5) Interfaz web

La interfaz esta en `front end/index.html`.

- En Vercel queda en la raiz: `/`
- El frontend consulta el backend en el mismo dominio
- El modelo se elige desde un select cargado con los modelos disponibles
- El chat se usa con Enter para enviar y Shift+Enter para salto de linea

## 6) Memoria por conversación

La memoria por conversación se guarda en el navegador y se envía al backend en cada consulta.

- Cada navegador genera su propio contexto local
- Las preguntas nuevas reutilizan el historial anterior de esa conversación
- El boton `Nueva conversación` crea un contexto limpio

Importante:

- Esto funciona bien en Vercel porque no depende del disco del servidor
- Si quieres memoria compartida entre dispositivos o usuarios logueados, entonces sí conviene añadir una base de datos externa como Vercel KV, Postgres, Redis o Supabase
- La implementación actual separa cada conversación por navegador, que es la forma más simple y estable sin infraestructura adicional

## 7) Seguridad contra prompt injection

El backend aplica defensas basicas:

- Detecta patrones peligrosos como "ignore previous instructions" y variantes
- Rechaza prompts sospechosos con error `400`
- Trata los adjuntos como entrada no confiable
- Agrega un mensaje de sistema con reglas de seguridad antes de consultar Ollama

Nota: esta defensa reduce riesgo, pero no reemplaza controles avanzados. Para mayor seguridad, conviene añadir validacion adicional por reglas del negocio y moderacion de contenido.

## Nota importante sobre Vercel

Una función en Vercel no puede conectarse directo a `127.0.0.1` de tu PC. Necesitas exponer Ollama con una URL pública (por ejemplo, Cloudflare Tunnel, Tailscale Funnel o Ngrok) y usar esa URL en `OLLAMA_BASE_URL`.
