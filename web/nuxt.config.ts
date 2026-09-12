export default defineNuxtConfig({
  // ponytail: demo is a fully dynamic per-tenant chat — SSR buys nothing, adds hydration edge cases.
  ssr: false,
  devServer: { port: 3000 },
  runtimeConfig: {
    public: {
      // Override via NUXT_PUBLIC_API_BASE / NUXT_PUBLIC_DEFAULT_TENANT
      apiBase: "http://localhost:8000",
      defaultTenant: "vortexia", // used in local dev when no {tenant}.demo.* subdomain
    },
  },
  app: {
    head: {
      link: [
        { rel: "preconnect", href: "https://fonts.googleapis.com" },
        { rel: "preconnect", href: "https://fonts.gstatic.com", crossorigin: "" },
        {
          rel: "stylesheet",
          href: "https://fonts.googleapis.com/css2?family=DM+Mono:wght@400&family=DM+Sans:wght@400;500;600&family=Instrument+Serif:ital@1&display=swap",
        },
      ],
      script: [
        {
          src: "https://analytics.vortexia.agency/script.js",
          defer: true,
          "data-website-id": "598de917-b4b7-4e02-954b-c1df4f71cc84",
        },
      ],
    },
  },
})
