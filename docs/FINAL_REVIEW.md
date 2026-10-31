# Final candidate review checklist

Status: approved public review package. Not submitted. Candidate personal run and review remain pending.

## Fast start

1. Unzip the download. On a Mac with Python 3.10+, follow START_ON_MAC.md. This build was tested on Linux, not a Mac.
2. From the project folder run:

```sh
python3 -m learninglab --db data/full.sqlite serve
```

3. Open http://127.0.0.1:8765/ . Stop the server with Control-C. No pip packages or API keys are needed.

## What to demonstrate

- Select EMP-000001 and explain the skill gaps, ordered prerequisites and remaining budget. The included dataset gives a five-course path costing INR 24,000 over 76 study hours, with INR 6,000 left from INR 30,000 available.
- Explain why the displayed gap closure is projected, not measured learning.
- Inspect enrollment, completion and reassessment histories. Explain why completion alone cannot change proficiency.
- Reduce the study-hour limit to 1 and rebuild the recommendation. No course fits the current minimum course duration, so the result should show no feasible path rather than overspend or violate prerequisites.
- Inspect separate baseline-linked anomaly inputs and labels. Explain each invalid proposed record and why clean controls are accepted.
- Use a disposable copy of the database if experimenting with local approval or lifecycle actions. Those buttons modify the local database; they do not submit an assessment.

## Verify from the command line

Use `python` instead of `python3` if that is the Python 3.10+ executable on your machine.

```sh
python3 -m learninglab --db data/full.sqlite validate
python3 -m unittest discover -s tests -v
python3 scripts/reproduce.py
```

The delivered evidence records 45 passing tests, 34 passing full-data checks and 42 identical export checksums across two same-seed generations. These are checks on this synthetic prototype, not proof of production readiness or a hiring outcome. Re-run them yourself before claiming personal verification.

## Before making a public repository

- Read README.md, COVERAGE.md, DECISIONS.md and AI_USE.md. Confirm the limitations and AI contribution are described honestly.
- Review the exact files being published. Do not add the confidential assessment statement, private messages, credentials, raw session material or personal data.
- Use a new dedicated public repository. Preserve truthful version history; do not fabricate prior commits or claim the commit listing is a substitute for actual repository history.
- Verify the repository opens while signed out. Keep it available and editable through the assessment deadline.
- The portal accepts one final submission. Check the exact URL and obtain final approval before sending it.

## Pending, not certified

Candidate local run, code understanding, personal final-content review and final portal submission are still pending. The complete raw AI prompt export is unavailable and that limitation is disclosed. A hosted demo and production login system are not added merely for appearance.
