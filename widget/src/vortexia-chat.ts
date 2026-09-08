import { LitElement, html, css, nothing } from "lit"
import { customElement, property, state } from "lit/decorators.js"
import { unsafeHTML } from "lit/directives/unsafe-html.js"
import { marked } from "marked"
import DOMPurify from "dompurify"

marked.setOptions({ breaks: true })

type Source = { url: string; title: string | null }
type Msg = { role: "user" | "assistant"; content: string; sources?: Source[] }
type Config = {
  display_name: string
  logo_url: string | null
  primary_color: string
  suggestions: string[]
}

const DEFAULT_API = "https://api-chat.getvortexia.com"

@customElement("vortexia-chat")
export class VortexiaChat extends LitElement {
  @property() tenant = ""
  @property() position: "bottom-right" | "bottom-left" = "bottom-right"
  @property() theme: "light" | "dark" | "auto" = "auto"
  @property({ attribute: "api-base" }) apiBase = DEFAULT_API

  @state() private open = false
  @state() private config: Config | null = null
  @state() private messages: Msg[] = []
  @state() private streaming = false
  @state() private draft = ""

  private sessionId: string | null = null

  connectedCallback() {
    super.connectedCallback()
    this.loadConfig()
  }

  private async loadConfig() {
    // Fallback if API down: widget simply doesn't show (spec 4.8).
    try {
      const r = await fetch(`${this.apiBase}/v1/tenants/${this.tenant}/config`)
      if (!r.ok) return
      this.config = await r.json()
    } catch {
      /* stay hidden */
    }
  }

