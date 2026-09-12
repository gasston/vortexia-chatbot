<script setup lang="ts">
import { ref, onMounted } from "vue"

type ScriptedQA = { question: string; answer: string; source_url: string | null }
type SamplePage = { title: string | null; url: string }
type Config = {
  tenant_id: string
  display_name: string
  logo_url: string | null
  primary_color: string
  suggestions: string[]
  pages_count: number
  crawled_at: string | null
  sample_pages: SamplePage[]
  scripted_qa: ScriptedQA[]
}

const cfg = useRuntimeConfig().public
const status = ref<"loading" | "ready" | "error">("loading")
const config = ref<Config | null>(null)
const tenant = ref("")
const chatRef = ref<{ focusInput: () => void } | null>(null)

function resolveTenant(): string {
  const m = location.hostname.match(/^([a-z0-9-]+)\.demo\./i)
  if (m) return m[1]
  return new URLSearchParams(location.search).get("tenant") || cfg.defaultTenant
}

function fmtDate(iso: string | null): string {
  if (!iso) return ""
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" }).format(new Date(iso))
}

function fmtDomain(url: string): string {
  try { return new URL(url).hostname.replace("www.", "") } catch { return url }
}

function focusChat(e: Event) {
  e.preventDefault()
  document.getElementById("demo")?.scrollIntoView({ behavior: "smooth" })
  setTimeout(() => chatRef.value?.focusInput(), 600)
}

function track(event: string) {
  try { (window as any).umami?.track(event, { tenant: tenant.value }) } catch {}
}

onMounted(async () => {
  tenant.value = resolveTenant()
  try {
    config.value = await $fetch<Config>(`${cfg.apiBase}/v1/tenants/${tenant.value}/config`)
    if (config.value.primary_color) {
      document.documentElement.style.setProperty("--brand", config.value.primary_color)
    }
    status.value = "ready"
    track("demo_view")
    useHead({
      title: `${config.value.display_name} — Assistant IA par Vortexia`,
      meta: [
        { property: "og:title", content: `Votre assistant IA est prêt — ${config.value.display_name}` },
        { property: "og:description", content: `Posez une vraie question sur ${config.value.display_name} et voyez la réponse en direct.` },
      ],
    })
  } catch {
    status.value = "error"
  }
})
</script>

