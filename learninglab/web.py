import json
import sqlite3
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from .core import connect,rows,recommend,validate,approve_plan,record_completion,reassess

PAGE=Path(__file__).with_name('index.html')
def serve(dbpath,port,host='127.0.0.1'):
    class Handler(BaseHTTPRequestHandler):
        def reply(self,value,status=200):
            raw=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            p=urlparse(self.path);q=parse_qs(p.query)
            if p.path=='/':
                raw=PAGE.read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(raw);return
            db=connect(dbpath)
            try:
                if p.path=='/api/summary':self.reply({'validation':validate(db),'budgets':rows(db,'SELECT department,amount FROM budget ORDER BY department'),'roles':rows(db,'SELECT * FROM role ORDER BY id'),'career_paths':rows(db,'SELECT * FROM career_path ORDER BY id')})
                elif p.path=='/api/employees':
                    term=q.get('q',[''])[0][:80]
                    self.reply(rows(db,'SELECT e.*,r.name role FROM employee e JOIN role r ON r.id=e.role_id WHERE e.id LIKE ? OR e.name LIKE ? ORDER BY e.id LIMIT 40',('%'+term+'%','%'+term+'%')))
                elif p.path=='/api/plan':self.reply(recommend(db,q.get('employee',['EMP-000001'])[0],q.get('role',[None])[0] or None,int(q.get('hours',['120'])[0]),q.get('end',['2027-03-31'])[0]))
                elif p.path=='/api/history':
                    eid=q.get('employee',['EMP-000001'])[0]
                    self.reply({'enrollments':rows(db,'SELECT e.*,v.state,v.occurred_on FROM enrollment e JOIN enrollment_event v ON v.enrollment_id=e.id WHERE e.employee_id=? ORDER BY v.occurred_on,v.id',(eid,)),'completions':rows(db,'SELECT c.* FROM completion c JOIN enrollment e ON e.id=c.enrollment_id WHERE e.employee_id=? ORDER BY c.id',(eid,)),'reassessments':rows(db,'SELECT * FROM reassessment WHERE employee_id=? ORDER BY assessed_on,id',(eid,))})
                else:self.reply({'error':'Not found'},404)
            except (ValueError,sqlite3.Error) as exc:self.reply({'error':str(exc)},400)
            finally:db.close()
        def do_POST(self):
            # Same-origin mutations only, with bounded JSON input. The origin's
            # host must match the Host header, so this holds on loopback and on a
            # hosted demo domain alike.
            origin = self.headers.get('Origin')
            if origin is not None and urlparse(origin).netloc != self.headers.get('Host',''):
                self.reply({'error':'Cross-origin request rejected'},403);return
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':self.reply({'error':'JSON required'},415);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=10000:raise ValueError('Invalid request size')
                body=json.loads(self.rfile.read(length));db=connect(dbpath)
                try:
                    if self.path=='/api/approve':result=approve_plan(db,body['employee'],body.get('role') or None,int(body.get('hours',120)),body.get('end','2027-03-31'))
                    elif self.path=='/api/complete':result={'completion_id':record_completion(db,body['enrollment_id'])}
                    elif self.path=='/api/reassess':result={'reassessment_id':reassess(db,body['completion_id'],body['skill_id'],body['level'])}
                    else:self.reply({'error':'Not found'},404);return
                    self.reply(result,201)
                finally:db.close()
            except (ValueError,KeyError,sqlite3.Error) as exc:self.reply({'error':str(exc)},400)
    print(f'Learning Path Lab: http://{host}:{port} (synthetic demo, no authentication)')
    ThreadingHTTPServer((host,port),Handler).serve_forever()
