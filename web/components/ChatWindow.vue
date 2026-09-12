<script setup lang="ts">
import { ref, reactive, nextTick, onMounted } from "vue"
import { marked } from "marked"
import DOMPurify from "dompurify"

type Source = { url: string; title: string | null }
type ScriptedQA = { question: string; answer: string; source_url: string | null }
type Msg = { role: "user" | "assistant"; content: string; sources?: Source[]; sourceUrl?: string | null }
type Config = {
  display_name: string
  logo_url: string | null
  suggestions: string[]
  scripted_qa?: ScriptedQA[]
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

function sourcePath(url: string | null | undefined): string {
  if (!url) return ""
  try {
    const u = new URL(url)
    return u.pathname + u.hash || "/"
  } catch { return url }
}

function umamiTrack(event: string, data?: Record<string, unknown>) {
  try { (window as any).umami?.track(event, data) } catch {}
}

const messages = ref<Msg[]>([])
const input = ref("")
const streaming = ref(false)
const scripting = ref(false) // auto-playing intro, blocks user input
const sessionId = ref<string | null>(null)
const scroller = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLInputElement | null>(null)

const reducedMotion = typeof window !== "undefined"
  && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches

function focusInput() {
  inputEl.value?.focus()
}
defineExpose({ focusInput })

async function scrollDown() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms))

async function ensureSession() {
  if (sessionId.value) return
  try {
    const r = await fetch(`${props.apiBase}/v1/sessions`, {
      method: "POST",
      headers: { "X-Tenant-Id": props.tenant },
    })
    sessionId.value = (await r.json()).session_id
  } catch { /* lazy retry on send */ }
}

// Auto-play the scripted conversation (2 real Q&A from the prospect's own site).
async function playScript() {
  const script = props.config.scripted_qa || []
  if (!script.length) return

  if (reducedMotion) {
    for (const qa of script) {
      messages.value.push({ role: "user", content: qa.question })
      messages.value.push({ role: "assistant", content: qa.answer, sourceUrl: qa.source_url })
    }
    scrollDown()
    return
  }

  scripting.value = true
  for (const qa of script) {
    messages.value.push({ role: "user", content: qa.question })
    scrollDown()
    await sleep(700)

    const asst = reactive<Msg>({ role: "assistant", content: "", sourceUrl: qa.source_url })
    messages.value.push(asst)
    await sleep(900) // typing indicator dwell

    // Type out the answer word by word
    const words = qa.answer.split(" ")
    for (let i = 0; i < words.length; i++) {
      asst.content += (i ? " " : "") + words[i]
      if (i % 2 === 0) await sleep(28)
      scrollDown()
    }
    await sleep(600)
  }
  scripting.value = false
}

