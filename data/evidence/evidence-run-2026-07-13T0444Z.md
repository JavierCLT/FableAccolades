# Evidence Run: 2026-07-13T04:44Z

This bundle was generated from commit `3a3a935` with:

```bash
python -m backend.pipeline
```

Collection completed at 2026-07-13T04:49:49Z. The rebuilt database is also
committed separately at `data/processed/broker_index.db` so the dashboard can
open without another collection run.

## Contents

- `evidence-run-2026-07-13T0444Z.zip`
- 137 raw source snapshots from this collection run
- `data/processed/broker_index.db`
- `logs/pipeline.log`

Archive SHA-256:

`5D2B6FC75A588E8D5616CE42BB45CB9C6369688B9A94DB969A08D022E12D4D66`

## Results

- 552 evidence records across 26 sources
- 218 product facts
- 198 expert ratings
- 11,040 CFPB complaints analyzed
- 100 withdrawn expert claims excluded from scoring
- 11 remaining expert contradictions
- 176 dimension scores and 99 persona scores
- 168 broker evidence pages archived; 50 URLs failed
- Expert verification: 7 confirmed, 9 corrected, 60 unverified, 100 withdrawn,
  and 22 blocked

## Known Gaps

- Live Reddit collection was skipped because Reddit API credentials were not
  configured. Curated Reddit and Bogleheads themes remain in the database.
- Blocked and non-extractable expert claims remain at low confidence.
- Unavailable sources remain visible in the evidence ledger and do not silently
  contribute to scoring.
