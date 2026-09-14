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
const widgetRef = ref<{ open: (fromUser?: boolean) => void } | null>(null)
const demoUrl = ref("")
const demoFormState = ref<"idle" | "success">("idle")

function resolveTenant(): string {
  const m = location.hostname.match(/^([a-z0-9-]+)\.demo\./i)
  if (m) return m[1]
  return new URLSearchParams(location.search).get("tenant") || cfg.defaultTenant
}

function track(event: string) {
  try { (window as any).dataLayer?.push({ event, tenant: tenant.value }) } catch {}
  try { (window as any).umami?.track(event, { tenant: tenant.value }) } catch {}
}

function openDemoChat(e?: Event) {
  e?.preventDefault()
  track("hero_test_assistant_click")
  widgetRef.value?.open(true)
}

function submitDemoForm() {
  const url = demoUrl.value.trim()
  if (!url) return
  track("demo_site_url_submit")
  // ponytail: TODO — needs a public /v1/leads endpoint; /v1/admin/demos requires admin auth
  demoFormState.value = "success"
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
      <div class="hero-inner">
        <p class="proof-line">
          {{ config.pages_count }} pages analysées
          · Réponses sourcées
          · Installation sans modifier votre site
        </p>

        <h1>Votre site peut répondre à vos clients 24h/24.</h1>

        <p class="sub">
          Un assistant IA qui connaît votre site, répond instantanément à vos visiteurs
          et transmet à votre équipe uniquement les demandes qu'il ne sait pas traiter.
        </p>

        <div class="hero-actions">
          <button class="btn-primary" @click="openDemoChat($event)">
            Tester l'assistant
          </button>
          <a href="#how-it-works" class="btn-secondary">Voir comment ça marche</a>
        </div>

        <p class="demo-hint">Démo réelle — essayez l'assistant en bas à droite&nbsp;↘</p>
      </div>
    </section>

    <!-- PAGES ANALYSÉES -->
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

    <!-- COMMENT ÇA MARCHE -->
    <section class="how-it-works" id="how-it-works">
      <div class="hiw-inner">
        <div class="hiw-step">
          <div class="hiw-num">01</div>
          <p><strong>Vortexia analyse votre site.</strong> Toutes les pages publiques crawlées automatiquement, aucune action de votre côté.</p>
        </div>
        <div class="hiw-step">
          <div class="hiw-num">02</div>
          <p><strong>L'assistant répond à vos visiteurs</strong> en temps réel, 24h/24, en citant les sources exactes de votre site.</p>
        </div>
        <div class="hiw-step">
          <div class="hiw-num">03</div>
          <p><strong>Les demandes hors périmètre</strong> sont transmises à votre équipe, triées et résumées automatiquement.</p>
        </div>
      </div>
    </section>

    <!-- QUAND IL NE SAIT PAS -->
    <section class="escalade">
      <div class="escalade-inner">
        <div class="escalade-copy">
          <h2>Quand il ne sait pas, il ne devine pas.</h2>
          <p>
            Une question est couverte par votre site ? Il répond et cite ses sources.<br>
            L'information n'existe pas ? Il ne l'invente pas : il transmet la demande à votre équipe.
          </p>
          <ul class="benefit-list">
            <li>Réponses sourcées</li>
            <li>Aucun contenu inventé</li>
            <li>Transmission à un humain en cas de doute</li>
          </ul>
        </div>
        <div class="escalade-mock">
          <div class="mock-chat">
            <div class="mock-msg user">Est-ce que vous proposez une intégration avec Kavimo ?</div>
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
            <p class="ticket-body">Question sur l'intégration Kavimo. Résumé de la conversation transmis à votre équipe.</p>
          </div>
        </div>
      </div>
      <div class="section-footer">
        <button class="micro-cta" @click="openDemoChat($event)">Voir ce qu'il répond ↘</button>
      </div>
    </section>

    <!-- AVANT / AVEC VORTEXIA -->
    <section class="impact">
      <h2 class="section-h2">Votre équipe ne devrait pas répondre 20 fois à la même question.</h2>
      <div class="impact-grid">
        <div class="impact-col before">
          <div class="impact-label">Avant</div>
          <ul>
            <li>Les mêmes questions reçoivent une réponse manuelle chaque jour</li>
            <li>Les visiteurs du soir repartent sans réponse</li>
            <li>Les vraies demandes arrivent sans contexte</li>
          </ul>
        </div>
        <div class="impact-divider"></div>
        <div class="impact-col after">
          <div class="impact-label">Avec Vortexia</div>
          <ul>
            <li>Les questions répétitives sont absorbées automatiquement</li>
            <li>Les visiteurs obtiennent une réponse immédiate 24h/24</li>
            <li>Les demandes complexes arrivent triées et résumées</li>
          </ul>
        </div>
      </div>
      <div class="section-footer">
        <button class="micro-cta" @click="openDemoChat($event)">Essayez une question ↘</button>
      </div>
    </section>

    <!-- MISE EN PLACE -->
    <section class="setup" id="setup">
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

    <!-- FAQ -->
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
        <p class="faq-footer">
          Vous préférez en discuter ?
          <a
            href="https://vortexia.agency/contact"
            target="_blank"
            rel="noopener"
            @click="track('booking_click')"
          >Réserver 20 minutes →</a>
        </p>
      </div>
    </section>

    <!-- CTA FINAL -->
    <section class="booking" id="contact">
      <div class="booking-inner">
        <h2>Vous voulez le même assistant sur votre site ?</h2>
        <p>Donnez-nous simplement l'adresse de votre site. Nous analysons son contenu et préparons une première démonstration.</p>

        <template v-if="demoFormState === 'idle'">
          <form class="demo-form" @submit.prevent="submitDemoForm">
            <input
              v-model="demoUrl"
              type="url"
              placeholder="https://monsite.fr"
              aria-label="URL de votre site"
              required
              @keydown.enter.prevent="submitDemoForm"
            />
            <button type="submit" class="btn-book">Créer ma démo</button>
          </form>
          <p class="form-reassurance">Aucun accès à votre site nécessaire · Aucun engagement</p>
        </template>

        <div v-else class="demo-success">
          <p class="success-msg">✓ Reçu. On analyse votre site et on revient vers vous sous 24h.</p>
          <a
            href="https://vortexia.agency/contact"
            target="_blank"
            rel="noopener"
            class="btn-book"
            @click="track('booking_click')"
          >Réserver 20 minutes pour la voir</a>
        </div>

        <p class="booking-secondary">
          Vous préférez en discuter d'abord ?
          <a
            href="https://vortexia.agency/contact"
            target="_blank"
            rel="noopener"
            @click="track('booking_click')"
          >Réserver 20 minutes</a>
        </p>

        <p class="credibility">
          Vortexia, agence de développement SaaS et IA, 17 ans d'expérience.
          La mise en place est réalisée par notre équipe, pas déléguée.
        </p>
      </div>
    </section>

    <!-- STICKY CHAT WIDGET -->
    <DemoChatWidget
      ref="widgetRef"
      :api-base="cfg.apiBase"
      :tenant="tenant"
      :config="config"
    />

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
  max-width: 1200px;
  margin: 0 auto;
  padding: 96px 48px 80px;
}
.hero-inner {
  max-width: 680px;
  display: flex;
  flex-direction: column;
  gap: 24px;
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
  max-width: 580px;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
}

