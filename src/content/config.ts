import { defineCollection, z } from 'astro:content';

// Shared fields used by every content type. `heroGradient` is a pair of Tailwind
// color stops used for a CSS gradient hero instead of a real photo — swap in a
// real image later by adding a `heroImage` field once you have licensed photos.
const base = {
  title: z.string(),
  description: z.string(),
  pubDate: z.coerce.date(),
  updatedDate: z.coerce.date().optional(),
  heroGradient: z.tuple([z.string(), z.string()]).default(['#1a1a3d', '#d6336c']),
  draft: z.boolean().default(false),
};

const guides = defineCollection({
  type: 'content',
  schema: z.object({
    ...base,
    region: z.string(), // e.g. "Kyoto"
    highlights: z.array(z.string()).default([]),
  }),
});

const itineraries = defineCollection({
  type: 'content',
  schema: z.object({
    ...base,
    days: z.number().int().positive(),
    region: z.string(),
    bestFor: z.array(z.string()).default([]),
  }),
});

// `affiliateUrl` is a placeholder until you generate real deep links in each
// network's partner dashboard. Never publish with the placeholder still in place.
const activities = defineCollection({
  type: 'content',
  schema: z.object({
    ...base,
    location: z.string(),
    category: z.string(), // e.g. "Day Trip", "Food Tour", "Culture"
    provider: z.enum(['klook', 'viator', 'getyourguide']),
    affiliateUrl: z.string(),
    priceHint: z.string().optional(), // keep vague, e.g. "Budget-friendly" — do not hardcode exact prices
  }),
});

const hotels = defineCollection({
  type: 'content',
  schema: z.object({
    ...base,
    area: z.string(), // e.g. "Kyoto Station"
    provider: z.enum(['booking', 'agoda']),
    affiliateUrl: z.string(),
    priceHint: z.string().optional(),
  }),
});

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    ...base,
    tags: z.array(z.string()).default([]),
  }),
});

// Japan eSIM / connectivity reviews and recommendations. Comparison articles
// ("Airalo vs Ubigi", "Best eSIM for Japan" roundups) that link to multiple
// providers inline belong in `blog` (as .mdx) instead — this collection is for
// single-provider recommendation/review pages with one primary CTA.
const esim = defineCollection({
  type: 'content',
  schema: z.object({
    ...base,
    useCase: z.string(), // e.g. "7-Day Trips", "Unlimited Data", "Short Layovers"
    provider: z.enum(['airalo', 'ubigi', 'holafly', 'sakuramobile', 'japanwireless']),
    affiliateUrl: z.string(),
    priceHint: z.string().optional(),
  }),
});

// JR Pass, IC cards, airport transfers, Shinkansen booking, rental cars.
// Same single-provider-CTA model as `esim`/`activities`/`hotels`.
const transportation = defineCollection({
  type: 'content',
  schema: z.object({
    ...base,
    transportType: z.string(), // e.g. "Airport Transfer", "JR Pass", "IC Card"
    provider: z.enum(['klook', 'jrpass', 'japanexperience', 'discovercars']),
    affiliateUrl: z.string(),
    priceHint: z.string().optional(),
  }),
});

export const collections = { guides, itineraries, activities, hotels, blog, esim, transportation };
