# Design and review notes

## Architecture
Python 3.10+ standard library only. SQLite holds relational data and append-only lifecycle records. A small loopback HTTP server exposes the planner and local demo actions. There is no model inference, network dependency, secret or external data source.

Master data is generated first, then dependent records. IDs are deterministic and immutable. Course-skill and role-skill bridges represent many-to-many relationships. Prerequisites reference courses; a course can require several courses. Each employee has one current role and department. Career-path records connect source and target roles. Plans reference employees and target roles and preserve their budget/hour assumptions. Plan items retain sequence. Events record recommendation and approval separately.

## Planning rules
- Proficiency is ordinal 0..5. Targets are 1..5. A gap is max(target - latest assessed level, 0).
- The latest dated reassessment supersedes the initial assessment, even when proficiency falls. Completion alone never increments skill.
- A prerequisite is satisfied by prior completion or by an earlier course in the proposed sequence. Approval reserves future courses in that sequence; it does not certify prerequisite completion. Recording actual completion requires already-completed prerequisites.
- Recommendations exclude active duplicate enrollments, completed courses, unavailable courses and exhausted capacity. Capacity is conservatively lifetime course capacity in this demo, not per session.
- Prerequisite bundles are scheduled sequentially at eight study hours/week. Waiting for availability is carried across bundles. Finish must fit both course availability and planning end.
- Department budgets are in whole INR, per 2026 cohort. All non-cancelled enrollments reserve their recorded costs. Completed seats/costs remain consumed. Recommendations are advisory; approval recomputes under a SQLite immediate transaction before reserving funds and seats.
- The greedy objective is marginal target-gap gain / (study hours + cost/100 + 1). Tie breaking is deterministic. This favors useful, low-burden bundles, but is not globally optimal knapsack scheduling. A plan may leave gaps even when another combination could do better.
- Course exit levels are expected potential, never evidence of actual learning. Displayed gap closure is projected. Real outcomes require reassessment.

## Synthetic distributions and labels
Employees span 25 role profiles and five departments at full scale. Initial levels are weighted toward 2-3, not uniform. Each skill has foundation/advanced courses; advanced courses depend on foundation. Costs and durations use discrete plausible course bands, including free courses. Most historical enrollments complete, and a separate fraction receive reassessment. Reassessment can fall short of a course's advertised exit level.

Budget allocations derive from historical enrollment spend plus controlled headroom. Capacity derives from historical seat use plus spare seats. Those policies guarantee an internally valid baseline and are stated assumptions, not observed employer statistics.

The five negative scenario categories, controls and one multi-issue case are generated in a separate self-contained scenario input file. In addition, anomaly_stream.json injects proposed transaction/event anomalies tied to actual generated employee/course/enrollment/completion/skill/budget IDs. anomaly_ground_truth.json separately labels those records. This sidecar includes exactly the five required failures plus exact-budget and no-false-learning-claim controls. It audits invalid proposed records before they can mutate the clean database. `ground_truth.json` records expected decisions independently of the detector's execution. Neither labels nor scenario inputs are used by the learning-path planner. The baseline database remains clean: deliberate anomalies are isolated rather than hidden in unrelated rows. The additional baseline-linked stream closes the coverage gap from disconnected toy fixtures, while retaining safe baseline integrity. Neither evaluation demonstrates a model generalizing to unseen corruption. Precision/recall are deterministic rule-check metrics, not machine-learning accuracy.

## Limitations and next steps
- Human-readable synthetic role and skill-family/topic names improve inspection, but the role mappings are invented demonstrations, not a validated HR ontology. A real rollout needs validated mappings and calibrated course outcomes.
- Static 2026-10-22 simulation date makes regeneration deterministic; this is not a live HR calendar. Initial competency rows are dated snapshots; reassessments are immutable event rows. No role-change history is modeled.
- Course completion and reassessment actions are separate API/UI steps. Duplicate completion and duplicate same-completion skill measurement are rejected rather than overwritten.
- Cancellation is represented in schema and budget/capacity calculations and tested, but no cancellation UI is supplied. Event history is not a general editable audit log.
- No employee/manager/HR authentication, role-based access, SSO or multi-tenant isolation. The server binds 127.0.0.1 only. Do not expose it on a network with real data.
- Standard-library HTTP serving and per-request SQLite connections suit local review, not production deployment. API approval is transaction-safe; this is not a distributed reservation service.
- One planner request concerns one employee and shares a department budget; concurrent approvals are serialized, but there is no cross-employee fair allocation optimizer.
- Data dictionary captures schema constraints; cross-record rules additionally live in validation and business functions. SQL alone does not enforce every temporal/business invariant.

## Personal review status
This implementation was AI-assisted. The candidate has not yet personally reviewed, run or explained it. No statement in this bundle claims otherwise. Before submission, the candidate should run it, inspect decisions, understand the dependency logic and budget transactions, and correct anything they cannot defend.
