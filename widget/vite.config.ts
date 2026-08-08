import { defineConfig } from "vite"

// Single self-contained bundle: everything inlined so <script src="widget.js"> is drop-in.
export default defineConfig({
  build: {
    lib: {
      entry: "src/vortexia-chat.ts",
      name: "VortexiaChat",
      formats: ["iife", "es"],
      fileName: (fmt) => (fmt === "iife" ? "widget.js" : "widget.mjs"),
    },
    minify: "terser",
    rollupOptions: { output: { inlineDynamicImports: true } },
  },
})
