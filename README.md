# Japan First Trip

_(Working title — see `SITE_TITLE` in `src/consts.ts`. Final brand name / domain not yet decided.)_

An Astro-based affiliate content site for English-speaking, first-time visitors to Japan (initially expanded
from an earlier Kansai-only version — see `japan-travel-media/00_handover.md` for the full business plan).
Monetized via eSIM/connectivity affiliates (Airalo, Ubigi, Holafly, Sakura Mobile), accommodation affiliates
(Booking.com, Agoda), activity affiliates (Klook, Viator, GetYourGuide) and transportation affiliates
(Klook, JRPass.com, Japan Experience, Discover Cars).

## Stack

- [Astro](https://astro.build) (static output) + TypeScript
- Tailwind CSS
- Content Collections (Markdown) for all articles
- `@astrojs/sitemap` for `sitemap-index.xml`

## Getting started

```bash
npm install
npm run dev
```

Site runs at `http://localhost:4321`.

```bash
npm run build    # type-checks then builds to dist/
npm run preview  # serves the built dist/ locally
```

> A `dev-server.cmd` file and `.claude/launch.json` exist in this repo only to support this session's
> automated browser preview tool. They're harmless to keep but not needed for normal development — plain
> `npm run dev` works once Node.js is on your PATH.

## Content model

Everything lives under `src/content/` as Markdown (or MDX), split into seven collections defined in
`src/content/config.ts`:

| Collection       | URL prefix          | Notes                                                        |
|------------------|----------------------|---------------------------------------------------------------|
| `esim`           | `/esim/`             | Single-provider eSIM/connectivity CTAs (Airalo, Ubigi, ...)   |
| `hotels`         | `/where-to-stay/`    | Booking.com/Agoda affiliate CTAs                              |
| `activities`     | `/things-to-do/`     | Klook/Viator/GetYourGuide affiliate CTAs                      |
| `transportation` | `/transportation/`   | JR Pass/airport transfer/rental car affiliate CTAs            |
| `guides`         | `/guides/`           | City guides (Kyoto, Osaka, Nara, ... — expanding beyond Kansai) |
| `itineraries`    | `/itineraries/`      | Multi-day sample routes                                       |
| `blog`           | `/blog/`             | Long-tail SEO + comparison articles (multi-provider, use `.mdx` to embed `<AffiliateButton>` for more than one CTA) |

`esim`, `activities`, `hotels` and `transportation` entries have `provider` and `affiliateUrl` frontmatter
fields — one primary CTA per page. Comparison/roundup articles (e.g. "Airalo vs Ubigi") that need more than one
affiliate link belong in `blog` as `.mdx` instead. **All seed content
ships with placeholder affiliate URLs** (containing `REPLACE_WITH_AFFILIATE_LINK`) — the site will render a
visible red warning under any affiliate button until you replace them with real links. Search the repo for
`REPLACE_WITH_AFFILIATE_LINK` to find every one that needs updating.

To add a new article, copy an existing `.md` file in the relevant collection folder and fill in the
frontmatter — no code changes needed.

## Before you publish

1. **Sign up for affiliate programs** and generate real deep links, then replace every
   `REPLACE_WITH_AFFILIATE_LINK` placeholder:
   - Booking.com Partner Hub — https://partner.booking.com
   - Agoda Affiliate (via Agoda / CJ / Partnerize, depending on region) — https://partners.agoda.com
   - Klook Affiliate — https://affiliate.klook.com
   - Viator / TripAdvisor Affiliate — https://www.viator.com/affiliations
   - GetYourGuide Partner — https://partner.getyourguide.com
   - Airalo Affiliate (via Impact) — https://www.airalo.com/affiliate
   - Sakura Mobile Affiliate — https://www.sakuramobile.jp/about-us/affiliate-program/
   - JRPass.com / Japan Experience Affiliate — https://www.japan-experience.com/affiliate-program

   See `japan-travel-media/research/02_affiliate_programs.md` for a full comparison (commission rates, cookie
   duration, approval difficulty) and a recommended sign-up priority order.
2. **Set your real domain** in `astro.config.mjs` (`site:`) and `public/robots.txt` (`Sitemap:`) — both
   currently point at a placeholder `example-kansai-guide.com`.
3. **Update contact details** — `CONTACT_EMAIL` in `src/pages/contact.astro` and `src/pages/privacy-policy.astro`
   is a placeholder.
4. **Have `/privacy-policy/` and `/affiliate-disclosure/` reviewed** — the shipped copy is a reasonable
   starting point, not legal advice. If you'll have EU/UK or California traffic, check GDPR/CCPA specifics
   with someone qualified.
5. **Add real photos.** Every hero currently uses a CSS gradient instead of an image, to avoid using
   unlicensed photos. Once you have your own or properly licensed images, add a `heroImage` field to the
   content schema and an `<Image>` in `ContentCard.astro` / `ArticleLayout.astro`.
6. **(Optional) Analytics.** Copy `.env.example` to `.env` and fill in `PUBLIC_GA_MEASUREMENT_ID` (from
   Google Analytics) and `PUBLIC_SEARCH_CONSOLE_VERIFICATION` (from Google Search Console) if you want them.
7. **Fact-check the seed content.** Prices, exact hours and pass costs change — every article that touches
   on these deliberately avoids hard numbers, but double-check before publishing anyway.

## Deployment

Any static host works. Vercel or Cloudflare Pages are the easiest for a git-based Astro project:

1. Push this repo to GitHub.
2. On Vercel: "Import Project" → select the repo → framework preset "Astro" is auto-detected → deploy.
   (Cloudflare Pages: build command `npm run build`, output directory `dist`.)
3. Set `PUBLIC_GA_MEASUREMENT_ID` / `PUBLIC_SEARCH_CONSOLE_VERIFICATION` as environment variables in the
   host's dashboard if you're using them.
4. Point your domain at the host, then update `site:` in `astro.config.mjs` to match and redeploy.

## Project structure

```
src/
  components/   Header, Footer, SEO, AffiliateButton, AffiliateDisclosureNote, ContentCard
  layouts/      BaseLayout (page shell), ArticleLayout (article hero + prose + disclosure)
  content/      All Markdown content, organized by collection
  pages/        Route definitions — index pages + [slug].astro per collection, plus static pages
  consts.ts     Site title, nav links, disclosure copy
public/
  robots.txt, favicon.svg
```
