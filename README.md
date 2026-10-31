# Learning Path Lab

A local, reproducible workforce-learning planner using entirely synthetic data. It connects assessed skills, role targets, course prerequisites, availability, study time, capacity and department budgets. Completion and verified learning are separate events.

Start with `docs/FINAL_REVIEW.md` for a short candidate run-through and the remaining submission gates.

## Requirements
Python 3.10 or newer with SQLite support. No packages, cloud accounts, API keys or paid services. Tested here on Python 3.10.12/Linux. Costs are integer INR; skills use 0..5 proficiency. Dates are intentionally simulated as of 2026-10-22 for reproducibility.

For a Mac shortcut, see `docs/START_ON_MAC.md` or run `START_MAC.command` after unzipping. macOS itself has not been tested.

## Quick start
From this directory:

```sh
python -m learninglab generate --scale starter
python -m learninglab serve
```

Open **http://127.0.0.1:8765/**. On systems where Python is `python3`, substitute it. Windows users can use `py -3`. The server runs on loopback only. Stop with Ctrl-C. Generation refuses to overwrite an existing database unless `--force` is supplied; regeneration discards local changes.

A full generated dataset is included at `data/full.sqlite`, with CSV/JSON/SQL exports at `data/full-export/`. To run it:

```sh
python -m learninglab --db data/full.sqlite serve
```

## Generate and verify

```sh
python -m learninglab --db data/review.sqlite generate --scale full --out data/review-export
python -m learninglab --db data/review.sqlite validate
python -m learninglab --db data/review.sqlite recommend EMP-000001
python -m learninglab --db data/review.sqlite recommend EMP-000001 --target-role ROL-000002 --hours 80 --period-end 2027-03-31
python -m unittest discover -s tests -v
python scripts/reproduce.py
```

Full scale: 5,000 employees, 500 skills, 1,000 courses, 10,000 historical enrollments. Starter scale: 100 employees, 30 skills, 60 courses, 200 enrollments. Both use the same generation functions and seed (default 20261022). `--seed` changes the population. Generation writes a SQLite database and individual CSV/JSON tables, executable SQL seed, manifest, validation summary, baseline-linked anomaly stream and separate labels, isolated scenario inputs and ground truth, and a rule-evaluation report. SQL import: `sqlite3 new.sqlite < data/full-export/seed.sql` if the SQLite CLI is installed; the application itself needs no CLI installation.

## Inspect the result
- `learninglab/core.py`: schema, generator, planner, lifecycle mutations, validator, isolated scenario detector and exports.
- `learninglab/web.py` and `index.html`: local API and responsive dashboard.
- `docs/DATA_DICTIONARY.md`: every field, type, optionality, key, unit and validation constraint.
- `docs/COVERAGE.md`: requirement-by-requirement coverage and remaining review gates.
- `docs/DECISIONS.md`: relationships, assumptions, decision rules, synthetic distributions and limitations.
- `docs/AI_USE.md`: AI contribution, project-facing prompt record and raw-export limitation.
- `docs/WALKTHROUGH.md`: personal-review guide.
- `artifacts/`: actual test, full-validation, evaluation, reproducibility and visual evidence.

The dashboard searches synthetic employees, compares current/career-role targets, explains gaps, shows a feasible ordered path and exclusion reasons, and exposes enrollment/completion/reassessment histories. Local approval reserves the recommended enrollments under a transaction; completion and reassessment are explicit subsequent actions. These are synthetic demonstration records, not a submission or real HR authorization.

## Metrics and caveats
Projected gap closure is (initial deficit minus projected deficit) / initial deficit, with already-at-target reported as 100%. It is not measured learning. Scenario precision/recall compare deterministic rule flags to isolated ground truth, not ML predictions. Completed records without reassessment do not silently acquire skills.

The prototype uses a deterministic greedy bundle heuristic, not an optimal scheduler. It has no production auth, per-session capacity, role-change history or real skills taxonomy. Read `docs/DECISIONS.md` before relying on outputs. The candidate has not yet personally reviewed this AI-assisted build. This repository is the approved public review package. The assessment has not been submitted, and the candidate's own run/review remains pending.

## Data provenance and privacy
All generated records are invented locally from documented rules. No external dataset was downloaded, no real employee data is present, and no proprietary problem statement is included. The manifest records seed, scale, units, source and export hashes. No third-party runtime dependencies need attribution. This code is provided for candidate review; no license grant for unrelated redistribution is asserted.

## Baseline-linked anomaly audit
`data/full-export/anomaly_stream.json` contains seven proposed records whose parent IDs resolve to the full clean database. The five invalid records cover unmet prerequisites, over-budget reservation, duplicate completion, unsupported skill improvement without reassessment, and unavailable courses. Two valid controls test exact-budget acceptance and honest unchanged proficiency. `anomaly_ground_truth.json` is separate; `anomaly_validation.json` records independent rule outputs and parent checks. No labels or invalid proposed records enter planner features.
