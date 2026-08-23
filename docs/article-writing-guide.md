# Article writing guide (STEP7 template)

For every new article, follow the 12-step process from `japan-travel-media/00_handover.md` section 8:
search intent → competitor check → primary source check → official site check → confirm affiliate program →
outline → AI draft → human fact-check → add comparison/original info → SEO polish → publish → measure in
Search Console.

## Which collection does this keyword belong in?

| Keyword type | Collection | Example |
|---|---|---|
| Single-provider recommendation/review, one clear CTA | `esim` / `hotels` / `activities` / `transportation` | "Best Japan eSIM for 7-Day Trips" |
| Comparison ("X vs Y"), roundup ("best of"), or informational piece touching 2+ providers | `blog` (as `.mdx` if it needs more than one `<AffiliateButton>`) | "Airalo vs Ubigi Japan" |
| City/region overview | `guides` | "Tokyo" |
| Multi-day sample route | `itineraries` | "5-Day Tokyo Itinerary" |

## Frontmatter checklist

Every collection shares: `title`, `description`, `pubDate` (`YYYY-MM-DD`), optional `updatedDate`,
`heroGradient` (two hex colors), `draft` (defaults false).

CTA collections (`esim`, `hotels`, `activities`, `transportation`) additionally need `provider` (must match an
enum value in `src/content/config.ts` — add a new one there + a label in `src/components/AffiliateButton.astro`
if it's a genuinely new provider), `affiliateUrl` (use `REPLACE_WITH_AFFILIATE_LINK` until a real deep link
exists), and an optional `priceHint` (a *qualitative* hint — "budget-friendly", "priced by data allowance" —
never a specific number).

## Writing rules (do not skip)

- **No hardcoded prices, exact hours, or exact fees.** These change. Say what the pricing model is (e.g. "priced
  per vehicle, not per person") rather than a number, and tell the reader to check the current listing.
- **No invented statistics, reviews, or personal experience.** If you don't have a verified source for a claim,
  either cut the claim or phrase it as general guidance instead of a specific fact.
- **Give a real recommendation, not a listicle.** Pick a primary pick and explain the reasoning (who it's for,
  what trade-off it makes), then mention 1-2 alternatives with the specific situation where they'd be better —
  this is what differentiates the site from thin AI-generated roundups per section 15's ban on "無検証大量公開".
- **Structure that has worked in this repo's seed content:** short intro framing the real decision → the factor
  that actually matters (data amount / area / group size / etc.) → primary recommendation with reasoning →
  named alternatives with the specific case they fit → common mistakes → one-paragraph bottom line.
- Every CTA collection page renders the `<AffiliateButton>` twice automatically (top and bottom of the article)
  — don't add extra manual CTAs in the body.
- Before setting `draft: false` (or removing a `REPLACE_WITH_AFFILIATE_LINK`), a human must have done the
  fact-check + primary-source-check steps from the 12-step process. Leave a placeholder link rather than
  guessing a real one.

## Reference

- Keyword list + priority tiers: `japan-travel-media/research/03_keywords.md`
- Affiliate program details + which provider to recommend per category: `japan-travel-media/research/02_affiliate_programs.md`
- Market/competitor context: `japan-travel-media/research/01_market_and_country_analysis.md`