<template>
  <div v-if="status === 'loading'" class="loading-page">Chargement…</div>
  <div v-else-if="status === 'error'" class="loading-page">Démo indisponible pour « {{ tenant }} ».</div>
  <div v-else-if="config" class="layout">

    <!-- HERO -->
    <section class="hero">
      <div class="hero-left">
        <p class="proof-line">
          Assistant entraîné sur <strong>{{ config.pages_count }} pages</strong> de
          <strong>{{ fmtDomain(config.sample_pages[0]?.url || '') || config.display_name }}</strong>
          <span v-if="config.crawled_at">, analysées le {{ fmtDate(config.crawled_at) }}</span>.
        </p>

        <!--
          Variante A (active) : directe, nocturne, bénéfice immédiat
          Variante B : "Vos visiteurs posent les mêmes questions depuis six mois. Personne ne répond après 19 h."
          Variante C : "Un assistant qui connaît {{ config.display_name }} mieux que votre dernier stagiaire."
        -->
        <h1>Cette nuit, votre site répondra à vos clients sans vous.</h1>

        <p class="sub">
          {{ config.display_name }} a déjà toutes les réponses. L'assistant les délivre à vos visiteurs, à partir du contenu réel de votre site, jamais depuis internet.
          Quand la question dépasse son périmètre, il le dit franchement et crée un ticket résumé pour votre équipe.
        </p>

        <div class="hero-actions">
          <a href="#contact" class="btn-book" @click="track('cta_hero')">Réserver 20 minutes</a>
          <span class="reassurance">Mise en place faite par nous, rien à installer côté marchand, pas d'engagement.</span>
        </div>

        <a href="#demo" class="try-link" @click="focusChat">Essayez, posez-lui une vraie question</a>
      </div>

      <div class="hero-right" id="demo">
        <ChatWindow
          ref="chatRef"
          :api-base="cfg.apiBase"
          :tenant="tenant"
          :config="config"
        />
      </div>
    </section>

    <!-- CE QU'IL A LU -->
    <section class="ingestion" v-if="config.sample_pages.length">
      <div class="ingestion-inner">
        <div class="ingestion-meta">
          <span class="ingestion-count">{{ config.pages_count }} pages analysées</span>
          <span class="ingestion-scope">Il ne répond que depuis ces pages, jamais depuis internet.</span>
        </div>
        <ul class="page-list">
          <li v-for="p in config.sample_pages" :key="p.url">
            <a :href="p.url" target="_blank" rel="noopener" class="page-item">
              <span class="page-title">{{ p.title || p.url }}</span>
              <span class="page-url">{{ p.url }}</span>
            </a>
          </li>
        </ul>
      </div>
    </section>

    <!-- QUAND IL NE SAIT PAS -->
    <section class="escalade">
      <div class="escalade-inner">
        <div class="escalade-copy">
          <h2>Quand il ne sait pas, il ne devine pas.</h2>
          <p>
            L'assistant répond à partir d'un périmètre défini. Pour toute question hors périmètre,
            il le dit clairement, crée un ticket, et résume la conversation pour l'agent qui prend le relais.
            Vos clients obtiennent toujours une réponse honnête.
          </p>
        </div>
        <div class="escalade-mock">
          <div class="mock-chat">
            <div class="mock-msg user">Est-ce que vous proposez une intégration avec Klaviyo ?</div>
            <div class="mock-msg assistant">
              Cette information ne figure pas dans les pages que j'ai analysées. Je crée un ticket pour que votre équipe puisse vous répondre précisément.
            </div>
          </div>
          <div class="ticket-card">
            <div class="ticket-header">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="1" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M4 5h6M4 7.5h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              Ticket créé
              <span class="ticket-badge">Nouveau</span>
            </div>
            <p class="ticket-body">Question sur l'intégration Klaviyo. Résumé de la conversation transmis à votre équipe.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- CE QUE CA CHANGE -->
    <section class="impact">
      <h2 class="section-h2">Ce que ça change dans la semaine</h2>
      <div class="impact-grid">
        <div class="impact-col before">
          <div class="impact-label">Avant</div>
          <ul>
            <li>Les mêmes questions reçoivent une réponse manuelle chaque jour</li>
            <li>Les visiteurs après 19h n'ont personne</li>
            <li>L'équipe trie les tickets sans contexte</li>
          </ul>
        </div>
        <div class="impact-divider"></div>
        <div class="impact-col after">
          <div class="impact-label">Après</div>
          <ul>
            <li>Les questions répétitives sont absorbées automatiquement</li>
            <li>Les visiteurs de 23h obtiennent une réponse immédiate</li>
            <li>Les vraies demandes arrivent triées et résumées</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- MISE EN PLACE -->
    <section class="setup">
      <h2 class="section-h2">Comment on met ça en place</h2>
      <ol class="setup-steps">
        <li>
          <div class="step-content">
            <strong>Nous analysons votre site, aucune action de votre côté.</strong>
            <span class="step-detail">On crawle les pages produit, la FAQ, les CGV. Délai : 24h.</span>
          </div>
        </li>
        <li>
          <div class="step-content">
            <strong>Nous chargeons votre FAQ et calons le ton. Vous validez les réponses.</strong>
            <span class="step-detail">Une session de 30 minutes avec vous, c'est tout ce qu'on demande.</span>
          </div>
        </li>
        <li>
          <div class="step-content">
            <strong>Nous installons le widget. Vous recevez le lien du dashboard.</strong>
            <span class="step-detail">Mise en ligne immédiate. Vous gardez la main à tout moment.</span>
          </div>
        </li>
      </ol>
    </section>

    <!-- OBJECTIONS -->
    <section class="faq-section">
      <div class="faq-inner">
        <h2 class="section-h2">Questions fréquentes</h2>
        <div class="faq-list">
          <details class="faq-item">
            <summary>Combien ça coûte ?</summary>
            <p>Les premiers marchands accèdent gratuitement ou à tarif réduit en échange de retours. On en parle lors des 20 minutes.</p>
          </details>
          <details class="faq-item">
            <summary>Où vont mes données ?</summary>
            <p>Uniquement les pages publiques de votre site, hébergées sur nos serveurs en Europe. Rien n'est partagé avec des tiers.</p>
          </details>
          <details class="faq-item">
            <summary>Est-ce que ça ralentit mon site ?</summary>
            <p>Non. Le widget se charge de façon asynchrone et n'impacte pas le rendu de votre page.</p>
          </details>
          <details class="faq-item">
            <summary>Est-ce que je peux le retirer ?</summary>
            <p>Une ligne de code à supprimer et c'est terminé. Aucune dépendance côté backend.</p>
          </details>
          <details class="faq-item">
            <summary>Dans quelles langues il répond ?</summary>
            <p>Il répond dans la langue du visiteur, à partir du contenu de votre site. Si votre site est en français, il répond en français.</p>
          </details>
        </div>
      </div>
    </section>

    <!-- CTA FINAL -->
    <section class="booking" id="contact">
      <div class="booking-inner">
        <h2>Vous voulez le même assistant sur votre site ?</h2>
        <p>Réservez 20 minutes. On analyse votre site avant l'appel et on arrive avec une démo de votre propre assistant.</p>
        <a
          href="https://vortexia.agency/contact"
          target="_blank"
          rel="noopener"
          class="btn-book"
          @click="track('cta_contact')"
        >Réserver 20 minutes</a>
        <p class="credibility">
          Vortexia, agence de développement SaaS et IA, 17 ans d'expérience.
          La mise en place est réalisée par notre équipe, pas déléguée.
        </p>
      </div>
    </section>

  </div>
