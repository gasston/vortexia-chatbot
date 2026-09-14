<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from "vue"

type Config = {
  display_name: string
  logo_url: string | null
  suggestions: string[]
  scripted_qa?: { question: string; answer: string; source_url: string | null }[]
  pages_count: number
}

const props = defineProps<{ apiBase: string; tenant: string; config: Config }>()

const isOpen = ref(false)
const sessionClosed = ref(false)
const hasInteracted = ref(false)
const chatRef = ref<{ focusInput: () => void; send: (text: string) => Promise<void> } | null>(null)

const suggestions = computed(() => props.config.suggestions.slice(0, 3))

function track(event: string) {
  try { (window as any).dataLayer?.push({ event, tenant: props.tenant }) } catch {}
  try { (window as any).umami?.track(event, { tenant: props.tenant }) } catch {}
}

function open(fromUser = false) {
  if (isOpen.value) return
  isOpen.value = true
  track(fromUser ? "demo_widget_open" : "demo_widget_auto_open")
  if (fromUser) nextTick(() => chatRef.value?.focusInput())
}

function close() {
  isOpen.value = false
  sessionClosed.value = true
  track("demo_widget_close")
}

function toggle() {
  if (isOpen.value) close(); else open(true)
}

async function sendSuggestion(q: string) {
  hasInteracted.value = true
  track("demo_suggested_question_click")
  await chatRef.value?.send(q)
}

defineExpose({ open })

onMounted(() => {
  setTimeout(() => { if (!sessionClosed.value) open() }, 1000)
})

function onRootKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && isOpen.value) close()
}
</script>

<template>
  <div class="widget-root" @keydown="onRootKeydown">
    <!-- Launcher bubble -->
    <button
      class="launcher"
      @click="toggle"
      :aria-label="isOpen ? 'Fermer l\'assistant' : 'Ouvrir l\'assistant'"
      :aria-expanded="String(isOpen)"
    >
      <svg v-if="!isOpen" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
      <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
        <path d="M18 6L6 18M6 6l12 12"/>
      </svg>
      <span v-if="!isOpen" class="online-dot" aria-hidden="true"></span>
    </button>

    <!-- Chat panel -->
    <div
      class="widget-panel"
      :class="{ 'widget-panel--open': isOpen }"
      role="dialog"
      aria-label="Assistant IA — démo Vortexia"
      :aria-hidden="String(!isOpen)"
    >
      <!-- Widget header -->
      <div class="widget-head">
        <div class="widget-head-info">
          <img v-if="config.logo_url" :src="config.logo_url" :alt="config.display_name" class="widget-logo" />
          <div class="widget-head-text">
            <div class="widget-brand">{{ config.display_name }}</div>
            <div class="widget-sub">Démo Vortexia · {{ config.pages_count }} pages analysées</div>
          </div>
        </div>
        <div class="widget-head-right">
          <span class="widget-online" aria-hidden="true">
            <span class="green-dot"></span>En ligne
          </span>
          <button
            class="widget-close"
            @click="close"
            aria-label="Fermer l'assistant"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Intro + suggestion chips (hidden after first interaction) -->
      <div v-if="!hasInteracted && suggestions.length" class="widget-intro">
        <p class="intro-greeting">
          👋 Testez-moi.<br>
          <span class="intro-scope">Je réponds uniquement à partir du contenu du site {{ config.display_name }}.</span>
        </p>
        <div class="suggestions" role="list">
          <button
            v-for="q in suggestions"
            :key="q"
            class="suggestion-chip"
            role="listitem"
            @click="sendSuggestion(q)"
          >{{ q }}</button>
        </div>
      </div>

      <!-- Chat window -->
      <ChatWindow
        ref="chatRef"
        :api-base="apiBase"
        :tenant="tenant"
        :config="config"
        hide-header
        widget-mode
        @user-message="hasInteracted = true"
      />
    </div>
  </div>
</template>

<style scoped>
.widget-root {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

/* Launcher */
.launcher {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: var(--ink);
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0,0,0,.22);
  position: relative;
  transition: opacity .15s, transform .15s;
  flex-shrink: 0;
}
.launcher:hover { opacity: .88; transform: scale(1.04); }
.launcher:focus-visible { outline: 2px solid var(--brand); outline-offset: 3px; }
.launcher:active { transform: scale(.97); }

.online-dot {
  position: absolute;
  top: 9px;
  right: 9px;
  width: 11px;
  height: 11px;
  background: #4ade80;
  border-radius: 50%;
  border: 2px solid var(--ink);
  animation: pulse-dot 2.5s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: .65; }
}

/* Panel */
.widget-panel {
  width: 400px;
  max-width: calc(100vw - 24px);
  height: 620px;
  max-height: calc(100dvh - 100px);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,.06), 0 24px 60px -12px rgba(0,0,0,.2);
  display: flex;
  flex-direction: column;
  transform-origin: bottom right;
  transform: scale(0.92) translateY(12px);
  opacity: 0;
  pointer-events: none;
  transition: transform .22s cubic-bezier(.16,1,.3,1), opacity .18s ease;
}
.widget-panel--open {
  transform: scale(1) translateY(0);
  opacity: 1;
  pointer-events: all;
}

/* Widget header */
.widget-head {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  background: var(--brand);
  color: #fff;
  flex-shrink: 0;
  gap: 8px;
  min-height: 54px;
}
.widget-head-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.widget-logo { height: 24px; width: auto; border-radius: 4px; background: #fff; padding: 2px; flex-shrink: 0; }
.widget-head-text { min-width: 0; }
.widget-brand { font-weight: 600; font-size: 0.875rem; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.widget-sub { font-size: 0.68rem; opacity: 0.72; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.widget-head-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.widget-online { display: flex; align-items: center; gap: 5px; font-size: 11px; opacity: .9; white-space: nowrap; }
.green-dot { width: 7px; height: 7px; background: #4ade80; border-radius: 50%; flex-shrink: 0; }

.widget-close {
  background: none;
  border: none;
  color: rgba(255,255,255,.75);
  cursor: pointer;
  padding: 5px;
  display: flex;
  align-items: center;
  border-radius: 5px;
  transition: color .15s, background .15s;
  line-height: 0;
}
.widget-close:hover { color: #fff; background: rgba(255,255,255,.12); }
.widget-close:focus-visible { outline: 2px solid rgba(255,255,255,.5); }

/* Intro */
.widget-intro {
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--stone);
  flex-shrink: 0;
}
.intro-greeting {
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--ink);
  margin: 0 0 10px;
}
.intro-scope { font-size: 0.78rem; color: var(--quiet); }

.suggestions {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.suggestion-chip {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 11px;
  font-size: 0.8rem;
  color: var(--ink);
  text-align: left;
  cursor: pointer;
  transition: border-color .15s, background .15s;
  font-family: inherit;
  line-height: 1.4;
}
.suggestion-chip:hover { border-color: var(--ink); background: #f5f5f3; }
.suggestion-chip:focus-visible { outline: 2px solid var(--brand); }

/* Chat fills remainder */
.widget-panel :deep(.chat.widget-mode) {
  flex: 1;
  min-height: 0;
}

@media (max-width: 480px) {
  .widget-root {
    bottom: 16px;
    right: 12px;
  }
  .launcher { width: 54px; height: 54px; }
  .widget-panel {
    width: calc(100vw - 24px);
    height: calc(100dvh - 90px);
    max-height: calc(100dvh - 90px);
    border-radius: 14px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .widget-panel { transition: none; }
  .launcher { transition: none; }
  .online-dot { animation: none; }
}
</style>
