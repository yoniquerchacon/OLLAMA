import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext): void {
  const disposable = vscode.commands.registerCommand("iaLocal.openChat", () => {
    IAChatPanel.createOrShow(context.extensionUri);
  });

  context.subscriptions.push(disposable);
}

export function deactivate(): void {
  // No cleanup required.
}

class IAChatPanel {
  private static currentPanel: IAChatPanel | undefined;
  private readonly panel: vscode.WebviewPanel;
  private readonly extensionUri: vscode.Uri;
  private readonly disposables: vscode.Disposable[] = [];

  static createOrShow(extensionUri: vscode.Uri): void {
    const column = vscode.window.activeTextEditor?.viewColumn;

    if (IAChatPanel.currentPanel) {
      IAChatPanel.currentPanel.panel.reveal(column);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "iaLocalChat",
      "IA Local Chat",
      column ?? vscode.ViewColumn.One,
      {
        enableScripts: true,
      },
    );

    IAChatPanel.currentPanel = new IAChatPanel(panel, extensionUri);
  }

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this.panel = panel;
    this.extensionUri = extensionUri;

    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
    this.panel.webview.onDidReceiveMessage(
      async (message: { command: string; prompt?: string; model?: string }) => {
        if (message.command === "ask") {
          await this.handleAsk(message.prompt ?? "", message.model ?? "");
        }
      },
      null,
      this.disposables,
    );

    this.panel.webview.html = this.getHtml();
  }

  private async handleAsk(prompt: string, model: string): Promise<void> {
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
      const response = await fetch(`${apiBaseUrl}/chat`, {
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
    this.panel.webview.postMessage(payload);
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
      grid-template-columns: 1fr auto;
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
  </style>
</head>
<body>
  <div class="bar">
    <input id="model" placeholder="Modelo (ej: llama3:8b)" />
    <button id="send">Enviar</button>
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
    const status = document.getElementById("status");

    const appendBubble = (text, cls = "") => {
      const div = document.createElement("div");
      div.className = "bubble " + cls;
      div.textContent = text;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    };

    const send = () => {
      const value = (prompt.value || "").trim();
      if (!value) {
        status.textContent = "Escribe un prompt antes de enviar.";
        return;
      }
      appendBubble(value, "user");
      status.textContent = "Consultando IA...";
      vscode.postMessage({ command: "ask", prompt: value, model: model.value || "" });
      prompt.value = "";
      prompt.focus();
    };

    document.getElementById("send").addEventListener("click", send);
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
  </script>
</body>
</html>`;
  }

  public dispose(): void {
    IAChatPanel.currentPanel = undefined;

    this.panel.dispose();

    while (this.disposables.length) {
      const disposable = this.disposables.pop();
      if (disposable) {
        disposable.dispose();
      }
    }
  }
}