onMounted(async () => {
  await ensureSession()
  playScript()
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
  if (!text || streaming.value || scripting.value) return
  input.value = ""
  umamiTrack("chat_message", { tenant: props.tenant, question: text })

  await ensureSession()

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
    <!-- Header carries the PROSPECT's brand, not ours -->
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

    <div ref="scroller" class="stream">
      <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
        <!-- Typing indicator: streaming OR scripting, empty assistant, last message -->
        <div
          v-if="m.role === 'assistant' && (streaming || scripting) && i === messages.length - 1 && !m.content"
          class="bubble typing"
        >
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
        <template v-else>
          <div v-if="m.role === 'assistant'" class="bubble md" v-html="render(m.content)" />
          <div v-else class="bubble">{{ m.content }}</div>
        </template>

        <!-- Single source pill (scripted) -->
        <a
          v-if="m.sourceUrl"
          :href="m.sourceUrl"
          target="_blank"
          rel="noopener"
          class="source-pill"
        >Source : {{ sourcePath(m.sourceUrl) }}</a>

        <!-- Multi-source (live chat) -->
        <div v-else-if="m.sources && uniqueSources(m.sources).length" class="sources-block">
          <a
            v-for="s in uniqueSources(m.sources)"
            :key="s.url"
            :href="s.url"
            target="_blank"
            rel="noopener"
            class="source-pill"
          >Source : {{ sourcePath(s.url) }}</a>
        </div>
      </div>
    </div>

    <form class="composer" @submit.prevent="send(input)">
      <input
        ref="inputEl"
        v-model="input"
        :disabled="scripting"
        :placeholder="scripting ? 'Un instant…' : 'Posez votre question…'"
        aria-label="Votre question"
      />
      <button type="submit" :disabled="streaming || scripting || !input.trim()" aria-label="Envoyer">
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
  height: min(600px, 78vh);
  min-height: 480px;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 2px 4px -1px rgba(0,0,0,.03), 0 18px 44px -12px rgba(0,0,0,.14);
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
.logo { height: 26px; width: auto; border-radius: 4px; background: #fff; padding: 2px; }
.head-info { display: flex; flex-direction: column; gap: 1px; }
.head-name { font-weight: 600; font-size: 0.9rem; line-height: 1; }
.head-badge { font-size: 11px; opacity: 0.7; }
.online-badge {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  opacity: 0.92;
}
.green-dot {
  width: 7px; height: 7px;
  background: #4ade80;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: .4 } }

/* Stream */
.stream {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Messages */
.msg { display: flex; flex-direction: column; gap: 6px; max-width: 88%; animation: fadeUp .2s ease; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(5px) } to { opacity: 1; transform: none } }
.msg.user { align-self: flex-end; align-items: flex-end; }
.msg.assistant { align-self: flex-start; }

.bubble { padding: 10px 14px; border-radius: 12px; line-height: 1.55; font-size: 0.9rem; }
.msg.user .bubble { background: var(--ink); color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: #F3F3F1; color: var(--ink); border-bottom-left-radius: 4px; }
.md :deep(p) { margin: 0 0 8px; }
.md :deep(p:last-child) { margin-bottom: 0; }
.md :deep(ul), .md :deep(ol) { margin: 6px 0; padding-left: 18px; }
.md :deep(li) { margin-bottom: 4px; }
.md :deep(a) { color: var(--brand); }

/* Typing */
.typing { display: flex; align-items: center; gap: 5px; padding: 13px 16px; min-width: 50px; }
.dot { width: 6px; height: 6px; background: #9ca3af; border-radius: 50%; animation: bounce 1.2s ease-in-out infinite; }
.dot:nth-child(2) { animation-delay: .2s }
.dot:nth-child(3) { animation-delay: .4s }
@keyframes bounce { 0%,80%,100% { transform: none } 40% { transform: translateY(-5px) } }

/* Source pill */
.sources-block { display: flex; flex-direction: column; gap: 3px; }
.source-pill {
  font-family: "DM Mono", monospace;
  font-size: 0.7rem;
  color: var(--quiet);
  text-decoration: none;
  border: 1px solid var(--line);
  padding: 3px 8px;
  border-radius: 5px;
  align-self: flex-start;
  transition: border-color .15s, color .15s;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-pill:hover { color: var(--brand); border-color: var(--brand); }

/* Composer */
.composer { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--line); background: #fff; flex-shrink: 0; }
.composer input {
  flex: 1;
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 11px 14px;
  font-size: 0.9rem;
  outline: none;
  background: var(--stone);
  transition: border-color .15s, background .15s;
  font-family: inherit;
}
.composer input:focus { border-color: var(--brand); background: #fff; }
.composer input:disabled { opacity: .6; }
.composer button {
  width: 40px; height: 40px;
  border: none;
  background: var(--ink);
  color: #fff;
  border-radius: 9px;
  font-size: 1rem; font-weight: 700;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: opacity .15s;
  flex-shrink: 0;
}
.composer button:disabled { opacity: .35; cursor: default; }

.spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg) } }

@media (prefers-reduced-motion: reduce) {
  .msg { animation: none; }
  .green-dot, .dot, .spinner { animation: none; }
}
</style>
