# Build verification

- 45 automated unit/integration tests passed.
- Full baseline validation passed all 34 checks.
- Two full same-seed generations matched all 42 exported CSV/JSON/SQL hashes and row counts.
- Ten isolated labelled rule scenarios matched expected flags exactly (precision/recall 1.0 on this deterministic fixture, not real-world accuracy).
- Fifty employee paths sampled: see planner-metrics.json.
- HTTP smoke checks passed on a disposable database.
- Desktop 1440px and mobile 390px browser renders inspected: readable cards, controls, gap table and course sequence, no visible horizontal overflow in inspected regions. Screenshots show the full dataset. The lower lifecycle region was subsequently inspected with its action form expanded; see dashboard-lifecycle.png.
- No public repository, hosted application or assessment submission created. Candidate personal review remains pending.

- Baseline-linked anomaly stream: all seven source-parent bindings valid; exact five required invalid categories detected and both clean controls accepted. Separate truth and no planner mutation verified.
