import { defineConfig } from "vite";

/** Bó src/runner.ts thành một tệp JS thường (không import) cho background-runner. Chạy sau `vite build`. */
export default defineConfig({
  publicDir: false,
  build: {
    outDir: "dist/runners",
    emptyOutDir: true,
    target: "es2019",
    minify: false,
    lib: { entry: "src/runner.ts", formats: ["iife"], name: "LvRunner", fileName: () => "runner.js" },
  },
});