</template>

<style>
:root {
  --brand: #0C0C0C;
  --ink: #0C0C0C;
  --stone: #F7F7F5;
  --surface: #FFFFFF;
  --line: #E2E2E0;
  --quiet: #8A8A85;
}

* { box-sizing: border-box; }
html, body, #__nuxt { margin: 0; }
body {
  font-family: "DM Sans", ui-sans-serif, system-ui, -apple-system, sans-serif;
  background: var(--stone);
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
}

/* LOADING */
.loading-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--quiet);
  font-size: 0.875rem;
}

/* HERO */
.hero {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 72px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 72px 48px;
  min-height: 100vh;
  align-items: center;
}

.hero-left {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.proof-line {
  font-family: "DM Mono", monospace;
  font-size: 0.72rem;
  color: var(--quiet);
  margin: 0;
  line-height: 1.6;
}

h1 {
  font-family: "Instrument Serif", Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: clamp(2.2rem, 4vw, 3.4rem);
  line-height: 1.1;
  letter-spacing: -0.01em;
  color: var(--ink);
  margin: 0;
}

.sub {
  font-size: 1rem;
  color: var(--quiet);
  line-height: 1.7;
  margin: 0;
}

.hero-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn-book {
  display: inline-block;
  background: var(--ink);
  color: #fff;
  padding: 14px 28px;
  border-radius: 6px;
  font-family: "DM Sans", sans-serif;
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none;
  transition: opacity 0.15s;
  align-self: flex-start;
}
.btn-book:hover { opacity: 0.78; }

.reassurance {
  font-size: 0.8rem;
  color: var(--quiet);
  line-height: 1.5;
}

.try-link {
  font-size: 0.875rem;
  color: var(--quiet);
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
  align-self: flex-start;
  background: none;
  border: none;
  padding: 0;
  font-family: inherit;
  transition: color 0.15s;
}
.try-link:hover { color: var(--ink); }

/* INGESTION BAND */
.ingestion {
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  background: var(--surface);
}
.ingestion-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 48px;
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 48px;
  align-items: start;
}
.ingestion-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 2px;
}
.ingestion-count {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--ink);
}
.ingestion-scope {
  font-size: 0.78rem;
  color: var(--quiet);
  line-height: 1.5;
}
.page-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
}
.page-item {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
  text-decoration: none;
}
.page-item:last-child { border-bottom: none; }
.page-title {
  font-size: 0.875rem;
  color: var(--ink);
  font-weight: 500;
  transition: color 0.15s;
}
.page-item:hover .page-title { color: var(--brand); }
.page-url {
  font-family: "DM Mono", monospace;
  font-size: 0.7rem;
  color: var(--quiet);
}

/* ESCALADE */
.escalade {
  background: var(--stone);
  padding: 96px 48px;
}
.escalade-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 80px;
  align-items: center;
}
.escalade-copy h2 {
  font-family: "Instrument Serif", Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: clamp(1.6rem, 2.5vw, 2.2rem);
  line-height: 1.2;
  margin: 0 0 20px;
  letter-spacing: -0.01em;
}
.escalade-copy p {
  font-size: 0.9rem;
  color: var(--quiet);
  line-height: 1.75;
  margin: 0;
}
.mock-chat {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.mock-msg {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 0.875rem;
  line-height: 1.5;
  max-width: 85%;
}
.mock-msg.user {
  background: var(--ink);
  color: #fff;
  align-self: flex-end;
  border-bottom-right-radius: 3px;
}
.mock-msg.assistant {
  background: var(--surface);
  border: 1px solid var(--line);
  color: var(--ink);
  align-self: flex-start;
  border-bottom-left-radius: 3px;
}
.ticket-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px 16px;
}
.ticket-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 8px;
}
.ticket-badge {
  margin-left: auto;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--brand);
  background: color-mix(in srgb, var(--brand) 10%, transparent);
  padding: 2px 8px;
  border-radius: 20px;
}
.ticket-body {
  font-size: 0.8rem;
  color: var(--quiet);
  margin: 0;
  line-height: 1.5;
}

