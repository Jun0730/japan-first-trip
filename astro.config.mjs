import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import tailwind from '@astrojs/tailwind';

// Live on Vercel's free subdomain as of 2026-08-24. Update this again once a real custom domain is
// purchased and connected in Vercel (Settings > Domains), then update public/robots.txt's Sitemap: line too.
export default defineConfig({
  site: 'https://japan-first-trip.vercel.app',
  integrations: [mdx(), sitemap(), tailwind()],
});
