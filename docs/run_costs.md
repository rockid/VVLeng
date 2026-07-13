# Apify Run Costs

One line per live collection run, pulled from the Apify console by the operator.
Actor: `harvestapi/linkedin-post-search` — paid per event (per post), not per
platform usage.

| Date | Keywords | maxPosts | Posts billed | Cost | Notes |
|---|---|---|---|---|---|
| 2026-07-05 | 48 | 35 | 1624 | $3.249 | $3.248 posts + $0.001 one 0-result query + $0.00005 actor start. First run at maxPosts=35 (cut from 50 after top-N analysis); June-22 run at 50 collected 2301 posts. |
| 2026-07-13 | 48 | 35 | 1646 | $3.29205 | $3.292 posts (1646 x $0.002) + $0.00005 actor start, no 0-result queries. Pulled programmatically via `GET /v2/actor-runs/{run_id}` (`usageTotalUsd`) rather than the console. First run on the reworked keyword set (dropped "NOT thrilled" suffix, cut 6 low-yield keywords, added 6 lookalikes). All 48 queries returned posts; only "peer-to-peer engagement" (unchanged, not part of this edit) came back near-empty (1/35) - candidate for the next culling round. |