/* IMPACT */
.impact {
  background: var(--surface);
  border-top: 1px solid var(--line);
  padding: 96px 48px;
}
.section-h2 {
  font-family: "Instrument Serif", Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: clamp(1.5rem, 2.5vw, 2rem);
  letter-spacing: -0.01em;
  text-align: center;
  margin: 0 0 56px;
}
.impact-grid {
  max-width: 860px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1px 1fr;
  gap: 48px;
  align-items: start;
}
.impact-divider { background: var(--line); }
.impact-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--quiet);
  margin-bottom: 20px;
}
.impact-col ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.impact-col.before ul li { color: var(--quiet); }
.impact-col.after ul li { color: var(--ink); }
.impact-col li {
  font-size: 0.875rem;
  line-height: 1.55;
  padding-left: 16px;
  position: relative;
}
.impact-col.before li::before { content: ""; position: absolute; left: 0; top: 8px; width: 5px; height: 1px; background: var(--line); }
.impact-col.after li::before { content: ""; position: absolute; left: 0; top: 7px; width: 5px; height: 5px; background: var(--brand); border-radius: 50%; }

/* SETUP */
.setup {
  background: var(--stone);
  border-top: 1px solid var(--line);
  padding: 96px 48px;
}
.setup-steps {
  max-width: 600px;
  margin: 0 auto;
  padding: 0;
  list-style: none;
  counter-reset: steps;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.setup-steps li {
  counter-increment: steps;
  display: flex;
  gap: 24px;
  padding: 28px 0;
  border-bottom: 1px solid var(--line);
  align-items: flex-start;
}
.setup-steps li:last-child { border-bottom: none; }
.setup-steps li::before {
  content: counter(steps);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--ink);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}
.step-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.step-content strong {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
}
.step-detail {
  font-size: 0.82rem;
  color: var(--quiet);
}

/* FAQ */
.faq-section {
  background: var(--surface);
  border-top: 1px solid var(--line);
  padding: 96px 48px;
}
.faq-inner {
  max-width: 640px;
  margin: 0 auto;
}
.faq-list { display: flex; flex-direction: column; }
.faq-item summary {
  list-style: none;
  cursor: pointer;
  padding: 20px 0;
  font-size: 0.9rem;
  font-weight: 500;
  border-bottom: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  color: var(--ink);
  user-select: none;
  transition: color 0.15s;
}
.faq-item summary:hover { color: var(--brand); }
.faq-item summary::-webkit-details-marker { display: none; }
.faq-item summary::after {
  content: "+";
  font-size: 1.1rem;
  font-weight: 400;
  color: var(--quiet);
  transition: transform 0.2s;
  flex-shrink: 0;
}
.faq-item[open] summary::after { transform: rotate(45deg); }
.faq-item[open] summary { border-bottom-color: transparent; }
.faq-item p {
  padding: 0 0 20px;
  font-size: 0.875rem;
  color: var(--quiet);
  line-height: 1.7;
  margin: 0;
  border-bottom: 1px solid var(--line);
}

/* CTA FINAL */
.booking {
  background: var(--stone);
  border-top: 1px solid var(--line);
  padding: 112px 48px;
}
.booking-inner {
  max-width: 520px;
  margin: 0 auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}
.booking-inner h2 {
  font-family: "Instrument Serif", Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: clamp(1.8rem, 3vw, 2.4rem);
  letter-spacing: -0.01em;
  margin: 0;
  line-height: 1.15;
}
.booking-inner p {
  font-size: 0.9rem;
  color: var(--quiet);
  line-height: 1.65;
  margin: 0;
}
.credibility {
  font-size: 0.78rem !important;
  color: var(--quiet);
  line-height: 1.6 !important;
  margin-top: 8px !important;
}

/* RESPONSIVE */
@media (max-width: 960px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 40px;
    padding: 48px 24px;
    min-height: auto;
  }
  .escalade { padding: 64px 24px; }
  .escalade-inner { grid-template-columns: 1fr; gap: 40px; }
  .impact { padding: 64px 24px; }
  .impact-grid { grid-template-columns: 1fr; gap: 32px; }
  .impact-divider { display: none; }
  .setup { padding: 64px 24px; }
  .faq-section { padding: 64px 24px; }
  .booking { padding: 80px 24px; }
  .ingestion-inner { grid-template-columns: 1fr; gap: 24px; padding: 32px 24px; }
}

@media (max-width: 600px) {
  .hero { padding: 36px 20px; }
  h1 { font-size: 1.9rem; }
  .btn-book { align-self: stretch; text-align: center; }
  .escalade { padding: 48px 20px; }
  .impact { padding: 48px 20px; }
  .setup { padding: 48px 20px; }
  .faq-section { padding: 48px 20px; }
  .booking { padding: 64px 20px; }
}
</style>
