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
})
