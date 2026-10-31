# Adversarial review

- Compared the implementation against the exact required workflow, data volumes, IDs, source provenance, separate labels and five negative scenarios. Baseline-linked anomaly sidecar now covers each required category with valid source IDs, plus two valid boundary controls.
- Independent validation catches deliberately corrupted completion chronology and cost/budget records; it is not merely comparing generator counts to expected constants.
- A trigger-induced failure after plan/enrollment inserts proves transaction rollback leaves no partial plan or reservation.
- Three simultaneous approval clients use separate SQLite connections; serialized write transactions preserve budget and capacity invariants. Post-competition validation passes.
- Tests cover prerequisite ordering/cycles, zero budget, exhausted capacity, unavailable dates, duplicate completion, invalid targets/dates/hour limits, unsupported reassessment and absent parents.
- Same-seed full exports match all 42 checksums and row counts. Different seeds change data. SQL seed round-trip succeeds.
- Labels are in separate artifacts, not planner inputs or database tables; anomaly evaluation does not mutate the baseline.
- Reassessments may lower proficiency; attendance/completion never implies learning. Projected course dates and assumed before/after outcomes now expose plan reasoning.
- Local screenshots show readable desktop/mobile paths and lower lifecycle controls. Local HTTP smoke checks exercise approval and errors.
- A clean-unzip test regenerates starter data, validates it, computes a plan and runs all tests without third-party dependencies.
- Repository hygiene excludes secrets, raw private assessment text, compiled caches and environment files. No external datasets or account details included. Public repository not yet created.

Remaining honest limits: greedy not globally optimal; synthetic taxonomy is illustrative; fixed simulation clock; lifetime rather than per-session capacity; local-only unauthenticated server; unavailable complete raw prompt export; candidate personal review not yet verified. No shortlist or employer acceptance guarantee.
