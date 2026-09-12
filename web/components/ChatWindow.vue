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
// v-html on LLM output = trust boundary: sanitize (model can echo raw HTML from ingested site).
const render = (md: string) => DOMPurify.sanitize(marked.parse(md || "") as string)

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
  } catch {
    /* session created lazily on first send if this failed */
  }
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

function umamiTrack(event: string, data?: Record<string, unknown>) {
  try { (window as any).umami?.track(event, data) } catch {}
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
      buf = frames.pop() ?? "" // keep the trailing incomplete frame
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
    <header class="head">
      <img v-if="config.logo_url" :src="config.logo_url" :alt="config.display_name" class="logo" />
      <span class="name">{{ config.display_name }}</span>
      <span class="ai">Assistant IA</span>
    </header>

    <div ref="scroller" class="stream">
      <div v-if="!messages.length" class="empty">
        <p class="muted">Posez une question sur {{ config.display_name }}.</p>
        <div v-if="config.suggestions.length" class="suggestions">
          <button
            v-for="q in config.suggestions"
            :key="q"
            class="chip"
            @click="umamiTrack('chat_suggestion', { tenant: props.tenant, suggestion: q }); send(q)"
          >{{ q }}</button>
        </div>
      </div>

      <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
        <div v-if="m.role === 'assistant'" class="bubble md" v-html="render(m.content)" />
        <div v-else class="bubble">{{ m.content }}</div>
        <div v-if="m.sources && m.sources.length" class="sources">
          <a v-for="s in m.sources" :key="s.url" :href="s.url" target="_blank" rel="noopener">
            {{ s.title || s.url }}
          </a>
        </div>
      </div>
    </div>

    <form class="composer" @submit.prevent="send(input)">
      <input
        v-model="input"
        :disabled="streaming"
        placeholder="Votre question…"
        autofocus
      />
      <button type="submit" :disabled="streaming || !input.trim()">
        {{ streaming ? "…" : "Envoyer" }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.chat {
  width: 100%;
  max-width: 560px;
  height: min(720px, 92vh);
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
}
.head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: var(--brand);
  color: #fff;
}
.logo { height: 24px; width: auto; border-radius: 4px; background: #fff; }
.name { font-weight: 600; }
.ai { margin-left: auto; font-size: 12px; opacity: 0.8; }

.stream { flex: 1; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 14px; }
.empty { margin: auto 0; text-align: center; }
.muted { color: var(--muted); }
.suggestions { display: flex; flex-direction: column; gap: 8px; margin-top: 14px; }
.chip {
  border: 1px solid var(--border);
  background: #fff;
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  text-align: left;
  transition: border-color 0.15s;
}
.chip:hover { border-color: var(--brand); }

.msg { display: flex; flex-direction: column; gap: 6px; max-width: 85%; }
.msg.user { align-self: flex-end; align-items: flex-end; }
.msg.assistant { align-self: flex-start; }
.bubble { padding: 10px 14px; border-radius: 12px; line-height: 1.5; font-size: 15px; }
.msg.user .bubble { background: var(--brand); color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: #f1f3f5; color: var(--text); border-bottom-left-radius: 4px; }
.md :deep(p) { margin: 0 0 8px; }
.md :deep(p:last-child) { margin-bottom: 0; }
.md :deep(ul), .md :deep(ol) { margin: 6px 0; padding-left: 20px; }
.md :deep(a) { color: var(--brand); }
.sources { display: flex; flex-wrap: wrap; gap: 8px; font-size: 12px; }
.sources a { color: var(--muted); text-decoration: none; border-bottom: 1px dotted var(--muted); }
.sources a:hover { color: var(--brand); border-color: var(--brand); }

.composer { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--border); }
.composer input {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 11px 14px;
  font-size: 15px;
  outline: none;
}
.composer input:focus { border-color: var(--brand); }
.composer button {
  border: none;
  background: var(--brand);
  color: #fff;
  padding: 0 18px;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
}
.composer button:disabled { opacity: 0.5; cursor: default; }
</style>
