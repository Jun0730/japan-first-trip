import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import tailwind from '@astrojs/tailwind';

// TODO: replace with your real domain before deploying (used for sitemap + canonical URLs)
// Placeholder only — SITE_TITLE in src/consts.ts ("Japan First Trip") is also a working title pending a final
// brand/domain decision.
export default defineConfig({
  site: 'https://www.example-japan-first-trip.com',
  integrations: [mdx(), sitemap(), tailwind()],
});
