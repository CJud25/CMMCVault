# Survival Guide — source and render pipeline

[`../CMMC_Level_2_Survival_Guide.pdf`](../CMMC_Level_2_Survival_Guide.pdf) is
generated from `survival-guide.html` by `render.mjs`, which prints the HTML to PDF
with Playwright's bundled Chromium.

To regenerate after an edit (requires Node.js):

```bash
cd docs/guide-src
npm install playwright@1.61.1
npx playwright install chromium   # first time only
node render.mjs
```

The PDF is written next to the HTML; move it up one level to `docs/` to replace the
published copy.

The guide's control tables — all 110 point values and POA&M-eligibility flags — are
asserted against the app's ruleset (`data/controls.json`,
`data/poam_eligibility.json`) by `tests/test_guide_consistency.py`, so an edit that
drifts from the app fails the build.