.btn-primary {
  display: inline-block;
  background: var(--ink);
  color: #fff;
  padding: 14px 28px;
  border-radius: 6px;
  font-family: "DM Sans", sans-serif;
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-primary:hover { opacity: 0.78; }

.btn-secondary {
  display: inline-flex;
  align-items: center;
  font-size: 0.875rem;
  color: var(--quiet);
  text-decoration: none;
  border-bottom: 1px solid var(--line);
  padding-bottom: 1px;
  transition: color .15s, border-color .15s;
  font-weight: 500;
}
.btn-secondary:hover { color: var(--ink); border-color: var(--ink); }

.demo-hint {
  font-family: "DM Mono", monospace;
  font-size: 0.72rem;
  color: var(--quiet);
  margin: 0;
}

/* SHARED BTN */
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
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
  align-self: flex-start;
}
.btn-book:hover { opacity: 0.78; }

/* MICRO CTA */
.micro-cta {
  font-size: 0.8rem;
  color: var(--quiet);
  background: none;
  border: none;
  border-bottom: 1px solid var(--line);
  padding: 0 0 1px;
  cursor: pointer;
  font-family: inherit;
  transition: color .15s, border-color .15s;
}
.micro-cta:hover { color: var(--ink); border-color: var(--ink); }

.section-footer {
  max-width: 1200px;
  margin: 32px auto 0;
  padding: 0 48px;
  display: flex;
}

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

