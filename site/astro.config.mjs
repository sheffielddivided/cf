// @ts-check
import { defineConfig } from "astro/config";

// GitHub Pages: https://sheffielddivided.github.io/cf/
export default defineConfig({
  site: "https://sheffielddivided.github.io",
  base: "/cf",
  trailingSlash: "always",
  build: { format: "directory" },
});
