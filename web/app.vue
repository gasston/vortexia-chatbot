<script setup lang="ts">
import { ref, onMounted } from "vue"

type Config = {
  tenant_id: string
  display_name: string
  logo_url: string | null
  primary_color: string
  suggestions: string[]
}

const cfg = useRuntimeConfig().public
const status = ref<"loading" | "ready" | "error">("loading")
const config = ref<Config | null>(null)
const tenant = ref("")

// Prod: {tenant}.demo.getvortexia.com (Traefik). Local dev: ?tenant= or default.
function resolveTenant(): string {
  const m = location.hostname.match(/^([a-z0-9-]+)\.demo\./i)
  if (m) return m[1]
  return new URLSearchParams(location.search).get("tenant") || cfg.defaultTenant
}

onMounted(async () => {
  tenant.value = resolveTenant()
  try {
    config.value = await $fetch<Config>(
      `${cfg.apiBase}/v1/tenants/${tenant.value}/config`,
    )
    if (config.value.primary_color) {
      document.documentElement.style.setProperty("--brand", config.value.primary_color)
    }
    status.value = "ready"
  } catch {
    status.value = "error"
  }
})
</script>

<template>
  <div class="page">
    <div v-if="status === 'loading'" class="center muted">Chargement…</div>
    <div v-else-if="status === 'error'" class="center muted">
      Démo indisponible pour « {{ tenant }} ».
    </div>
    <ChatWindow
      v-else-if="config"
      :api-base="cfg.apiBase"
      :tenant="tenant"
      :config="config"
    />
    <div v-if="status === 'ready'" class="cta-banner">
      Vous voulez ça pour votre site ?
      <a href="https://vortexia.agency/contact" target="_blank" rel="noopener">Contactez-nous →</a>
    </div>
  </div>
</template>

<style>
:root {
  --brand: #111827;
  --bg: #f6f7f9;
  --surface: #ffffff;
  --text: #1f2937;
  --muted: #9ca3af;
  --border: #e5e7eb;
}
* { box-sizing: border-box; }
html, body, #__nuxt { height: 100%; margin: 0; }
body {
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
}
.page { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px 24px 0; }
.cta-banner {
  width: 100%; max-width: 480px;
  padding: 12px 16px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  text-align: center;
  font-size: 0.85rem;
  color: var(--muted);
}
.cta-banner a { color: var(--brand); font-weight: 600; text-decoration: none; margin-left: 6px; }
.cta-banner a:hover { text-decoration: underline; }
.center { display: flex; align-items: center; justify-content: center; height: 100%; }
.muted { color: var(--muted); }
</style>