/* HOW IT WORKS */
.how-it-works {
  background: var(--stone);
  border-top: 1px solid var(--line);
  padding: 72px 48px;
}
.hiw-inner {
  max-width: 1000px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 48px;
}
.hiw-step {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.hiw-num {
  font-family: "DM Mono", monospace;
  font-size: 0.7rem;
  color: var(--quiet);
  letter-spacing: 0.05em;
}
.hiw-step p {
  font-size: 0.875rem;
  color: var(--quiet);
  line-height: 1.65;
  margin: 0;
}
.hiw-step strong { color: var(--ink); }

/* ESCALADE */
.escalade {
  background: var(--surface);
  border-top: 1px solid var(--line);
  padding: 96px 48px 48px;
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
  margin: 0 0 20px;
}
.benefit-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.benefit-list li {
  font-size: 0.875rem;
  color: var(--ink);
  padding-left: 20px;
  position: relative;
  line-height: 1.5;
}
.benefit-list li::before {
  content: "✓";
  position: absolute;
  left: 0;
  color: var(--brand);
  font-size: 0.8rem;
  top: 1px;
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
  background: var(--stone);
  border: 1px solid var(--line);
  color: var(--ink);
  align-self: flex-start;
  border-bottom-left-radius: 3px;
}
.ticket-card {
  background: var(--stone);
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
  background: var(--stone);
  border-top: 1px solid var(--line);
  padding: 96px 48px 48px;
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
  background: var(--surface);
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
  background: var(--stone);
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
.faq-footer {
  margin-top: 32px;
  font-size: 0.875rem;
  color: var(--quiet);
}
.faq-footer a {
  color: var(--ink);
  text-underline-offset: 3px;
}

/* CTA FINAL */
.booking {
  background: var(--surface);
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
.booking-inner > p {
  font-size: 0.9rem;
  color: var(--quiet);
  line-height: 1.65;
  margin: 0;
}

.demo-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}
.demo-form input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 13px 16px;
  font-size: 0.9rem;
  outline: none;
  background: var(--stone);
  transition: border-color .15s;
  font-family: inherit;
  text-align: center;
}
.demo-form input:focus { border-color: var(--ink); background: #fff; }
.demo-form .btn-book { align-self: stretch; text-align: center; }

.form-reassurance {
  font-size: 0.78rem;
  color: var(--quiet);
  margin: 0;
}

.demo-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.success-msg {
  font-size: 0.9rem;
  color: var(--ink);
  margin: 0;
  font-weight: 500;
}

.booking-secondary {
  font-size: 0.82rem;
  color: var(--quiet);
  margin: 0;
}
.booking-secondary a {
  color: var(--ink);
  text-underline-offset: 3px;
}
.credibility {
  font-size: 0.78rem;
  color: var(--quiet);
  line-height: 1.6;
  margin: 0;
}

/* RESPONSIVE */
@media (max-width: 960px) {
  .hero { padding: 64px 24px 56px; }
  .ingestion-inner { grid-template-columns: 1fr; gap: 24px; padding: 32px 24px; }
  .how-it-works { padding: 56px 24px; }
  .hiw-inner { grid-template-columns: 1fr; gap: 32px; }
  .escalade { padding: 64px 24px 40px; }
  .escalade-inner { grid-template-columns: 1fr; gap: 40px; }
  .impact { padding: 64px 24px 40px; }
  .impact-grid { grid-template-columns: 1fr; gap: 32px; }
  .impact-divider { display: none; }
  .section-footer { padding: 0 24px; }
  .setup { padding: 64px 24px; }
  .faq-section { padding: 64px 24px; }
  .booking { padding: 80px 24px; }
}

@media (max-width: 600px) {
  .hero { padding: 48px 20px 40px; }
  h1 { font-size: 1.9rem; }
  .hero-actions { flex-direction: column; align-items: flex-start; }
  .btn-primary { align-self: stretch; text-align: center; }
  .how-it-works { padding: 48px 20px; }
  .escalade { padding: 48px 20px 32px; }
  .impact { padding: 48px 20px 32px; }
  .section-footer { padding: 0 20px; }
  .setup { padding: 48px 20px; }
  .faq-section { padding: 48px 20px; }
  .booking { padding: 64px 20px; }
}
</style>
