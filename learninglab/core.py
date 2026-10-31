import csv
import hashlib
import json
import random
import sqlite3
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

AS_OF = '2026-10-22'
SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE role(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE skill(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE employee(id TEXT PRIMARY KEY, name TEXT NOT NULL, role_id TEXT NOT NULL REFERENCES role(id), department TEXT NOT NULL, effective_from TEXT NOT NULL);
CREATE TABLE role_skill_target(role_id TEXT NOT NULL REFERENCES role(id),skill_id TEXT NOT NULL REFERENCES skill(id),target INTEGER NOT NULL CHECK(target BETWEEN 1 AND 5),effective_from TEXT NOT NULL,PRIMARY KEY(role_id,skill_id));
CREATE TABLE employee_skill(employee_id TEXT NOT NULL REFERENCES employee(id),skill_id TEXT NOT NULL REFERENCES skill(id),level INTEGER NOT NULL CHECK(level BETWEEN 0 AND 5),assessed_on TEXT NOT NULL,PRIMARY KEY(employee_id,skill_id));
CREATE TABLE course(id TEXT PRIMARY KEY,name TEXT NOT NULL,cost INTEGER NOT NULL CHECK(cost>=0),hours INTEGER NOT NULL CHECK(hours>0),capacity INTEGER NOT NULL CHECK(capacity>0),available_from TEXT NOT NULL,available_to TEXT NOT NULL,CHECK(available_to>=available_from));
CREATE TABLE course_skill(course_id TEXT NOT NULL REFERENCES course(id),skill_id TEXT NOT NULL REFERENCES skill(id),exit_level INTEGER NOT NULL CHECK(exit_level BETWEEN 1 AND 5),PRIMARY KEY(course_id,skill_id));
CREATE TABLE prerequisite(course_id TEXT NOT NULL REFERENCES course(id),required_course_id TEXT NOT NULL REFERENCES course(id),PRIMARY KEY(course_id,required_course_id),CHECK(course_id!=required_course_id));
CREATE TABLE budget(id TEXT PRIMARY KEY,department TEXT NOT NULL,year INTEGER NOT NULL,amount INTEGER NOT NULL CHECK(amount>=0),UNIQUE(department,year));
CREATE TABLE enrollment(id TEXT PRIMARY KEY,employee_id TEXT NOT NULL REFERENCES employee(id),course_id TEXT NOT NULL REFERENCES course(id),budget_id TEXT NOT NULL REFERENCES budget(id),cost INTEGER NOT NULL CHECK(cost>=0),enrolled_on TEXT NOT NULL,UNIQUE(employee_id,course_id));
CREATE TABLE enrollment_event(id TEXT PRIMARY KEY,enrollment_id TEXT NOT NULL REFERENCES enrollment(id),state TEXT NOT NULL CHECK(state IN ('enrolled','completed','cancelled')),occurred_on TEXT NOT NULL);
CREATE TABLE completion(id TEXT PRIMARY KEY,enrollment_id TEXT NOT NULL UNIQUE REFERENCES enrollment(id),completed_on TEXT NOT NULL);
CREATE TABLE reassessment(id TEXT PRIMARY KEY,completion_id TEXT NOT NULL REFERENCES completion(id),employee_id TEXT NOT NULL REFERENCES employee(id),skill_id TEXT NOT NULL REFERENCES skill(id),level INTEGER NOT NULL CHECK(level BETWEEN 0 AND 5),assessed_on TEXT NOT NULL,UNIQUE(completion_id,skill_id));
CREATE TABLE career_path(id TEXT PRIMARY KEY,from_role_id TEXT NOT NULL REFERENCES role(id),to_role_id TEXT NOT NULL REFERENCES role(id),name TEXT NOT NULL);
CREATE TABLE learning_plan(id TEXT PRIMARY KEY,employee_id TEXT NOT NULL REFERENCES employee(id),target_role_id TEXT NOT NULL REFERENCES role(id),created_on TEXT NOT NULL,period_end TEXT NOT NULL,budget_remaining INTEGER NOT NULL,hour_limit INTEGER NOT NULL);
CREATE TABLE plan_item(plan_id TEXT NOT NULL REFERENCES learning_plan(id),course_id TEXT NOT NULL REFERENCES course(id),position INTEGER NOT NULL,PRIMARY KEY(plan_id,course_id),UNIQUE(plan_id,position));
CREATE TABLE plan_event(id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES learning_plan(id),state TEXT NOT NULL CHECK(state IN ('recommended','approved','rejected')),occurred_on TEXT NOT NULL,reason TEXT NOT NULL);
CREATE INDEX ix_enrollment_employee ON enrollment(employee_id);
CREATE INDEX ix_enrollment_course ON enrollment(course_id);
CREATE INDEX ix_enrollment_budget ON enrollment(budget_id);
CREATE INDEX ix_event_enrollment ON enrollment_event(enrollment_id,state);
CREATE INDEX ix_reassessment_employee ON reassessment(employee_id,assessed_on,id);
CREATE INDEX ix_prerequisite_course ON prerequisite(course_id);

'''
ROLE_NAMES = ['Data Analyst','Data Engineer','Analytics Engineer','ML Engineer','Backend Engineer','Platform Engineer','Cloud Engineer','Security Analyst','Reliability Engineer','QA Engineer','Product Analyst','Technical Support Engineer','Business Analyst','Operations Analyst','Finance Analyst','People Analyst','Learning Coordinator','Sales Engineer','Solutions Engineer','Customer Success Analyst','Database Engineer','Integration Engineer','AI Solutions Engineer','Technical Program Analyst','Engineering Lead']
SKILL_FAMILIES = ['Python','SQL','Data Modeling','Statistics','Machine Learning','API Design','Cloud Fundamentals','Security','Reliability','Test Engineering','Product Analytics','Customer Support','Process Analysis','Operations','Financial Analysis','People Analytics','Learning Design','Technical Sales','Solution Design','Data Governance']
SKILL_TOPICS = ['Foundations','Applied Practice','Diagnostics','Design','Validation','Automation','Quality','Performance','Documentation','Monitoring','Integration','Risk Review','Troubleshooting','Planning','Measurement','Communication','Implementation','Optimization','Controls','Reporting','Evaluation','Maintenance','Scaling','Change Management','Review']
TABLES = ['role','skill','employee','role_skill_target','employee_skill','course','course_skill','prerequisite','budget','enrollment','enrollment_event','completion','reassessment','career_path','learning_plan','plan_item','plan_event']

def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def rows(db, sql, args=()):
    return [dict(r) for r in db.execute(sql,args)]

def effective_levels(db, employee):
    levels = {r['skill_id']: r['level'] for r in db.execute('SELECT * FROM employee_skill WHERE employee_id=?',(employee,))}
    # Chronology matters: reassessment can lower proficiency, not only increase it.
    for r in db.execute('SELECT * FROM reassessment WHERE employee_id=? AND assessed_on<=? ORDER BY assessed_on,id',(employee,AS_OF)):
        levels[r['skill_id']] = r['level']
    return levels

def completed_courses(db, employee):
    return {r[0] for r in db.execute('SELECT e.course_id FROM enrollment e JOIN completion c ON c.enrollment_id=e.id WHERE e.employee_id=? AND c.completed_on<=?',(employee,AS_OF))}

def gaps(db,employee,target_role=None):
    e = db.execute('SELECT * FROM employee WHERE id=?',(employee,)).fetchone()
    if not e: raise ValueError('Unknown employee')
    role = target_role or e['role_id']
    if not db.execute('SELECT 1 FROM role WHERE id=?',(role,)).fetchone(): raise ValueError('Unknown target role')
    levels = effective_levels(db, employee)
    return [dict(r, current=levels.get(r['skill_id'],0), gap=max(0,r['target']-levels.get(r['skill_id'],0))) for r in rows(db,'SELECT t.*,s.name FROM role_skill_target t JOIN skill s ON s.id=t.skill_id WHERE role_id=? ORDER BY t.skill_id',(role,))]

def budget_remaining(db,department):
    b=db.execute('SELECT * FROM budget WHERE department=? AND year=2026',(department,)).fetchone()
    spent=db.execute("SELECT COALESCE(SUM(e.cost),0) FROM enrollment e WHERE e.budget_id=? AND NOT EXISTS(SELECT 1 FROM enrollment_event v WHERE v.enrollment_id=e.id AND v.state='cancelled')",(b['id'],)).fetchone()[0]
    return b['amount']-spent

def recommend(db,employee,target_role=None,hour_limit=120,period_end='2027-03-31'):
    if hour_limit<1 or hour_limit>2000: raise ValueError('Hour limit must be 1..2000')
    if date.fromisoformat(period_end)<date.fromisoformat(AS_OF): raise ValueError('Planning end precedes planning start')
    e=db.execute('SELECT * FROM employee WHERE id=?',(employee,)).fetchone()
    if not e: raise ValueError('Unknown employee')
    gs=gaps(db,employee,target_role)
    targets={g['skill_id']:g['target'] for g in gs}
    levels=effective_levels(db,employee)
    courses={c['id']:c for c in rows(db,'SELECT * FROM course ORDER BY id')}
    outcomes={}
    for r in rows(db,'SELECT * FROM course_skill'): outcomes.setdefault(r['course_id'],[]).append(r)
    prereqs={}
    for r in rows(db,'SELECT * FROM prerequisite ORDER BY required_course_id'): prereqs.setdefault(r['course_id'],[]).append(r['required_course_id'])
    counts={r['course_id']:r['n'] for r in rows(db,"SELECT e.course_id,COUNT(*) n FROM enrollment e WHERE NOT EXISTS(SELECT 1 FROM enrollment_event v WHERE v.enrollment_id=e.id AND v.state='cancelled') GROUP BY e.course_id")}
    active={r[0] for r in db.execute("SELECT course_id FROM enrollment e WHERE employee_id=? AND NOT EXISTS(SELECT 1 FROM enrollment_event v WHERE v.enrollment_id=e.id AND v.state IN ('completed','cancelled'))",(employee,))}
    done=completed_courses(db,employee); selected=[]; money=budget_remaining(db,e['department']); total_cost=0; total_hours=0; reasons=Counter(); plan_cursor=date.fromisoformat(AS_OF)
    def chain(cid,seen=None):
        seen=set() if seen is None else set(seen)
        if cid in done or cid in selected:return []
        if cid in seen:raise ValueError('prerequisite_cycle')
        seen.add(cid)
        result=[]
        for p in prereqs.get(cid,[]):
            for x in chain(p,seen):
                if x not in result: result.append(x)
        return result+[cid]
    while True:
        choices=[]
        for cid in courses:
            if cid in done or cid in selected:continue
            try: bundle=chain(cid)
            except ValueError:reasons['prerequisite_cycle']+=1;continue
            if any(x in active for x in bundle):reasons['already_enrolled']+=1;continue
            bc=[courses[x] for x in bundle]
            if any(c['available_from']>period_end or c['available_to']<AS_OF for c in bc): reasons['unavailable']+=1;continue
            if any(counts.get(c['id'],0)>=c['capacity'] for c in bc): reasons['capacity']+=1;continue
            cost=sum(c['cost'] for c in bc); hours=sum(c['hours'] for c in bc)
            if total_cost+cost>money:reasons['budget']+=1;continue
            if total_hours+hours>hour_limit:reasons['hours']+=1;continue
            # Sequence earliest possible completion; eight study hours per week.
            cursor=plan_cursor
            feasible=True
            for c in bc:
                cursor=max(cursor,date.fromisoformat(c['available_from']))+timedelta(days=(c['hours']*7+7)//8)
                if cursor>min(date.fromisoformat(c['available_to']),date.fromisoformat(period_end)):feasible=False;break
            if not feasible:reasons['schedule']+=1;continue
            projected=dict(levels)
            for x in bundle:
                for out in outcomes.get(x,[]):projected[out['skill_id']]=max(projected.get(out['skill_id'],0),out['exit_level'])
            gain=sum(min(t,projected.get(s,0))-min(t,levels.get(s,0)) for s,t in targets.items())
            if gain<=0:continue
            choices.append((gain/(hours+cost/100+1),gain,-cost,cid,bundle,projected,cost,hours,cursor))
        if not choices:break
        _,_,_,_,bundle,levels,cost,hours,plan_cursor=max(choices,key=lambda v:(v[0],v[1],v[2],v[3]))
        selected.extend(bundle);total_cost+=cost;total_hours+=hours
    initial=sum(g['gap'] for g in gs)
    residual=sum(max(0,t-levels.get(s,0)) for s,t in targets.items())
    sequence=[]; cursor=date.fromisoformat(AS_OF); projected=effective_levels(db,employee)
    for i,cid in enumerate(selected):
        c=courses[cid]; start=max(cursor,date.fromisoformat(c['available_from'])); finish=start+timedelta(days=(c['hours']*7+7)//8)
        explained=[]
        for out in outcomes.get(cid,[]):
            before=projected.get(out['skill_id'],0); after=max(before,out['exit_level']);projected[out['skill_id']]=after
            explained.append({'skill_id':out['skill_id'],'assumed_before':before,'projected_after':after,'target':targets.get(out['skill_id']),'basis':'Advertised course exit level, pending future reassessment'})
        sequence.append(dict(c,position=i+1,prerequisites=prereqs.get(cid,[]),planned_start=start.isoformat(),planned_finish=finish.isoformat(),outcomes=explained));cursor=finish
    return {'employee_id':employee,'employee_name':e['name'],'department':e['department'],'target_role_id':target_role or e['role_id'],'as_of':AS_OF,'period_end':period_end,'hour_limit':hour_limit,'gaps':gs,'courses':sequence,'cost':total_cost,'hours':total_hours,'expected_finish':plan_cursor.isoformat(),'budget_remaining_before':money,'budget_remaining_after':money-total_cost,'initial_gap':initial,'projected_gap':residual,'projected_gap_closure':round((initial-residual)/initial,4) if initial else 1.0,'decision':'feasible_path' if selected else ('already_at_target' if not initial else 'no_feasible_path'),'excluded_candidate_reasons':dict(sorted(reasons.items())),'warning':'Projected learning is not verified proficiency. Completion alone never changes assessed skill. This recommendation is not a seat or budget reservation.'}

def approve_plan(db,employee,target_role=None,hour_limit=120,period_end='2027-03-31'):
    # Serialize approvals so capacity and department budget are checked at commit time.
    db.execute('BEGIN IMMEDIATE')
    try:
        plan=recommend(db,employee,target_role,hour_limit,period_end)
        if not plan['courses']:raise ValueError('No feasible courses to approve')
        n=db.execute('SELECT COUNT(*) FROM learning_plan').fetchone()[0]+1
        pid=f'PLN-{n:06d}'
        db.execute('INSERT INTO learning_plan VALUES(?,?,?,?,?,?,?)',(pid,employee,plan['target_role_id'],AS_OF,period_end,plan['budget_remaining_before'],hour_limit))
        bid=db.execute('SELECT id FROM budget WHERE department=? AND year=2026',(plan['department'],)).fetchone()[0]
        for c in plan['courses']:
            eid=f'ENR-{employee}-{c["id"]}'
            db.execute('INSERT INTO plan_item VALUES(?,?,?)',(pid,c['id'],c['position']))
            db.execute('INSERT INTO enrollment VALUES(?,?,?,?,?,?)',(eid,employee,c['id'],bid,c['cost'],AS_OF))
            db.execute('INSERT INTO enrollment_event VALUES(?,?,?,?)',(f'EV-{eid}',eid,'enrolled',AS_OF))
        db.execute('INSERT INTO plan_event VALUES(?,?,?,?,?)',(pid+'-1',pid,'recommended',AS_OF,'Recomputed under transaction lock'))
        db.execute('INSERT INTO plan_event VALUES(?,?,?,?,?)',(pid+'-2',pid,'approved',AS_OF,'Budget and seats reserved; prerequisites are ordered future learning'))
        db.commit();return dict(plan,plan_id=pid)
    except Exception:
        db.rollback();raise

def record_completion(db,enrollment_id,when=AS_OF):
    date.fromisoformat(when)
    e=db.execute('SELECT * FROM enrollment WHERE id=?',(enrollment_id,)).fetchone()
    if not e:raise ValueError('Unknown enrollment')
    if when<e['enrolled_on'] or when>AS_OF:raise ValueError('Completion date outside enrollment/as-of window')
    if db.execute("SELECT 1 FROM enrollment_event WHERE enrollment_id=? AND state='cancelled'",(enrollment_id,)).fetchone():raise ValueError('Cancelled enrollment')
    if db.execute('SELECT 1 FROM completion WHERE enrollment_id=?',(enrollment_id,)).fetchone():raise ValueError('Completion already recorded')
    for p in db.execute('SELECT required_course_id FROM prerequisite WHERE course_id=?',(e['course_id'],)):
        if not db.execute('SELECT 1 FROM enrollment x JOIN completion c ON c.enrollment_id=x.id WHERE x.employee_id=? AND x.course_id=? AND c.completed_on<=?',(e['employee_id'],p[0],when)).fetchone():raise ValueError('Prerequisite not completed')
    n=db.execute('SELECT COUNT(*) FROM completion').fetchone()[0]+1
    cid=f'CMP-2026-{n:06d}'
    with db:
        db.execute('INSERT INTO completion VALUES(?,?,?)',(cid,enrollment_id,when))
        db.execute('INSERT INTO enrollment_event VALUES(?,?,?,?)',(cid+'-event',enrollment_id,'completed',when))
    return cid

def reassess(db,completion_id,skill_id,level,when=AS_OF):
    if not isinstance(level,int) or isinstance(level,bool) or not 0<=level<=5:raise ValueError('Level must be integer 0..5')
    date.fromisoformat(when)
    c=db.execute('SELECT c.*,e.employee_id,e.course_id FROM completion c JOIN enrollment e ON e.id=c.enrollment_id WHERE c.id=?',(completion_id,)).fetchone()
    if not c:raise ValueError('Unknown completion')
    if when<c['completed_on'] or when>AS_OF:raise ValueError('Invalid reassessment date')
    if not db.execute('SELECT 1 FROM course_skill WHERE course_id=? AND skill_id=?',(c['course_id'],skill_id)).fetchone():raise ValueError('Skill not taught by course')
    rid=f'REA-{completion_id}-{skill_id}'
    with db:db.execute('INSERT INTO reassessment VALUES(?,?,?,?,?,?)',(rid,completion_id,c['employee_id'],skill_id,level,when))
    return rid

def generate(path,scale='starter',seed=20261022):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():path.unlink()
    db=connect(path);db.executescript(SCHEMA)
    rng=random.Random(seed)
    ne,ns,nc,nen=(5000,500,1000,10000) if scale=='full' else (100,30,60,200)
    nr=min(25,ns//2);deps=['Engineering','Operations','Sales','People','Finance']
    for r in range(nr):db.execute('INSERT INTO role VALUES(?,?)',(f'ROL-{r+1:06d}',ROLE_NAMES[r]))
    for s in range(ns):db.execute('INSERT INTO skill VALUES(?,?)',(f'SKL-{s+1:06d}',f'{SKILL_FAMILIES[s//25%len(SKILL_FAMILIES)]}: {SKILL_TOPICS[s%25]}'))
    targets={}
    for r in range(nr):
        targets[r]=[(r*7+i)%ns for i in range(8)]
        for s in targets[r]:db.execute('INSERT INTO role_skill_target VALUES(?,?,?,?)',(f'ROL-{r+1:06d}',f'SKL-{s+1:06d}',rng.choice([3,3,4,4,5]),'2026-01-01'))
        if r+1<nr:db.execute('INSERT INTO career_path VALUES(?,?,?,?)',(f'CAR-{r+1:06d}',f'ROL-{r+1:06d}',f'ROL-{r+2:06d}',f'{ROLE_NAMES[r]} to {ROLE_NAMES[r+1]}'))
    for c in range(nc):
        advanced=c>=ns;sid=c%ns
        cost=rng.choice([0,1500,2500,4000,6000,9000]);hours=rng.choice([4,8,12,16,24])
        start='2027-07-01' if c%41==40 or sid==ns-1 else '2026-01-01';end='2027-12-31'
        db.execute('INSERT INTO course VALUES(?,?,?,?,?,?,?)',(f'CRS-{c+1:06d}',f'{"Advanced" if advanced else "Foundation"}: {SKILL_FAMILIES[sid//25%len(SKILL_FAMILIES)]} / {SKILL_TOPICS[sid%25]}',cost,hours,rng.choice([12,20,40,80]),start,end))
        db.execute('INSERT INTO course_skill VALUES(?,?,?)',(f'CRS-{c+1:06d}',f'SKL-{sid+1:06d}',5 if advanced else 3))
        if advanced:db.execute('INSERT INTO prerequisite VALUES(?,?)',(f'CRS-{c+1:06d}',f'CRS-{sid+1:06d}'))
    enroll_counts=Counter();spent=Counter();compn=0
    for i in range(ne):
        eid=f'EMP-{i+1:06d}';r=i%nr;dep=deps[i%len(deps)]
        db.execute('INSERT INTO employee VALUES(?,?,?,?,?)',(eid,f'Synthetic Employee {i+1:05d}',f'ROL-{r+1:06d}',dep,'2026-01-01'))
        for s in targets[r]:db.execute('INSERT INTO employee_skill VALUES(?,?,?,?)',(eid,f'SKL-{s+1:06d}',rng.choices([0,1,2,3,4,5],[5,15,30,30,15,5])[0],'2026-01-02'))
    # Parent budget rows are created before child enrollments; final allocations are derived from spend.
    for dep in deps:db.execute('INSERT INTO budget VALUES(?,?,?,?)',(f'BUD-{dep}-2026',dep,2026,10**9))
    for i in range(nen):
        emp=i//2;eid=f'EMP-{emp+1:06d}';dep=deps[emp%5];r=emp%nr
        candidates=[s for s in targets[r] if s%41!=40 and s!=ns-1]
        sid=candidates[i%2];cid=f'CRS-{sid+1:06d}';enid=f'ENR-{eid}-{cid}'
        cost=db.execute('SELECT cost FROM course WHERE id=?',(cid,)).fetchone()[0]
        db.execute('INSERT INTO enrollment VALUES(?,?,?,?,?,?)',(enid,eid,cid,f'BUD-{dep}-2026',cost,'2026-02-01'))
        db.execute('INSERT INTO enrollment_event VALUES(?,?,?,?)',(f'EV-{i+1:06d}-1',enid,'enrolled','2026-02-01'))
        enroll_counts[cid]+=1;spent[dep]+=cost
        if rng.random()<0.72:
            compn+=1;cp=f'CMP-2026-{compn:06d}'
            db.execute('INSERT INTO completion VALUES(?,?,?)',(cp,enid,'2026-03-01'))
            db.execute('INSERT INTO enrollment_event VALUES(?,?,?,?)',(f'EV-{i+1:06d}-2',enid,'completed','2026-03-01'))
            if rng.random()<0.8:
                # Outcome measured separately: some courses do not yield mastery.
                level=rng.choices([1,2,3],[10,25,65])[0]
                db.execute('INSERT INTO reassessment VALUES(?,?,?,?,?,?)',(f'REA-{compn:06d}',cp,eid,f'SKL-{sid+1:06d}',level,'2026-03-08'))
    for cid,count in enroll_counts.items():db.execute('UPDATE course SET capacity=MAX(capacity,?) WHERE id=?',(count+4,cid))
    for dep in deps:db.execute('UPDATE budget SET amount=? WHERE department=?',(spent[dep]+rng.choice([30000,60000,120000]),dep))
    db.commit();db.close()
    return {'scale':scale,'seed':seed,'employees':ne,'skills':ns,'courses':nc,'enrollments':nen}

def validate(db):
    checks=[]
    def ck(name,sql):
        bad=rows(db,sql);checks.append({'check':name,'passed':not bad,'violations':len(bad),'examples':bad[:3]})
    ck('foreign_keys','PRAGMA foreign_key_check')
    for t in TABLES:
        cols=rows(db,f'PRAGMA table_info({t})');pk=[c['name'] for c in cols if c['pk']]
        ck(t+'_primary_key_unique',f'SELECT {",".join(pk)},COUNT(*) n FROM {t} GROUP BY {",".join(pk)} HAVING n>1')
    ck('lifecycle_terminal_exclusive',"SELECT enrollment_id FROM enrollment_event WHERE state IN ('completed','cancelled') GROUP BY enrollment_id HAVING COUNT(*)>1")
    ck('event_date_order','SELECT v.id FROM enrollment_event v JOIN enrollment e ON e.id=v.enrollment_id WHERE v.occurred_on<e.enrolled_on')
    ck('lifecycle_terminal_has_completion',"SELECT v.id FROM enrollment_event v WHERE v.state='completed' AND NOT EXISTS(SELECT 1 FROM completion c WHERE c.enrollment_id=v.enrollment_id AND c.completed_on=v.occurred_on)")
    ck('completion_date_order','SELECT c.id FROM completion c JOIN enrollment e ON e.id=c.enrollment_id WHERE c.completed_on<e.enrolled_on')
    ck('reassessment_date_order','SELECT r.id FROM reassessment r JOIN completion c ON c.id=r.completion_id WHERE r.assessed_on<c.completed_on')
    ck('reassessment_employee_and_skill','SELECT r.id FROM reassessment r JOIN completion c ON c.id=r.completion_id JOIN enrollment e ON e.id=c.enrollment_id WHERE r.employee_id!=e.employee_id OR NOT EXISTS(SELECT 1 FROM course_skill s WHERE s.course_id=e.course_id AND s.skill_id=r.skill_id)')
    ck('enrollment_cost_reconciliation','SELECT e.id FROM enrollment e JOIN course c ON c.id=e.course_id WHERE e.cost!=c.cost')
    ck('capacity','SELECT c.id FROM course c JOIN enrollment e ON e.course_id=c.id WHERE NOT EXISTS(SELECT 1 FROM enrollment_event v WHERE v.enrollment_id=e.id AND v.state=\'cancelled\') GROUP BY c.id HAVING COUNT(*)>c.capacity')
    ck('budget_reconciliation','SELECT b.id FROM budget b LEFT JOIN enrollment e ON e.budget_id=b.id AND NOT EXISTS(SELECT 1 FROM enrollment_event v WHERE v.enrollment_id=e.id AND v.state=\'cancelled\') GROUP BY b.id HAVING COALESCE(SUM(e.cost),0)>b.amount')
    ck('budget_department','SELECT e.id FROM enrollment e JOIN employee p ON p.id=e.employee_id JOIN budget b ON b.id=e.budget_id WHERE p.department!=b.department')
    ck('completion_event_consistency',"SELECT c.id FROM completion c WHERE NOT EXISTS(SELECT 1 FROM enrollment_event v WHERE v.enrollment_id=c.enrollment_id AND v.state='completed' AND v.occurred_on=c.completed_on)")
    ck('lifecycle_enrollment_event',"SELECT e.id FROM enrollment e WHERE (SELECT COUNT(*) FROM enrollment_event v WHERE v.enrollment_id=e.id AND v.state='enrolled')!=1")
    ck('event_enum',"SELECT id FROM enrollment_event WHERE state NOT IN ('enrolled','completed','cancelled')")
    ck('enrollment_availability','SELECT e.id FROM enrollment e JOIN course c ON c.id=e.course_id WHERE e.enrolled_on<c.available_from OR e.enrolled_on>c.available_to')
    ck('prerequisite_completion','SELECT c.id FROM completion c JOIN enrollment e ON e.id=c.enrollment_id JOIN prerequisite p ON p.course_id=e.course_id WHERE NOT EXISTS(SELECT 1 FROM enrollment x JOIN completion y ON y.enrollment_id=x.id WHERE x.employee_id=e.employee_id AND x.course_id=p.required_course_id AND y.completed_on<=c.completed_on)')
    # Directed graph cycle detection without unbounded recursive SQL.
    graph={}
    for r in rows(db,'SELECT * FROM prerequisite'):graph.setdefault(r['course_id'],[]).append(r['required_course_id'])
    visiting=set();seen=set();cycles=[]
    def visit(n):
        if n in visiting:cycles.append(n);return
        if n in seen:return
        visiting.add(n)
        for child in graph.get(n,[]):visit(child)
        visiting.remove(n);seen.add(n)
    for n in graph:visit(n)
    checks.append({'check':'prerequisite_acyclic','passed':not cycles,'violations':len(cycles),'examples':cycles[:3]})
    return {'passed':all(x['passed'] for x in checks),'checks':checks,'row_counts':{t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in TABLES}}

def anomaly_cases():
    # Self-contained evaluation inputs; labels live in a separate file, never in the detector input.
    baseline={'completed':['CRS-000001'],'planned':['CRS-000002'],'prerequisites':{'CRS-000002':['CRS-000001']},'cost':100,'budget':200,'completions':['CMP-2026-000001'],'target':4,'assessed_level':4,'completion_present':True,'reassessed':True,'available_from':'2026-01-01','available_to':'2026-12-31','planning_on':AS_OF}
    variants=[('valid',{}),('missing_prerequisite',{'completed':[]}),('over_budget',{'cost':201}),('duplicate_completion',{'completions':['CMP-2026-000001','CMP-2026-000001']}),('unverified_outcome',{'assessed_level':2,'reassessed':False}),('unavailable',{'available_from':'2027-01-01'}),('exact_budget',{'cost':200}),('last_available_day',{'available_to':AS_OF}),('below_target_after_reassessment',{'assessed_level':2}),('multiple_issues',{'completed':[],'cost':250})]
    expected=[[],['prerequisite_violation'],['budget_exceeded'],['duplicate_completion'],['missing_reassessment'],['course_unavailable'],[],[],['residual_skill_gap'],['budget_exceeded','prerequisite_violation']]
    return [dict(baseline,case_id=f'CASE-{i+1:03d}',**patch) for i,(_,patch) in enumerate(variants)], [{'case_id':f'CASE-{i+1:03d}','issue_type':name,'expected':expected[i]} for i,(name,_) in enumerate(variants)]

def detect(case):
    issues=[];done=set(case['completed'])
    for c in case['planned']:
        if any(p not in done for p in case['prerequisites'].get(c,[])):issues.append('prerequisite_violation')
        done.add(c)
    if case['cost']>case['budget']:issues.append('budget_exceeded')
    if len(case['completions'])!=len(set(case['completions'])):issues.append('duplicate_completion')
    if case['completion_present'] and not case['reassessed']:issues.append('missing_reassessment')
    elif case['assessed_level']<case['target']:issues.append('residual_skill_gap')
    if not case['available_from']<=case['planning_on']<=case['available_to']:issues.append('course_unavailable')
    return sorted(set(issues))

def export(path,out,meta):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);db=connect(path);checksums={}
    for table in TABLES:
        data=rows(db,f'SELECT * FROM {table} ORDER BY rowid')
        fields=[r['name'] for r in rows(db,f'PRAGMA table_info({table})')]
        with (out/(table+'.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fields);w.writeheader();w.writerows(data)
        (out/(table+'.json')).write_text(json.dumps(data,indent=2)+'\n')
        for ext in ['csv','json']:
            file=out/(table+'.'+ext);checksums[file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
    (out/'seed.sql').write_text('\n'.join(db.iterdump())+'\n');checksums['seed.sql']=hashlib.sha256((out/'seed.sql').read_bytes()).hexdigest()
    cases,truth=anomaly_cases();(out/'scenario_inputs.json').write_text(json.dumps(cases,indent=2)+'\n');(out/'ground_truth.json').write_text(json.dumps(truth,indent=2)+'\n')
    predictions={c['case_id']:detect(c) for c in cases}
    exact=sum(predictions[t['case_id']]==t['expected'] for t in truth)
    tp=sum(len(set(predictions[t['case_id']])&set(t['expected'])) for t in truth);fp=sum(len(set(predictions[t['case_id']])-set(t['expected'])) for t in truth);fn=sum(len(set(t['expected'])-set(predictions[t['case_id']])) for t in truth)
    evaluation={'cases':len(cases),'exact_matches':exact,'exact_match_rate':exact/len(cases),'precision':tp/(tp+fp) if tp+fp else 1,'recall':tp/(tp+fn) if tp+fn else 1,'predictions':predictions,'scope':'Deterministic labelled scenario checks, not evidence of real-world ML generalization.'}
    export_baseline_anomalies(db,out)
    report=validate(db);(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'evaluation.json').write_text(json.dumps(evaluation,indent=2)+'\n')
    for name in ['scenario_inputs.json','ground_truth.json','anomaly_stream.json','anomaly_ground_truth.json','anomaly_validation.json','validation.json','evaluation.json']:
        checksums[name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
    (out/'manifest.json').write_text(json.dumps(dict(meta,as_of=AS_OF,source='Entirely synthetic; no external datasets or personal data',units={'cost':'INR whole rupees','hours':'study hours','level':'ordinal 0..5'},checksums=checksums),indent=2)+'\n')
    db.close();return report

def baseline_anomaly_stream(db):
    """Proposed records reference clean baseline parents; mutations stay in an audit sidecar."""
    employee=db.execute('SELECT * FROM employee ORDER BY id LIMIT 1').fetchone()
    eid=employee['id'];dep=employee['department'];remaining=budget_remaining(db,dep)
    advanced=db.execute('SELECT p.course_id,p.required_course_id FROM prerequisite p WHERE NOT EXISTS(SELECT 1 FROM enrollment e JOIN completion c ON c.enrollment_id=e.id WHERE e.employee_id=? AND e.course_id=p.required_course_id) ORDER BY p.course_id LIMIT 1',(eid,)).fetchone()
    unavailable=db.execute('SELECT id FROM course WHERE available_from>? ORDER BY id LIMIT 1',(AS_OF,)).fetchone()[0]
    duplicate=db.execute('SELECT c.*,e.employee_id,e.course_id FROM completion c JOIN enrollment e ON e.id=c.enrollment_id ORDER BY c.id LIMIT 1').fetchone()
    missing=db.execute('''SELECT c.id completion_id,e.employee_id,e.course_id,s.skill_id,t.target FROM completion c JOIN enrollment e ON e.id=c.enrollment_id JOIN employee p ON p.id=e.employee_id JOIN course_skill s ON s.course_id=e.course_id JOIN role_skill_target t ON t.role_id=p.role_id AND t.skill_id=s.skill_id WHERE NOT EXISTS(SELECT 1 FROM reassessment r WHERE r.completion_id=c.id) ORDER BY c.id''').fetchall()
    missing=next(r for r in missing if effective_levels(db,r['employee_id']).get(r['skill_id'],0)<r['target'])
    # Each sidecar item is a proposed event, not a feature row nor a ground-truth-bearing input.
    records=[
      {'kind':'recommendation','employee_id':eid,'course_ids':[advanced['course_id']],'planning_on':AS_OF,'proposed_cost':0},
      {'kind':'budget_reservation','employee_id':eid,'budget_id':f'BUD-{dep}-2026','proposed_cost':remaining+1},
      {'kind':'completion','employee_id':duplicate['employee_id'],'enrollment_id':duplicate['enrollment_id'],'completion_id':duplicate['id'],'completed_on':duplicate['completed_on']},
      {'kind':'learning_claim','employee_id':missing['employee_id'],'completion_id':missing['completion_id'],'skill_id':missing['skill_id'],'claimed_level':missing['target']},
      {'kind':'recommendation','employee_id':eid,'course_ids':[unavailable],'planning_on':AS_OF,'proposed_cost':0},
      {'kind':'budget_reservation','employee_id':eid,'budget_id':f'BUD-{dep}-2026','proposed_cost':remaining},
      {'kind':'learning_claim','employee_id':missing['employee_id'],'completion_id':missing['completion_id'],'skill_id':missing['skill_id'],'claimed_level':effective_levels(db,missing['employee_id']).get(missing['skill_id'],0)},
    ]
    # The unavailable course may also have an unmet prerequisite. Isolate availability explicitly with a foundation.
    foundation=db.execute('SELECT id FROM course c WHERE c.available_from>? AND NOT EXISTS(SELECT 1 FROM prerequisite p WHERE p.course_id=c.id) ORDER BY id LIMIT 1',(AS_OF,)).fetchone()[0]
    records[4]['course_ids']=[foundation]
    expected=[['prerequisite_violation'],['budget_exceeded'],['duplicate_completion'],['missing_reassessment'],['course_unavailable'],[],[]]
    names=['prerequisite_violation','budget_exceeded','duplicate_completion','missing_reassessment','course_unavailable','exact_budget_boundary','no_false_learning_claim']
    for i,r in enumerate(records):r['record_id']=f'INJECT-{i+1:06d}'
    truth=[{'record_id':r['record_id'],'issue_type':names[i],'expected':expected[i]} for i,r in enumerate(records)]
    return records,truth

def detect_baseline_record(db,record):
    """Evaluate proposed sidecar events from baseline source facts only. Never read labels."""
    issues=[];kind=record['kind'];eid=record['employee_id']
    if not db.execute('SELECT 1 FROM employee WHERE id=?',(eid,)).fetchone():return ['unknown_employee']
    if kind=='recommendation':
        done=completed_courses(db,eid)
        for cid in record['course_ids']:
            course=db.execute('SELECT * FROM course WHERE id=?',(cid,)).fetchone()
            if not course:issues.append('unknown_course');continue
            if not course['available_from']<=record['planning_on']<=course['available_to']:issues.append('course_unavailable')
            if any(p[0] not in done for p in db.execute('SELECT required_course_id FROM prerequisite WHERE course_id=?',(cid,))):issues.append('prerequisite_violation')
            done.add(cid)
    elif kind=='budget_reservation':
        b=db.execute('SELECT * FROM budget WHERE id=?',(record['budget_id'],)).fetchone()
        dep=db.execute('SELECT department FROM employee WHERE id=?',(eid,)).fetchone()[0]
        if not b or b['department']!=dep:issues.append('invalid_budget_parent')
        elif record['proposed_cost']>budget_remaining(db,dep):issues.append('budget_exceeded')
    elif kind=='completion':
        parent=db.execute('SELECT * FROM enrollment WHERE id=?',(record['enrollment_id'],)).fetchone()
        if not parent or parent['employee_id']!=eid:issues.append('invalid_enrollment_parent')
        if db.execute('SELECT 1 FROM completion WHERE id=? OR enrollment_id=?',(record['completion_id'],record['enrollment_id'])).fetchone():issues.append('duplicate_completion')
    elif kind=='learning_claim':
        c=db.execute('SELECT e.employee_id FROM completion c JOIN enrollment e ON e.id=c.enrollment_id WHERE c.id=?',(record['completion_id'],)).fetchone()
        if not c or c['employee_id']!=eid:issues.append('invalid_completion_parent')
        measured=effective_levels(db,eid).get(record['skill_id'],0)
        reassessed=db.execute('SELECT 1 FROM reassessment WHERE completion_id=? AND skill_id=?',(record['completion_id'],record['skill_id'])).fetchone()
        if record['claimed_level']>measured and not reassessed:issues.append('missing_reassessment')
    else:issues.append('unknown_record_kind')
    return sorted(set(issues))

def export_baseline_anomalies(db,out):
    out=Path(out);records,truth=baseline_anomaly_stream(db)
    (out/'anomaly_stream.json').write_text(json.dumps(records,indent=2)+'\n')
    (out/'anomaly_ground_truth.json').write_text(json.dumps(truth,indent=2)+'\n')
    predictions={r['record_id']:detect_baseline_record(db,r) for r in records}
    refs=[]
    for r in records:
        # Each source ID is validated by kind-specific checks and source lookups.
        valid=db.execute('SELECT 1 FROM employee WHERE id=?',(r['employee_id'],)).fetchone() is not None
        if 'course_ids' in r:valid=valid and all(db.execute('SELECT 1 FROM course WHERE id=?',(c,)).fetchone() is not None for c in r['course_ids'])
        for field,table in [('budget_id','budget'),('enrollment_id','enrollment'),('completion_id','completion'),('skill_id','skill')]:
            if field in r:valid=valid and db.execute(f'SELECT 1 FROM {table} WHERE id=?',(r[field],)).fetchone() is not None
        refs.append({'record_id':r['record_id'],'parent_ids_valid':valid})
    result={'records':len(records),'all_parent_ids_valid':all(x['parent_ids_valid'] for x in refs),'exact_matches':sum(predictions[t['record_id']]==t['expected'] for t in truth),'predictions':predictions,'parent_validation':refs,'isolation':'Proposed anomaly events are a sidecar tied to baseline IDs, never planner features or committed clean records.'}
    (out/'anomaly_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
