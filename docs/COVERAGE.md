# First-build requirement coverage

This is an implementation coverage review, not a claim of employer acceptance.

| Area | Implementation / evidence | Status / caveat |
|---|---|---|
| End-to-end gap-to-learning workflow | core.py gaps/recommend/approve_plan/record_completion/reassess; local UI and API | Implemented, local synthetic prototype |
| Required entity model and keys | 11 core entities plus event, plan and career bridges; DATA_DICTIONARY.md and SQL DDL | Implemented; employee has one current role, not full role-change history |
| Parent-first generation / consistent IDs | generate() builds master then child records; foreign keys and immutable IDs | Implemented; fixed seed and zero-padded conventions |
| Full baseline volume | full-export/validation.json | Exactly 5,000 employees / 500 skills / 1,000 courses / 10,000 enrollments |
| Fixed seed / shared starter-full generator | generate(scale,seed), reproduce.py | Implemented; 42 matching normalized file hashes over two full generations |
| Course costs, capacity, availability, prerequisite chains | course/prerequisite records and planner checks | Implemented; two-level foundation/advanced chains, lifetime course capacity |
| Prerequisites / budget respected | ordered dependency bundles and transaction-safe approval | Implemented; plans project future prerequisite completion, actual completion separately enforces it |
| Immutable lifecycle records | enrollment_event, completion, reassessment, plan_event | Implemented for exposed actions; no general edit/cancel UI |
| Learning distinct from attendance/completion | only reassessment changes effective observed levels | Implemented and tested |
| Five required negative categories | scenario_inputs.json, independent ground_truth.json, detect(), evaluation.json | Implemented as a proposed event sidecar referencing real generated baseline IDs, with separate labels and five exact negative categories plus two clean boundary controls. Clean baseline is preserved. |
| Ground-truth isolation | labels absent from planner database and scenario input features | Implemented; detector receives inputs only |
| Validation and reconciliation | validation.json, 34 checks; 45 tests | PK/FK, enum, chronology, cycles, lifecycle, capacity/budget/cost joins covered; SQL constraints supplement validator |
| Measurable outputs | projected gap closure, cost/hours, fifty-plan sample, precision/recall on ten fixtures | Implemented; rule fixtures are not ML generalization evidence |
| CSV/JSON/SQL export + source manifest | full-export/, manifest.json | Implemented, all synthetic local provenance |
| Setup, assumptions, trade-offs and review | README, DATA_DICTIONARY, DECISIONS, WALKTHROUGH, START_ON_MAC | Implemented; Linux-tested, Mac instructions not machine-tested |
| Prompt history and AI disclosure | AI_USE.md | Partial by disclosure: project-facing prompts and development record only; complete raw export unavailable. No full-history compliance claim |
| Meaningful source evolution | local initial implementation commit, tests and fixes in development record | First review baseline; external PR flow not yet started |
| Dedicated public repository | Not created | Held pending user approval; mandatory before submission |
| Final portal repository link | Not submitted | Held pending candidate review and explicit final approval; portal allows one final send |
| Confidentiality and privacy | No actual problem statement, private source files, credentials or real employee data in bundle | Checked in authored source and packaging |

## Review decisions before final delivery
1. Candidate must personally run and understand the build.
2. Inspect the baseline-linked proposed anomaly stream and its separate ground truth; all seven cases and their source-parent references are validated.
3. Acknowledge the prompt-export limitation before representing the submission as compliant.
4. Approve public repository contents and then separately approve the one-time final portal submission.
