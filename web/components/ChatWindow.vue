<script setup lang="ts">
import { ref, reactive, nextTick, onMounted } from "vue"
import { marked } from "marked"
import DOMPurify from "dompurify"

type Source = { url: string; title: string | null }
type Msg = { role: "user" | "assistant"; content: string; sources?: Source[] }
type Config = {
  display_name: string
  logo_url: string | null
  suggestions: string[]
}

const props = defineProps<{ apiBase: string; tenant: string; config: Config }>()

marked.setOptions({ breaks: true })

const render = (md: string) => {
  const cleaned = (md || "").replace(/\[SOURCE\s*\d+\]/gi, "").trim()
  return DOMPurify.sanitize(marked.parse(cleaned) as string)
}

function uniqueSources(sources: Source[] = []): Source[] {
  const seen = new Set<string>()
  return sources.filter(s => {
    if (seen.has(s.url)) return false
    seen.add(s.url)
    return true
  }).slice(0, 3)
}

function umamiTrack(event: string, data?: Record<string, unknown>) {
  try { (window as any).umami?.track(event, data) } catch {}
}

const messages = ref<Msg[]>([])
const input = ref("")
const streaming = ref(false)
const sessionId = ref<string | null>(null)
const scroller = ref<HTMLElement | null>(null)

async function scrollDown() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

onMounted(async () => {
  try {
    const r = await fetch(`${props.apiBase}/v1/sessions`, {
      method: "POST",
      headers: { "X-Tenant-Id": props.tenant },
    })
    sessionId.value = (await r.json()).session_id
  } catch { /* lazy init on first send */ }
})

function parseFrame(frame: string): { event: string; data: string } {
  let event = "message"
  let data = ""
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim()
    else if (line.startsWith("data:")) data += line.slice(5).trim()
  }
  return { event, data }
}

