# KFOOD 30-day search and revenue plan

## Baseline: 2026-08-03

- Search Console: 51 indexed pages, 21 not indexed. The last 28 days produced 250 impressions and 0 clicks. The last three months produced 2 clicks, 2,139 impressions, 0.1% CTR, and average position 54.1.
- The highest-impression recipe queries were `yukgaejang` (124), `galbitang` (68), `dolsot bibimbap` (66), `sundubu jjigae` (66), `haemultang` (36), and `godeungeo gui` (27).
- AdSense, last seven days: 95 page views, 8 ad impressions, 0 clicks, and $0.00. Policy Center reported no violation.
- GA4, last seven days: 63 `user_engagement` events and 15 50%-scroll events. The 151 active-user headline included 80 users from Singapore and 123 Direct sessions, so it is not treated as a count of monetizable readers.

These are operating baselines, not promises. Revenue follows qualified readers; it is not a useful daily content quota.

## Editorial rule

Every new or materially revised article must pass the local editorial bridge before publication. The sequence is problem, conclusion, criteria, evidence and limits, tradeoffs, and recommended action. No first-hand cooking, purchase, tasting, rating, nutrition, price, or timing claim is added without an owner note or a reliable source. Existing inherited copy is not described as tested until that record exists.

## Days 1–3: trust and search-result cleanup

- Align recipe page titles, H1s, descriptions, Recipe names, and recipe-archive ItemList names with plain dish intent.
- Remove unsupported publication-frequency and “tested” promises.
- Replace CSS-only featured images with crawlable `<img src>` elements and descriptive alt text.
- Add social image metadata and `x-default` hreflang to recipe archives.
- Publish the editorial method and verification limits on both About pages.
- Replace empty Stories-page fragment links with real reading paths.
- Run `python3 scripts/build_static_recipes.py`, `python3 scripts/content_quality_audit.py`, and `python3 scripts/verify_site.py`.

## Days 4–7: repair the first three high-opportunity recipes

- Select at most three pages from the audit, starting with high impressions and unsupported first-person claims.
- Prepare a source-backed brief in the editorial bridge before changing HTML.
- Preserve useful ingredients and instructions, remove invented personal scenes and unsupported cultural or health claims, and add troubleshooting that follows from the recipe method.
- Use the existing representative food image unless a better owner-supplied or newly commissioned image is available. Do not publish generic decorative art as a recipe result image.
- Update contextual internal links to the beginner guide and two genuinely related recipes.

## Week 2: build one strong topic cluster

- Treat `/recipes/` as the `korean recipes` hub and improve its introductory copy only from the questions visible in Search Console.
- Connect the hub, beginner guide, and the six priority recipes with concise descriptive anchors.
- Add no new article unless Search Console reveals a distinct question that none of the existing pages answers.
- Review Google Images discovery: HTML image elements, representative high-resolution images, filenames, alt text, and page context.

## Week 3: qualified-reader and ad diagnostics

- Compare `engaged_reader`, `user_engagement`, 50% scroll, country, and source. Exclude data-center-like Direct spikes from reader estimates.
- Verify that `engaged_reader` has started appearing after the 2026-08-01 deployment. If not, debug the event locally without opening the ad-supported live site in a JavaScript browser.
- Compare AdSense page views, ad requests or impressions, Active View, platform, and country. Do not add extra ad units merely to increase requests.
- Keep the manual responsive ad in a content-rich location. Change placement only if real readers scroll past it before rendering.

## Week 4: measure, consolidate, and decide the next month

- Compare 28-day Search Console clicks, impressions, CTR, and position against the baseline and record which updated URLs changed.
- Keep, revise, or roll back title and snippet changes based on query-level evidence.
- Update the next three flagged recipes; do not mass-publish.
- Review indexed versus non-indexed URLs by reason. Fix genuine canonical or duplicate issues, but do not force low-value aliases into the index.
- Compare AdSense and engaged-reader changes only for qualified traffic sources.

## Operating targets for day 30

- Search impressions: directional target of at least 375 over a comparable 28-day window.
- Search clicks: at least 3 genuine clicks, with CTR moving toward 0.5% or better.
- Priority-query average position: move from the 50s toward the mid-40s or better.
- Editorial debt: reduce unsupported first-person and promotional wording on at least 9 priority recipe pages.
- Analytics: observe stable `engaged_reader` events from non-data-center traffic before judging ad performance.

Targets guide decisions and are not revenue guarantees.

## Automation cadence

- Daily lightweight run: use `audit-manifest.json` and HTTP source checks only, run both local audit scripts, and report only failures or a newly detected regression. Never open the public site in a JavaScript browser for this routine.
- Monday weekly run: inspect Search Console, GA4, AdSense, and the qualified-reader split; send the existing Korean weekly email.
- Tuesday and Thursday editorial run: prepare or update no more than one priority-page brief per run. Publish only after the editorial bridge and site verifier pass.
- Month-end run: compare the 28-day baselines above, choose the next topic cluster, and reset the priority list.

## Primary guidance used

- Google Search Central, people-first content: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Google Search Central, recipe structured data: https://developers.google.com/search/docs/appearance/structured-data/recipe
- Google Search Central, image SEO: https://developers.google.com/search/docs/appearance/google-images
- Google Search Central, link best practices: https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- Google Search Central, title links: https://developers.google.com/search/docs/appearance/title-link
- Google Search Central, multilingual sites: https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites
- Google AdSense, ad placement: https://support.google.com/adsense/answer/1282097
- Google AdSense, viewability: https://support.google.com/adsense/answer/6219980
