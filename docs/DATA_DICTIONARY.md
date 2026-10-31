# Data dictionary

All IDs are immutable text keys. SQLite foreign-key enforcement is enabled on every application connection. Dates are ISO 8601 calendar dates; proficiency is ordinal 0..5, costs/budgets are whole INR, hours are study hours and capacity is seats. Names identify invented records only.

Required means NOT NULL or part of a primary key. Foreign-key columns additionally declare NOT NULL. No optional key participates in a join.

## role

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| name | TEXT | yes | - | see table SQL constraints |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE role(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
```

## skill

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| name | TEXT | yes | - | see table SQL constraints |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE skill(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
```

## employee

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| name | TEXT | yes | - | see table SQL constraints |
| role_id | TEXT | yes |  FK role.id | see table SQL constraints |
| department | TEXT | yes | - | see table SQL constraints |
| effective_from | TEXT | yes | - | ISO date |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE employee(id TEXT PRIMARY KEY, name TEXT NOT NULL, role_id TEXT NOT NULL REFERENCES role(id), department TEXT NOT NULL, effective_from TEXT NOT NULL);
```

## role_skill_target

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| role_id | TEXT | yes | PK 1 FK role.id | see table SQL constraints |
| skill_id | TEXT | yes | PK 2 FK skill.id | see table SQL constraints |
| target | INTEGER | yes | - | ordinal 1..5 |
| effective_from | TEXT | yes | - | ISO date |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE role_skill_target(role_id TEXT NOT NULL REFERENCES role(id),skill_id TEXT NOT NULL REFERENCES skill(id),target INTEGER NOT NULL CHECK(target BETWEEN 1 AND 5),effective_from TEXT NOT NULL,PRIMARY KEY(role_id,skill_id));
```

## employee_skill

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| employee_id | TEXT | yes | PK 1 FK employee.id | see table SQL constraints |
| skill_id | TEXT | yes | PK 2 FK skill.id | see table SQL constraints |
| level | INTEGER | yes | - | ordinal 0..5 |
| assessed_on | TEXT | yes | - | ISO date |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE employee_skill(employee_id TEXT NOT NULL REFERENCES employee(id),skill_id TEXT NOT NULL REFERENCES skill(id),level INTEGER NOT NULL CHECK(level BETWEEN 0 AND 5),assessed_on TEXT NOT NULL,PRIMARY KEY(employee_id,skill_id));
```

## course

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| name | TEXT | yes | - | see table SQL constraints |
| cost | INTEGER | yes | - | whole INR; non-negative |
| hours | INTEGER | yes | - | positive study hours |
| capacity | INTEGER | yes | - | positive seats |
| available_from | TEXT | yes | - | ISO date |
| available_to | TEXT | yes | - | ISO date |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE course(id TEXT PRIMARY KEY,name TEXT NOT NULL,cost INTEGER NOT NULL CHECK(cost>=0),hours INTEGER NOT NULL CHECK(hours>0),capacity INTEGER NOT NULL CHECK(capacity>0),available_from TEXT NOT NULL,available_to TEXT NOT NULL,CHECK(available_to>=available_from));
```

## course_skill

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| course_id | TEXT | yes | PK 1 FK course.id | see table SQL constraints |
| skill_id | TEXT | yes | PK 2 FK skill.id | see table SQL constraints |
| exit_level | INTEGER | yes | - | ordinal 1..5 |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE course_skill(course_id TEXT NOT NULL REFERENCES course(id),skill_id TEXT NOT NULL REFERENCES skill(id),exit_level INTEGER NOT NULL CHECK(exit_level BETWEEN 1 AND 5),PRIMARY KEY(course_id,skill_id));
```

## prerequisite

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| course_id | TEXT | yes | PK 1 FK course.id | see table SQL constraints |
| required_course_id | TEXT | yes | PK 2 FK course.id | see table SQL constraints |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE prerequisite(course_id TEXT NOT NULL REFERENCES course(id),required_course_id TEXT NOT NULL REFERENCES course(id),PRIMARY KEY(course_id,required_course_id),CHECK(course_id!=required_course_id));
```

## budget

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| department | TEXT | yes | - | see table SQL constraints |
| year | INTEGER | yes | - | 2026 cohort |
| amount | INTEGER | yes | - | whole INR; non-negative |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE budget(id TEXT PRIMARY KEY,department TEXT NOT NULL,year INTEGER NOT NULL,amount INTEGER NOT NULL CHECK(amount>=0),UNIQUE(department,year));
```

## enrollment

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| employee_id | TEXT | yes |  FK employee.id | see table SQL constraints |
| course_id | TEXT | yes |  FK course.id | see table SQL constraints |
| budget_id | TEXT | yes |  FK budget.id | see table SQL constraints |
| cost | INTEGER | yes | - | whole INR; non-negative |
| enrolled_on | TEXT | yes | - | ISO date |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE enrollment(id TEXT PRIMARY KEY,employee_id TEXT NOT NULL REFERENCES employee(id),course_id TEXT NOT NULL REFERENCES course(id),budget_id TEXT NOT NULL REFERENCES budget(id),cost INTEGER NOT NULL CHECK(cost>=0),enrolled_on TEXT NOT NULL,UNIQUE(employee_id,course_id));
```

## enrollment_event

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| enrollment_id | TEXT | yes |  FK enrollment.id | see table SQL constraints |
| state | TEXT | yes | - | see table SQL constraints |
| occurred_on | TEXT | yes | - | ISO date |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE enrollment_event(id TEXT PRIMARY KEY,enrollment_id TEXT NOT NULL REFERENCES enrollment(id),state TEXT NOT NULL CHECK(state IN ('enrolled','completed','cancelled')),occurred_on TEXT NOT NULL);
```

## completion

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| enrollment_id | TEXT | yes |  FK enrollment.id | see table SQL constraints |
| completed_on | TEXT | yes | - | ISO date |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE completion(id TEXT PRIMARY KEY,enrollment_id TEXT NOT NULL UNIQUE REFERENCES enrollment(id),completed_on TEXT NOT NULL);
```

## reassessment

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| completion_id | TEXT | yes |  FK completion.id | see table SQL constraints |
| employee_id | TEXT | yes |  FK employee.id | see table SQL constraints |
| skill_id | TEXT | yes |  FK skill.id | see table SQL constraints |
| level | INTEGER | yes | - | ordinal 0..5 |
| assessed_on | TEXT | yes | - | ISO date |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE reassessment(id TEXT PRIMARY KEY,completion_id TEXT NOT NULL REFERENCES completion(id),employee_id TEXT NOT NULL REFERENCES employee(id),skill_id TEXT NOT NULL REFERENCES skill(id),level INTEGER NOT NULL CHECK(level BETWEEN 0 AND 5),assessed_on TEXT NOT NULL,UNIQUE(completion_id,skill_id));
```

## career_path

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| from_role_id | TEXT | yes |  FK role.id | see table SQL constraints |
| to_role_id | TEXT | yes |  FK role.id | see table SQL constraints |
| name | TEXT | yes | - | see table SQL constraints |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE career_path(id TEXT PRIMARY KEY,from_role_id TEXT NOT NULL REFERENCES role(id),to_role_id TEXT NOT NULL REFERENCES role(id),name TEXT NOT NULL);
```

## learning_plan

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| employee_id | TEXT | yes |  FK employee.id | see table SQL constraints |
| target_role_id | TEXT | yes |  FK role.id | see table SQL constraints |
| created_on | TEXT | yes | - | ISO date |
| period_end | TEXT | yes | - | ISO date |
| budget_remaining | INTEGER | yes | - | whole INR; non-negative |
| hour_limit | INTEGER | yes | - | positive study hours |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE learning_plan(id TEXT PRIMARY KEY,employee_id TEXT NOT NULL REFERENCES employee(id),target_role_id TEXT NOT NULL REFERENCES role(id),created_on TEXT NOT NULL,period_end TEXT NOT NULL,budget_remaining INTEGER NOT NULL,hour_limit INTEGER NOT NULL);
```

## plan_item

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| plan_id | TEXT | yes | PK 1 FK learning_plan.id | see table SQL constraints |
| course_id | TEXT | yes | PK 2 FK course.id | see table SQL constraints |
| position | INTEGER | yes | - | 1-based sequence |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE plan_item(plan_id TEXT NOT NULL REFERENCES learning_plan(id),course_id TEXT NOT NULL REFERENCES course(id),position INTEGER NOT NULL,PRIMARY KEY(plan_id,course_id),UNIQUE(plan_id,position));
```

## plan_event

| Field | Type | Required | Key / relationship | Units / rules |
|---|---|---|---|---|
| id | TEXT | yes | PK 1 | immutable identifier |
| plan_id | TEXT | yes |  FK learning_plan.id | see table SQL constraints |
| state | TEXT | yes | - | see table SQL constraints |
| occurred_on | TEXT | yes | - | ISO date |
| reason | TEXT | yes | - | see table SQL constraints |

Exact uniqueness, enums and check constraints:

```sql
CREATE TABLE plan_event(id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES learning_plan(id),state TEXT NOT NULL CHECK(state IN ('recommended','approved','rejected')),occurred_on TEXT NOT NULL,reason TEXT NOT NULL);
```

## Cardinality and temporal semantics

Role 1:N Employee; Role N:M Skill through RoleSkillTarget; Employee N:M Skill through EmployeeSkill. Course N:M Skill through CourseSkill. Course N:M Course through Prerequisite. Department budget 1:N Enrollment; Employee and Course each 1:N Enrollment, with a unique employee/course pair. Enrollment 1:N EnrollmentEvent and 0:1 Completion. Completion 0:N Reassessment. Role N:M Role through CareerPath. Employee 1:N LearningPlan; LearningPlan 1:N PlanItem and PlanEvent.

All effective dates and event timestamps are calendar dates, not wall-clock instants. Initial proficiency is an assessed snapshot; subsequent reassessments are immutable and supersede it in date/ID order. Enrollment lifecycles are enrolled -> completed or cancelled; completion -> reassessment is optional, never assumed. Plans preserve recommended -> approved records. Runtime actions prevent duplicate completion and validate dates, prerequisite completion and skill ownership. Cross-row joins and arithmetic are checked in validation.json.
