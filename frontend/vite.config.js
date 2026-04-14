import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [svelte(), tailwindcss()],
  root: ".",
  base: "/static/",
  build: {
    outDir: "dist",
    manifest: true,
    rollupOptions: {
      input: {
        main: "src/main.js",
      },
    },
  },
  server: {
    port: 5176,
    origin: "http://localhost:5176",
  },
});