  private emit(name: string, detail?: unknown) {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }))
  }

  private toggle() {
    this.open = !this.open
    this.emit(this.open ? "vortexia:opened" : "vortexia:closed")
    if (this.open && !this.sessionId) this.createSession()
  }

  private async createSession() {
    try {
      const r = await fetch(`${this.apiBase}/v1/sessions`, {
        method: "POST",
        headers: { "X-Tenant-Id": this.tenant },
      })
      this.sessionId = (await r.json()).session_id
    } catch {
      /* retried on send */
    }
  }

  private render_md(md: string) {
    return unsafeHTML(DOMPurify.sanitize(marked.parse(md || "") as string))
  }

  private async send(text: string) {
    text = text.trim()
    if (!text || this.streaming) return
    this.draft = ""
    if (!this.sessionId) await this.createSession()

    this.emit("vortexia:message", { role: "user", content: text })
    this.messages = [
      ...this.messages,
      { role: "user", content: text },
      { role: "assistant", content: "", sources: [] },
    ]
    const asst = this.messages[this.messages.length - 1]
    this.streaming = true

    try {
      const res = await fetch(`${this.apiBase}/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Tenant-Id": this.tenant },
        body: JSON.stringify({ session_id: this.sessionId, message: text }),
      })
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ""
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const frames = buf.split("\n\n")
        buf = frames.pop() ?? "" // keep trailing incomplete frame
        for (const f of frames) {
          let event = "message"
          let data = ""
          for (const line of f.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim()
            else if (line.startsWith("data:")) data += line.slice(5).trim()
          }
          if (!data) continue
          const payload = JSON.parse(data)
          if (event === "token") asst.content += payload.delta
          else if (event === "sources") asst.sources = payload.sources
        }
        this.messages = [...this.messages] // trigger re-render
      }
      this.emit("vortexia:message", { role: "assistant", content: asst.content, sources: asst.sources })
    } catch (e: any) {
      if (!asst.content) asst.content = `⚠️ Erreur : ${e?.message || "réseau"}`
      this.messages = [...this.messages]
    } finally {
      this.streaming = false
      this.updateComplete.then(() => this.scrollDown())
    }
  }

  private scrollDown() {
    const s = this.renderRoot.querySelector(".stream")
    if (s) s.scrollTop = s.scrollHeight
  }

  private get dark() {
    return (
      this.theme === "dark" ||
      (this.theme === "auto" && matchMedia("(prefers-color-scheme: dark)").matches)
    )
  }

  render() {
    if (!this.config) return nothing // hidden until config loads (or forever if API down)
    const brand = this.config.primary_color || "#111827"

    const panel = this.open
      ? html`
          <div class="panel ${this.dark ? "dark" : ""}" style="--brand:${brand}">
            <header class="head">
              ${this.config.logo_url
                ? html`<img class="logo" src=${this.config.logo_url} alt=${this.config.display_name} />`
                : nothing}
              <span class="name">${this.config.display_name}</span>
              <button class="x" @click=${this.toggle} aria-label="Fermer">✕</button>
            </header>

            <div class="stream">
              ${this.messages.length === 0
                ? html`<div class="empty">
                    <p class="muted">Posez une question sur ${this.config.display_name}.</p>
                    ${this.config.suggestions.map(
                      (q) => html`<button class="chip" @click=${() => this.send(q)}>${q}</button>`,
                    )}
                  </div>`
                : this.messages.map(
                    (m) => html`
                      <div class="msg ${m.role}">
                        <div class="bubble">
                          ${m.role === "assistant" ? this.render_md(m.content) : m.content}
                        </div>
                        ${m.sources && m.sources.length
                          ? html`<div class="sources">
                              ${m.sources.map(
                                (s) =>
                                  html`<a href=${s.url} target="_blank" rel="noopener"
                                    >${s.title || s.url}</a
                                  >`,
                              )}
                            </div>`
                          : nothing}
                      </div>
                    `,
                  )}
            </div>

            <form
              class="composer"
              @submit=${(e: Event) => {
                e.preventDefault()
                this.send(this.draft)
              }}
            >
              <input
                .value=${this.draft}
                ?disabled=${this.streaming}
                placeholder="Votre question…"
                @input=${(e: Event) => (this.draft = (e.target as HTMLInputElement).value)}
              />
              <button type="submit" ?disabled=${this.streaming || !this.draft.trim()}>
                ${this.streaming ? "…" : "→"}
              </button>
            </form>
          </div>
        `
      : nothing

    return html`
      <div class="root ${this.position}">
        ${panel}
        <button class="fab" style="--brand:${brand}" @click=${this.toggle} aria-label="Ouvrir le chat">
          ${this.open ? "✕" : "💬"}
        </button>
      </div>
    `
  }

  static styles = css`
    :host {
      --bg: #fff;
      --text: #1f2937;
      --muted: #9ca3af;
      --border: #e5e7eb;
      --panel-bg: #fff;
      --bubble-bot: #f1f3f5;
      all: initial;
      font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    }
    .root { position: fixed; bottom: 20px; z-index: 2147483000; }
    .root.bottom-right { right: 20px; }
    .root.bottom-left { left: 20px; }

    .fab {
      width: 56px; height: 56px; border-radius: 50%; border: none;
      background: var(--brand); color: #fff; font-size: 22px; cursor: pointer;
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25); margin-left: auto; display: block;
    }
    .fab:hover { filter: brightness(1.08); }

    .panel {
      position: absolute; bottom: 68px; right: 0;
      width: min(380px, calc(100vw - 40px)); height: min(560px, calc(100vh - 120px));
      display: flex; flex-direction: column; background: var(--panel-bg);
      border: 1px solid var(--border); border-radius: 16px; overflow: hidden;
      box-shadow: 0 12px 48px rgba(0, 0, 0, 0.18); color: var(--text);
    }
    .root.bottom-left .panel { right: auto; left: 0; }
    .panel.dark {
      --panel-bg: #1f2430; --text: #e5e7eb; --border: #374151;
      --bubble-bot: #2a3140; --muted: #9ca3af;
    }

    .head { display: flex; align-items: center; gap: 8px; padding: 12px 14px; background: var(--brand); color: #fff; }
    .logo { height: 22px; border-radius: 4px; background: #fff; }
    .name { font-weight: 600; }
    .x { margin-left: auto; background: transparent; border: none; color: #fff; cursor: pointer; font-size: 15px; }

    .stream { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 12px; }
    .empty { margin: auto 0; text-align: center; display: flex; flex-direction: column; gap: 8px; }
    .muted { color: var(--muted); }
    .chip {
      border: 1px solid var(--border); background: var(--panel-bg); color: var(--text);
      padding: 9px 12px; border-radius: 10px; cursor: pointer; font-size: 13px; text-align: left;
    }
    .chip:hover { border-color: var(--brand); }

    .msg { display: flex; flex-direction: column; gap: 5px; max-width: 85%; }
    .msg.user { align-self: flex-end; align-items: flex-end; }
    .msg.assistant { align-self: flex-start; }
    .bubble { padding: 9px 12px; border-radius: 12px; line-height: 1.45; font-size: 14px; }
    .msg.user .bubble { background: var(--brand); color: #fff; border-bottom-right-radius: 4px; }
    .msg.assistant .bubble { background: var(--bubble-bot); border-bottom-left-radius: 4px; }
    .bubble p { margin: 0 0 6px; }
    .bubble p:last-child { margin-bottom: 0; }
    .bubble ul, .bubble ol { margin: 4px 0; padding-left: 18px; }
    .bubble a { color: var(--brand); }
    .sources { display: flex; flex-wrap: wrap; gap: 6px; font-size: 11px; }
    .sources a { color: var(--muted); text-decoration: none; border-bottom: 1px dotted var(--muted); }

    .composer { display: flex; gap: 6px; padding: 10px; border-top: 1px solid var(--border); }
    .composer input {
      flex: 1; border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px;
      font-size: 14px; outline: none; background: var(--panel-bg); color: var(--text);
    }
    .composer input:focus { border-color: var(--brand); }
    .composer button {
      border: none; background: var(--brand); color: #fff; width: 40px; border-radius: 10px;
      font-size: 16px; cursor: pointer;
    }
    .composer button:disabled { opacity: 0.5; cursor: default; }
  `
}

declare global {
  interface HTMLElementTagNameMap {
    "vortexia-chat": VortexiaChat
  }
}