async function send(text: string) {
  text = text.trim()
  if (!text || streaming.value) return
  input.value = ""
  umamiTrack("chat_message", { tenant: props.tenant, question: text })

  if (!sessionId.value) {
    const r = await fetch(`${props.apiBase}/v1/sessions`, {
      method: "POST",
      headers: { "X-Tenant-Id": props.tenant },
    })
    sessionId.value = (await r.json()).session_id
  }

  messages.value.push({ role: "user", content: text })
  const asst = reactive<Msg>({ role: "assistant", content: "", sources: [] })
  messages.value.push(asst)
  streaming.value = true
  scrollDown()

  try {
    const res = await fetch(`${props.apiBase}/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Tenant-Id": props.tenant },
      body: JSON.stringify({ session_id: sessionId.value, message: text }),
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
      buf = frames.pop() ?? ""
      for (const f of frames) {
        const { event, data } = parseFrame(f)
        if (!data) continue
        const payload = JSON.parse(data)
        if (event === "token") asst.content += payload.delta
        else if (event === "sources") asst.sources = payload.sources
      }
      scrollDown()
    }
  } catch (e: any) {
    if (!asst.content) asst.content = `⚠️ Erreur : ${e?.message || "réseau"}`
  } finally {
    streaming.value = false
    scrollDown()
  }
}
</script>

<template>
  <div class="chat">
    <!-- Header -->
    <header class="head">
      <img v-if="config.logo_url" :src="config.logo_url" :alt="config.display_name" class="logo" />
      <div class="head-info">
        <span class="head-name">{{ config.display_name }}</span>
        <span class="head-badge">Assistant IA</span>
      </div>
      <div class="online-badge">
        <span class="green-dot"></span>
        En ligne
      </div>
    </header>

    <!-- Messages -->
    <div ref="scroller" class="stream">
      <!-- Empty state -->
      <div v-if="!messages.length" class="empty">
        <div class="greeting">
          <span class="greeting-icon">👋</span>
          <p>
            <strong>Bonjour !</strong><br>
            Je connais le site <strong>{{ config.display_name }}</strong>.<br>
            Posez-moi une question ou choisissez un exemple.
          </p>
        </div>
        <div v-if="config.suggestions.length" class="suggestions">
          <button
            v-for="q in config.suggestions"
            :key="q"
            class="chip"
            @click="umamiTrack('chat_suggestion', { tenant: props.tenant, suggestion: q }); send(q)"
          >{{ q }}</button>
        </div>
      </div>

      <!-- Message list -->
      <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
        <!-- Typing indicator -->
        <div v-if="m.role === 'assistant' && streaming && i === messages.length - 1 && !m.content" class="bubble typing">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
        <!-- Message bubble -->
        <template v-else>
          <div v-if="m.role === 'assistant'" class="bubble md" v-html="render(m.content)" />
          <div v-else class="bubble">{{ m.content }}</div>
        </template>

        <!-- Sources -->
        <div v-if="m.sources && uniqueSources(m.sources).length" class="sources-block">
          <span class="sources-label">Sources consultées</span>
          <a
            v-for="s in uniqueSources(m.sources)"
            :key="s.url"
            :href="s.url"
            target="_blank"
            rel="noopener"
            class="source-link"
          >↗ {{ s.title || s.url }}</a>
        </div>
      </div>
    </div>

    <!-- Composer -->
    <form class="composer" @submit.prevent="send(input)">
      <input
        v-model="input"
        :disabled="streaming"
        placeholder="Votre question…"
        autofocus
      />
      <button type="submit" :disabled="streaming || !input.trim()">
        <span v-if="streaming" class="spinner"></span>
        <span v-else>↑</span>
      </button>
    </form>
  </div>
</template>

<style scoped>
.chat {
  width: 100%;
  max-width: 520px;
  height: min(660px, 85vh);
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,.04), 0 16px 48px -8px rgba(0,0,0,.10);
}

/* Header */
.head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: var(--brand);
  color: #fff;
  flex-shrink: 0;
}
.logo { height: 26px; width: auto; border-radius: 4px; }
.head-info { display: flex; flex-direction: column; gap: 1px; }
.head-name { font-weight: 600; font-size: 0.9rem; line-height: 1; }
.head-badge { font-size: 11px; opacity: 0.7; }
.online-badge {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  opacity: 0.9;
}
.green-dot {
  width: 7px;
  height: 7px;
  background: #4ade80;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Stream */
.stream {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  scroll-behavior: smooth;
}

/* Empty state */
.empty {
  margin: auto 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.greeting {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.greeting-icon { font-size: 1.4rem; flex-shrink: 0; }
.greeting p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text);
  line-height: 1.6;
}
.suggestions { display: flex; flex-direction: column; gap: 8px; }
.chip {
  border: 1px solid var(--border);
  background: #fff;
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.875rem;
  text-align: left;
  color: var(--text);
  transition: border-color 0.15s, background 0.15s;
  line-height: 1.4;
}
.chip:hover { border-color: var(--brand); background: var(--subtle, #f9fafb); }

/* Messages */
.msg {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 88%;
  animation: fadeUp 0.2s ease;
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.msg.user { align-self: flex-end; align-items: flex-end; }
.msg.assistant { align-self: flex-start; }

.bubble {
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.55;
  font-size: 0.9rem;
}
.msg.user .bubble {
  background: var(--text);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg.assistant .bubble {
  background: #f3f4f6;
  color: var(--text);
  border-bottom-left-radius: 4px;
}
.md :deep(p) { margin: 0 0 8px; }
.md :deep(p:last-child) { margin-bottom: 0; }
.md :deep(ul), .md :deep(ol) { margin: 6px 0; padding-left: 18px; }
.md :deep(li) { margin-bottom: 4px; }
.md :deep(a) { color: var(--brand); }
.md :deep(code) { background: #e5e7eb; padding: 1px 5px; border-radius: 4px; font-size: 0.85em; }

/* Typing indicator */
.typing {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 12px 16px;
  min-width: 52px;
}
.dot {
  width: 6px;
  height: 6px;
  background: #9ca3af;
  border-radius: 50%;
  animation: bounce 1.2s ease-in-out infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-5px); }
}

/* Sources */
.sources-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 2px;
}
.sources-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
}
.source-link {
  font-size: 12px;
  color: var(--muted);
  text-decoration: none;
  transition: color 0.15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 280px;
}
.source-link:hover { color: var(--brand); }

/* Composer */
.composer {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--border);
  background: #fff;
  flex-shrink: 0;
}
.composer input {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 11px 14px;
  font-size: 0.9rem;
  outline: none;
  background: var(--subtle, #f9fafb);
  transition: border-color 0.15s, background 0.15s;
  font-family: inherit;
}
.composer input:focus { border-color: var(--brand); background: #fff; }
.composer button {
  width: 40px;
  height: 40px;
  border: none;
  background: var(--text);
  color: #fff;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.15s;
  flex-shrink: 0;
}
.composer button:disabled { opacity: 0.4; cursor: default; }

/* Spinner */
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
