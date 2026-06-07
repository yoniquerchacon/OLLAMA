import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext): void {
  const provider = new IAChatSidebarProvider(context.extensionUri);

  const viewRegistration = vscode.window.registerWebviewViewProvider("iaLocal.chatView", provider, {
    webviewOptions: { retainContextWhenHidden: true },
  });

  const focusCommand = vscode.commands.registerCommand("iaLocal.openChat", async () => {
    await vscode.commands.executeCommand("iaLocal.chatView.focus");
  });

  context.subscriptions.push(provider, viewRegistration, focusCommand);
}

export function deactivate(): void {
  // No cleanup required.
}

type IncomingAttachment = {
  name: string;
  type: string;
  base64: string;
};

class IAChatSidebarProvider implements vscode.WebviewViewProvider, vscode.Disposable {
  private view: vscode.WebviewView | undefined;
  private readonly extensionUri: vscode.Uri;
  private readonly disposables: vscode.Disposable[] = [];
  private readonly conversationId: string = crypto.randomUUID();

  constructor(extensionUri: vscode.Uri) {
    this.extensionUri = extensionUri;
  }

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.view = webviewView;
    this.view.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "media")],
    };

    this.view.webview.html = this.getHtml();

    this.view.webview.onDidReceiveMessage(
      async (message: { command: string; prompt?: string; model?: string; attachments?: IncomingAttachment[] }) => {
        if (message.command === "ask") {
          await this.handleAsk(message.prompt ?? "", message.model ?? "", message.attachments ?? []);
        }
      },
      null,
      this.disposables,
    );

    this.view.onDidDispose(() => {
      this.view = undefined;
    });
  }

  private async handleAsk(prompt: string, model: string, attachments: IncomingAttachment[]): Promise<void> {
    const trimmed = prompt.trim();
    if (!trimmed) {
      this.postToWebview({ type: "error", error: "Escribe un prompt antes de enviar." });
      return;
    }

    const config = vscode.workspace.getConfiguration("iaLocal");
    const apiBaseUrl = String(config.get("apiBaseUrl") || "https://ollama-proxy-api.vercel.app").replace(/\/$/, "");
    const defaultModel = String(config.get("defaultModel") || "llama3:8b");
    const finalModel = model.trim() || defaultModel;

    try {
      let response: Response;

      if (attachments.length) {
        const form = new FormData();
        form.append("prompt", trimmed);
        form.append("model", finalModel);
        form.append("conversation_id", this.conversationId);
        form.append("messages_json", "[]");

        for (const file of attachments) {
          const mimeType = file.type || "application/octet-stream";
          const fileName = file.name || "adjunto.bin";
          const bytes = Buffer.from(file.base64, "base64");
          const blob = new Blob([bytes], { type: mimeType });
          form.append("files", blob, fileName);
        }

        response = await fetch(`${apiBaseUrl}/chat/attachments`, {
          method: "POST",
          body: form,
        });
      } else {
        response = await fetch(`${apiBaseUrl}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: finalModel,
            stream: false,
            messages: [{ role: "user", content: trimmed }],
          }),
        });
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
      }

      const content = String(data?.data?.message?.content || "(sin respuesta)");
      this.postToWebview({ type: "answer", answer: content, model: data?.model || finalModel });
    } catch (error) {
      this.postToWebview({
        type: "error",
        error: String((error as Error)?.message || error),
      });
    }
  }

  private postToWebview(payload: unknown): void {
    this.view?.webview.postMessage(payload);
  }

  private getHtml(): string {
    return `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {
      --bg: #0b1020;
      --panel: #121a31;
      --line: rgba(255, 255, 255, 0.12);
      --text: #ecf4ff;
      --muted: #9fb2d1;
      --brand: #34d399;
      --brand-2: #10b981;
      --error: #ef4444;
    }
    body {
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background: radial-gradient(circle at top right, rgba(16, 185, 129, 0.15), transparent 30%), var(--bg);
      color: var(--text);
      height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr auto;
    }
    .bar {
      padding: 12px;
      border-bottom: 1px solid var(--line);
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      background: #0e162a;
    }
    input, textarea, button {
      font: inherit;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      color: var(--text);
      padding: 10px;
    }
    textarea {
      resize: vertical;
      min-height: 90px;
      width: 100%;
    }
    button {
      background: var(--brand);
      border: none;
      color: #04120d;
      font-weight: 700;
      cursor: pointer;
    }
    button:hover { background: var(--brand-2); }
    .chat {
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .bubble {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 12px;
      padding: 10px;
      white-space: pre-wrap;
      line-height: 1.45;
    }
    .user { border-color: rgba(52, 211, 153, 0.45); }
    .error { color: var(--error); }
    .composer {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      padding: 12px;
      border-top: 1px solid var(--line);
      background: #0e162a;
    }
    .status {
      color: var(--muted);
      font-size: 12px;
      padding: 0 12px 10px;
    }
    .attach-row {
      display: grid;
      gap: 6px;
    }
    .attach-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
    }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 8px;
      background: #0f1830;
    }
  </style>
</head>
<body>
  <div class="bar">
    <input id="model" placeholder="Modelo (ej: llama3:8b)" />
    <div class="attach-row">
      <input id="attachments" type="file" accept="image/*" multiple />
      <div id="attachList" class="attach-list"><span class="pill">Sin imagenes adjuntas</span></div>
    </div>
  </div>
  <div id="chat" class="chat">
    <div class="bubble">IA Local lista. Escribe tu prompt abajo.</div>
  </div>
  <div>
    <div class="composer">
      <textarea id="prompt" placeholder="Escribe tu consulta..."></textarea>
      <button id="send2">Enviar</button>
    </div>
    <div id="status" class="status">Conectando con tu API configurada en iaLocal.apiBaseUrl</div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();
    const chat = document.getElementById("chat");
    const prompt = document.getElementById("prompt");
    const model = document.getElementById("model");
    const attachmentsInput = document.getElementById("attachments");
    const attachList = document.getElementById("attachList");
    const status = document.getElementById("status");
    let selectedFiles = [];

    const appendBubble = (text, cls = "") => {
      const div = document.createElement("div");
      div.className = "bubble " + cls;
      div.textContent = text;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    };

    const renderAttachments = () => {
      if (!selectedFiles.length) {
        attachList.innerHTML = '<span class="pill">Sin imagenes adjuntas</span>';
        return;
      }
      attachList.innerHTML = selectedFiles.map((f) => '<span class="pill">' + f.name + '</span>').join("");
    };

    const filesToPayload = async () => {
      const jobs = selectedFiles.map((file) => new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = String(reader.result || "");
          const base64 = result.includes(",") ? result.split(",")[1] : "";
          resolve({ name: file.name, type: file.type || "application/octet-stream", base64 });
        };
        reader.onerror = () => reject(new Error("No se pudo leer el archivo: " + file.name));
        reader.readAsDataURL(file);
      }));
      return Promise.all(jobs);
    };

    const send = async () => {
      const value = (prompt.value || "").trim();
      if (!value) {
        status.textContent = "Escribe un prompt antes de enviar.";
        return;
      }
      appendBubble(value, "user");
      status.textContent = "Consultando IA...";
      try {
        const attachments = await filesToPayload();
        vscode.postMessage({ command: "ask", prompt: value, model: model.value || "", attachments });
        selectedFiles = [];
        attachmentsInput.value = "";
        renderAttachments();
      } catch (error) {
        appendBubble("Error: " + ((error && error.message) || error), "error");
        status.textContent = "Fallo leyendo imagenes adjuntas.";
      }
      prompt.value = "";
      prompt.focus();
    };

    attachmentsInput.addEventListener("change", () => {
      selectedFiles = Array.from(attachmentsInput.files || []);
      renderAttachments();
    });

    document.getElementById("send2").addEventListener("click", send);
    prompt.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        send();
      }
    });

    window.addEventListener("message", (event) => {
      const message = event.data;
      if (message.type === "answer") {
        appendBubble(message.answer || "(sin respuesta)");
        status.textContent = "Respuesta recibida (" + (message.model || "modelo") + ").";
      }
      if (message.type === "error") {
        appendBubble("Error: " + (message.error || "desconocido"), "error");
        status.textContent = "Hubo un error al consultar la IA.";
      }
    });

    renderAttachments();
  </script>
</body>
</html>`;
  }

  public dispose(): void {
    this.view = undefined;

    while (this.disposables.length) {
      const disposable = this.disposables.pop();
      if (disposable) {
        disposable.dispose();
      }
    }
  }
}
