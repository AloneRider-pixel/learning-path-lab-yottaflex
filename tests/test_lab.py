import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from learninglab.core import *

class LabTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'lab.db';generate(self.path);self.db=connect(self.path)
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def test_integrity(self):self.assertTrue(validate(self.db)['passed'])
    def test_cycle_is_rejected_by_validator(self):
        self.db.execute("INSERT INTO prerequisite VALUES('CRS-000001','CRS-000031')");self.db.commit();self.assertFalse(validate(self.db)['passed']);p=recommend(self.db,'EMP-000001');self.assertIsInstance(p['courses'],list)
    def test_sql_export_round_trip(self):
        export(self.path,self.root/'export',{'seed':20261022});other=sqlite3.connect(':memory:');other.executescript((self.root/'export/seed.sql').read_text());self.assertEqual(other.execute('SELECT COUNT(*) FROM enrollment').fetchone()[0],200)
    def test_schedule_finishes_within_period(self):
        p=recommend(self.db,'EMP-000001',period_end='2026-11-30');self.assertLessEqual(p['expected_finish'],'2026-11-30')
    def test_no_null_foreign_keys(self):
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("INSERT INTO course_skill VALUES(NULL,'SKL-000001',3)")
    def test_pending_enrollment_not_duplicated(self):
        p=approve_plan(self.db,'EMP-000001');q=recommend(self.db,'EMP-000001');self.assertFalse({c['id'] for c in p['courses']}&{c['id'] for c in q['courses']})
    def test_future_completion_rejected(self):
        with self.assertRaises(ValueError):record_completion(self.db,'BAD','2027-01-01')
    def test_baseline_linked_anomalies(self):
        records,truth=baseline_anomaly_stream(self.db)
        for r,t in zip(records,truth):
            self.assertNotIn('expected',r);self.assertNotIn('issue_type',r);self.assertEqual(detect_baseline_record(self.db,r),t['expected'])
        result=export_baseline_anomalies(self.db,self.root);self.assertTrue(result['all_parent_ids_valid']);self.assertEqual(result['exact_matches'],7)
    def test_anomalies_leave_baseline_unchanged(self):
        before=self.db.total_changes;records,truth=baseline_anomaly_stream(self.db)
        for r in records:detect_baseline_record(self.db,r)
        self.assertEqual(before,self.db.total_changes);self.assertTrue(validate(self.db)['passed'])
    def test_anomaly_labels_not_planner_features(self):
        records,truth=baseline_anomaly_stream(self.db);p=recommend(self.db,'EMP-000001');self.assertNotIn('ground_truth',p);self.assertNotIn('anomaly',p)
    def test_transaction_rolls_back_partial_reservation(self):
        before=self.db.execute('SELECT COUNT(*) FROM enrollment').fetchone()[0]
        self.db.execute("CREATE TRIGGER test_fail BEFORE INSERT ON plan_event BEGIN SELECT RAISE(ABORT,'simulated event failure'); END;");self.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):approve_plan(self.db,'EMP-000001')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM enrollment').fetchone()[0],before);self.assertEqual(self.db.execute('SELECT COUNT(*) FROM learning_plan').fetchone()[0],0)
    def test_sequential_competing_approvals_never_overspend(self):
        # Separate connections represent competing clients. BEGIN IMMEDIATE serializes the critical section.
        other=connect(self.path)
        try:
            for i in [1,6,11,16,21]:
                db=self.db if i%2 else other
                try:approve_plan(db,f'EMP-{i:06d}')
                except ValueError:pass
            self.assertGreaterEqual(budget_remaining(other,'Engineering'),0);self.assertTrue(validate(other)['passed'])
        finally:other.close()
    def test_concurrent_approvals_never_overspend(self):
        from concurrent.futures import ThreadPoolExecutor
        def worker(eid):
            c=connect(self.path)
            try:
                try:return approve_plan(c,eid)['plan_id']
                except ValueError:return 'no_feasible_path'
            finally:c.close()
        with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(worker,['EMP-000001','EMP-000006','EMP-000011']))
        self.assertEqual(len(results),3);self.assertTrue(validate(self.db)['passed']);self.assertGreaterEqual(budget_remaining(self.db,'Engineering'),0)
    def test_schedule_traceability(self):
        p=recommend(self.db,'EMP-000001');previous=AS_OF
        for c in p['courses']:
            self.assertGreaterEqual(c['planned_start'],previous);self.assertLessEqual(c['planned_finish'],p['period_end']);self.assertTrue(c['outcomes']);previous=c['planned_finish']
        self.assertEqual(previous,p['expected_finish'])
    def test_invalid_calendar_date(self):
        with self.assertRaises(ValueError):recommend(self.db,'EMP-000001',period_end='2027-02-30')
    def test_validator_independent_of_generator_expected_counts(self):
        self.db.execute("UPDATE completion SET completed_on='2025-01-01' WHERE rowid=1");self.db.commit()
        r=validate(self.db);self.assertFalse(r['passed']);self.assertFalse(next(x for x in r['checks'] if x['check']=='completion_date_order')['passed'])
    def test_counts(self):
        for t,n in [('employee',100),('skill',30),('course',60),('enrollment',200)]:self.assertEqual(self.db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0],n)
    def test_reproducible_exports(self):
        meta=generate(self.root/'other.db');export(self.path,self.root/'a',meta);export(self.root/'other.db',self.root/'b',meta)
        a=json.loads((self.root/'a/manifest.json').read_text());b=json.loads((self.root/'b/manifest.json').read_text());self.assertEqual(a,b)
    def test_different_seeds_differ(self):
        generate(self.root/'other.db',seed=1);self.assertNotEqual(self.path.read_bytes(),(self.root/'other.db').read_bytes())
    def test_recommendation_budget_and_hours(self):
        for i in range(1,21):
            p=recommend(self.db,f'EMP-{i:06d}');self.assertLessEqual(p['cost'],p['budget_remaining_before']);self.assertLessEqual(p['hours'],120);self.assertGreaterEqual(p['initial_gap'],p['projected_gap'])
    def test_prerequisites_ordered(self):
        p=recommend(self.db,'EMP-000001');done=completed_courses(self.db,'EMP-000001')
        for c in p['courses']:
            self.assertTrue(set(c['prerequisites'])<=done);done.add(c['id'])
    def test_no_recommendation_side_effect(self):
        self.db.commit();before=self.db.total_changes;recommend(self.db,'EMP-000001');self.assertEqual(before,self.db.total_changes)
    def test_no_ground_truth_in_planner(self):
        self.assertFalse(any('truth' in r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")))
    def test_completed_not_recommended(self):
        p=recommend(self.db,'EMP-000001');self.assertFalse({c['id'] for c in p['courses']}&completed_courses(self.db,'EMP-000001'))
    def test_unknown_employee(self):
        with self.assertRaises(ValueError):recommend(self.db,'BAD')
    def test_invalid_hours(self):
        with self.assertRaises(ValueError):recommend(self.db,'EMP-000001',hour_limit=0)
    def test_invalid_date(self):
        with self.assertRaises(ValueError):recommend(self.db,'EMP-000001',period_end='2020-01-01')
    def test_unknown_role(self):
        with self.assertRaises(ValueError):recommend(self.db,'EMP-000001','BAD')
    def test_zero_budget_blocks_paid_courses(self):
        dep='Engineering';spent=self.db.execute('SELECT SUM(cost) FROM enrollment WHERE budget_id=?',(f'BUD-{dep}-2026',)).fetchone()[0];self.db.execute('UPDATE budget SET amount=? WHERE department=?',(spent,dep));self.db.commit()
        p=recommend(self.db,'EMP-000001');self.assertEqual(p['cost'],0)
    def test_no_capacity_blocks(self):
        self.db.execute("UPDATE course SET capacity=1 WHERE id NOT IN (SELECT course_id FROM enrollment)")
        for r in rows(self.db,'SELECT course_id,COUNT(*) n FROM enrollment GROUP BY course_id'):self.db.execute('UPDATE course SET capacity=? WHERE id=?',(r['n'],r['course_id']))
        # Occupy unused courses so none has capacity.
        self.db.execute("UPDATE course SET available_from='2028-01-01',available_to='2029-01-01' WHERE id NOT IN(SELECT course_id FROM enrollment)");self.db.commit()
        self.assertEqual(recommend(self.db,'EMP-000001')['courses'],[])
    def test_unavailable_courses_excluded(self):
        self.db.execute("UPDATE course SET available_from='2028-01-01',available_to='2029-01-01'");self.db.commit();self.assertEqual(recommend(self.db,'EMP-000001')['courses'],[])
    def test_approval_is_traceable_and_reserves(self):
        before=self.db.execute('SELECT COUNT(*) FROM enrollment').fetchone()[0];p=approve_plan(self.db,'EMP-000001');self.assertEqual(self.db.execute('SELECT COUNT(*) FROM enrollment').fetchone()[0],before+len(p['courses']));self.assertEqual(self.db.execute('SELECT COUNT(*) FROM plan_event').fetchone()[0],2);self.assertTrue(validate(self.db)['passed'])
    def test_duplicate_completion_rejected(self):
        eid=self.db.execute('SELECT enrollment_id FROM completion LIMIT 1').fetchone()[0]
        with self.assertRaises(ValueError):record_completion(self.db,eid)
    def test_completion_does_not_change_skills(self):
        row=self.db.execute('SELECT e.* FROM enrollment e LEFT JOIN completion c ON c.enrollment_id=e.id WHERE c.id IS NULL LIMIT 1').fetchone();before=effective_levels(self.db,row['employee_id']);record_completion(self.db,row['id']);self.assertEqual(before,effective_levels(self.db,row['employee_id']))
    def test_reassessment_changes_observed_level(self):
        row=self.db.execute('SELECT c.id,e.employee_id,s.skill_id FROM completion c JOIN enrollment e ON e.id=c.enrollment_id JOIN course_skill s ON s.course_id=e.course_id LEFT JOIN reassessment r ON r.completion_id=c.id WHERE r.id IS NULL LIMIT 1').fetchone();reassess(self.db,row['id'],row['skill_id'],5);self.assertEqual(effective_levels(self.db,row['employee_id'])[row['skill_id']],5)
    def test_reassessment_wrong_skill(self):
        c=self.db.execute('SELECT id FROM completion LIMIT 1').fetchone()[0]
        with self.assertRaises(ValueError):reassess(self.db,c,'SKL-999999',3)
    def test_reassessment_invalid_level(self):
        with self.assertRaises(ValueError):reassess(self.db,'BAD','BAD',8)
    def test_foreign_key_enforcement(self):
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("INSERT INTO employee VALUES('BAD','X','BAD','X','2026-01-01')")
    def test_completion_uniqueness_constraint(self):
        r=self.db.execute('SELECT * FROM completion LIMIT 1').fetchone()
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('INSERT INTO completion VALUES(?,?,?)',('OTHER',r['enrollment_id'],r['completed_on']))
    def test_labelled_negative_scenarios(self):
        cases,truth=anomaly_cases()
        for c,t in zip(cases,truth):self.assertNotIn('expected',c);self.assertEqual(detect(c),t['expected'])
    def test_validator_catches_overbudget(self):
        self.db.execute('UPDATE budget SET amount=0');self.db.commit();r=validate(self.db);self.assertFalse(r['passed']);self.assertFalse(next(c for c in r['checks'] if c['check']=='budget_reconciliation')['passed'])
    def test_validator_catches_cost(self):
        self.db.execute('UPDATE enrollment SET cost=cost+1 WHERE rowid=1');self.db.commit();self.assertFalse(validate(self.db)['passed'])
    def test_career_path(self):
        p=recommend(self.db,'EMP-000001','ROL-000002');self.assertEqual(p['target_role_id'],'ROL-000002')
    def test_cancelled_completion_rejected(self):
        r=self.db.execute('SELECT e.id FROM enrollment e LEFT JOIN completion c ON c.enrollment_id=e.id WHERE c.id IS NULL LIMIT 1').fetchone()[0];self.db.execute('INSERT INTO enrollment_event VALUES(?,?,?,?)',('CANCEL',r,'cancelled',AS_OF));self.db.commit()
        with self.assertRaises(ValueError):record_completion(self.db,r)
    def test_cancelled_releases_budget(self):
        e=self.db.execute('SELECT * FROM enrollment WHERE cost>0 LIMIT 1').fetchone();dep=self.db.execute('SELECT department FROM employee WHERE id=?',(e['employee_id'],)).fetchone()[0];before=budget_remaining(self.db,dep);self.db.execute('INSERT INTO enrollment_event VALUES(?,?,?,?)',('CANCEL',e['id'],'cancelled',AS_OF));self.db.commit();self.assertEqual(budget_remaining(self.db,dep),before+e['cost'])

if __name__=='__main__':unittest.main()
