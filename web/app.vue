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

function track(event: string) {
  try { (window as any).umami?.track(event, { tenant: tenant.value }) } catch {}
}
</script>

<template>
  <div v-if="status === 'loading'" class="loading-page">Chargement…</div>
  <div v-else class="layout">

    <!-- HERO -->
    <section class="hero">
      <div class="hero-left">
        <div v-if="config" class="eyebrow">Démonstration — {{ config.display_name }}</div>
        <h1>Votre site connaît déjà les réponses.<br><em>Donnons-lui la parole.</em></h1>
        <p class="sub">Un assistant IA qui répond à vos visiteurs à partir du contenu réel de votre site, 24h/24.</p>
        <ul class="perks">
          <li>Réponses basées sur vos données</li>
          <li>Disponible 24h/24</li>
          <li>Installation rapide</li>
        </ul>
        <div class="hero-ctas">
          <a href="#contact" class="btn-primary" @click="track('cta_hero')">Je veux le même assistant</a>
          <a href="#demo" class="btn-ghost">Tester la démo ↓</a>
        </div>
      </div>
      <div class="hero-right" id="demo">
        <div v-if="status === 'error'" class="demo-error">Démo indisponible pour « {{ tenant }} ».</div>
        <ChatWindow v-else-if="config" :api-base="cfg.apiBase" :tenant="tenant" :config="config" />
      </div>
    </section>

    <!-- FEATURES -->
    <section class="features">
      <div class="feat">
        <div class="feat-title">Réponses fiables</div>
        <div class="feat-text">L'assistant répond à partir du contenu réel de votre site, pas depuis Internet.</div>
      </div>
      <div class="feat">
        <div class="feat-title">Installation simple</div>
        <div class="feat-text">Ajoutez le widget à votre site sans reconstruire votre stack.</div>
      </div>
      <div class="feat">
        <div class="feat-title">À votre image</div>
        <div class="feat-text">Logo, couleurs, ton et comportement adaptés à votre marque.</div>
      </div>
    </section>

    <!-- HOW IT WORKS -->
    <section class="how">
      <h2 class="section-title">Comment ça marche ?</h2>
      <div class="steps">
        <div class="step">
          <span class="step-n">1</span>
          <span class="step-label">Nous analysons votre site</span>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <span class="step-n">2</span>
          <span class="step-label">L'assistant apprend votre contenu</span>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <span class="step-n">3</span>
          <span class="step-label">Vous ajoutez le widget</span>
        </div>
      </div>
    </section>

    <!-- CTA FINAL -->
    <section class="cta-section" id="contact">
      <h2>Vous voulez le même assistant sur votre site ?</h2>
      <p>Transformez votre contenu existant en assistant commercial et support disponible 24h/24.</p>
      <a
        href="https://vortexia.agency/contact"
        target="_blank"
        rel="noopener"
        class="btn-primary btn-lg"
        @click="track('cta_contact')"
      >Demander une démo</a>
    </section>

  </div>
</template>

<style>
:root {
  --brand: #111827;
  --bg: #ffffff;
  --surface: #ffffff;
  --text: #0a0a0a;
  --muted: #6b7280;
  --border: #e5e7eb;
  --subtle: #f9fafb;
}
* { box-sizing: border-box; }
html, body, #__nuxt { margin: 0; }
body {
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}

/* LOADING */
.loading-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  font-size: 0.9rem;
}

/* HERO */
.hero {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  max-width: 1140px;
  margin: 0 auto;
  padding: 80px 40px;
  align-items: center;
  min-height: 100vh;
}

.hero-left {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.eyebrow {
  font-size: 12px;
  font-weight: 500;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

h1 {
  font-size: clamp(2rem, 3.5vw, 2.8rem);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.025em;
  color: var(--text);
  margin: 0;
}
h1 em {
  font-style: normal;
  color: var(--brand);
}

.sub {
  font-size: 1.05rem;
  color: var(--muted);
  line-height: 1.65;
  margin: 0;
  max-width: 400px;
}

.perks {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.perks li {
  font-size: 0.9rem;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 10px;
}
.perks li::before {
  content: "";
  width: 5px;
  height: 5px;
  background: var(--brand);
  border-radius: 50%;
  flex-shrink: 0;
}

.hero-ctas {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.btn-primary {
  background: var(--text);
  color: #fff;
  padding: 12px 22px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none;
  transition: opacity 0.15s;
  display: inline-block;
}
.btn-primary:hover { opacity: 0.8; }

.btn-ghost {
  background: transparent;
  color: var(--muted);
  padding: 12px 22px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.9rem;
  text-decoration: none;
  border: 1px solid var(--border);
  transition: color 0.15s, border-color 0.15s;
  display: inline-block;
}
.btn-ghost:hover { color: var(--text); border-color: #9ca3af; }

.btn-lg { padding: 15px 32px; font-size: 0.95rem; }

.demo-error {
  color: var(--muted);
  font-size: 0.9rem;
  text-align: center;
  padding: 40px;
}

/* FEATURES */
.features {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.feat {
  padding: 48px 40px;
  border-right: 1px solid var(--border);
}
.feat:last-child { border-right: none; }
.feat-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 10px;
}
.feat-text {
  font-size: 0.875rem;
  color: var(--muted);
  line-height: 1.65;
}

/* HOW */
.how {
  max-width: 760px;
  margin: 0 auto;
  padding: 80px 40px;
  text-align: center;
}
.section-title {
  font-size: 1.4rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text);
  margin: 0 0 48px;
}
.steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 12px;
}
.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  flex: 1;
  max-width: 160px;
}
.step-n {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--text);
  color: #fff;
  font-size: 0.8rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.step-label {
  font-size: 0.875rem;
  color: var(--text);
  font-weight: 500;
  line-height: 1.4;
}
.step-arrow {
  color: var(--border);
  font-size: 1.2rem;
  margin-top: 10px;
  flex-shrink: 0;
}

/* CTA FINAL */
.cta-section {
  background: var(--subtle);
  border-top: 1px solid var(--border);
  text-align: center;
  padding: 96px 40px;
}
.cta-section h2 {
  font-size: clamp(1.4rem, 3vw, 2rem);
  font-weight: 700;
  color: var(--text);
  margin: 0 0 16px;
  letter-spacing: -0.02em;
}
.cta-section p {
  color: var(--muted);
  font-size: 1rem;
  line-height: 1.6;
  margin: 0 auto 32px;
  max-width: 460px;
}

/* RESPONSIVE */
@media (max-width: 960px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 48px;
    padding: 56px 24px;
    min-height: auto;
  }
  .sub { max-width: 100%; }
  .features { grid-template-columns: 1fr; }
  .feat { border-right: none; border-bottom: 1px solid var(--border); padding: 32px 24px; }
  .feat:last-child { border-bottom: none; }
  .how { padding: 56px 24px; }
  .cta-section { padding: 64px 24px; }
}

@media (max-width: 600px) {
  h1 { font-size: 1.75rem; }
  .hero-ctas { flex-direction: column; }
  .btn-primary, .btn-ghost { text-align: center; }
  .steps { flex-direction: column; align-items: center; gap: 8px; }
  .step { max-width: 100%; flex-direction: row; gap: 16px; text-align: left; }
  .step-label { text-align: left; }
  .step-arrow { transform: rotate(90deg); margin: 0; }
}
</style>
