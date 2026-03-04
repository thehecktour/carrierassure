import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./setup.js"],
    include: ["tests/**/*.{test,spec}.{js,jsx}", "tests/**/*.jsx"],
  },
});