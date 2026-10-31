# Baseline analysis (DASH-247)

Read-only queries behind the choice of baseline and "outside normal" rule. Each file is
self-contained and runs against the seed through the read-only role:

```bash
./scripts/sql-ro.sh "$(cat docs/analysis/<file>.sql)"
```

Shared definitions (identical in every file): events deduplicated on all columns except `id`;
Monday–Sunday weeks in the account's local timezone; complete weeks 2026-02-02 .. 2026-07-20;
weeks with no events count as 0; account totals only for multi-location accounts.

Methods compared:

- **A**: median of prior 8 weeks ± 3 × 1.4826 × MAD (Hampel).
- **B**: 10th–90th percentile of prior 12 weeks.
- **C**: Poisson 0.5%–99.5% range around the median of prior N weeks (N = 8 unless stated).

| File | Question | Result |
|---|---|---|
| `01-dispersion.sql` | Are weekly counts Poisson-like? | variance/mean median 0.97 (range 0.37–1.67, 4 of 69 locations > 1.5) |
| `02-method-series.sql` | How do A/B/C behave around the spike and on low-volume series? | all three keep the baseline stable after the spike; A's band is unstable on small counts |
| `03-min-detectable-change.sql` | Smallest drop / rise C flags, per baseline size | baseline 8: −88% / +113%; 30: −47% / +53%; 70: −31% / +33%; LOW impossible at ≤ 5 |
| `04a-halved-week-examples.sql` | Halve week 2026-07-20 on 5 series: who catches it? | C catches it only on account totals (56, 72.5); misses locations at 5–10 |
| `04b-detection-vs-false-alarm.sql` | Misses vs false alarms by baseline size, A/B/C | see table below |
| `05-window-sensitivity.sql` | C with 6 / 8 / 12 weeks, 99% vs 95% | window length barely matters; the range width does |

`04b` (weeks 2026-04-27 .. 2026-07-20, account 6 excluded; fa = normal week flagged,
det = halved week flagged LOW):

| baseline | loc / acct weeks | A fa / det | B fa / det | C fa / det |
|---|---|---|---|---|
| ≤ 5 | 76 / 0 | 4% / 4% | 30% / 39% | 0% / 0% |
| 5–10 | 592 / 0 | 8% / 14% | 34% / 65% | 0% / 2% |
| 10–20 | 34 / 75 | 6% / 30% | 35% / 90% | 1% / 10% |
| 20–40 | 0 / 81 | 6% / 33% | 35% / 100% | 2% / 59% |
| > 40 | 0 / 26 | 0% / 50% | 23% / 100% | 0% / 92% |

## Known limitations

- **Dispersion is measured on synthetic data.** C assumes Poisson noise (variance ≈ mean),
  which holds on this seed (`01`). Real activity is usually more dispersed (campaigns, weather,
  holidays). There, C's range is too narrow and it over-fires. Nothing is built for this.
  **Next step:** on production data, measure variance/mean per series. If it's materially
  above 1, widen the range using a dispersion estimate from each series' own history
  (quasi-Poisson or negative binomial).
- **Single-week location verdicts have little power.** In this seed every location's baseline is 4–11
  events/week. No method in `04b` detects a halved week there without also flagging a large share of normal
  weeks. This is a property of the volume, not of the method.
- "False alarm" assumes the seed is flat apart from the account 6 spike. Real changes, if any,
  are counted as false alarms.
