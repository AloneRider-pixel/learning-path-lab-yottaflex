import argparse
import json
from pathlib import Path
from .core import connect,generate,export,recommend,validate

def main():
    p=argparse.ArgumentParser(description='Reproducible learning-path lab')
    p.add_argument('--db',default='data/lab.sqlite')
    s=p.add_subparsers(dest='command',required=True)
    g=s.add_parser('generate');g.add_argument('--scale',choices=['starter','full'],default='starter');g.add_argument('--seed',type=int,default=20261022);g.add_argument('--out',default='data/export');g.add_argument('--force',action='store_true',help='Replace existing generated database')
    s.add_parser('validate')
    r=s.add_parser('recommend');r.add_argument('employee');r.add_argument('--target-role');r.add_argument('--hours',type=int,default=120);r.add_argument('--period-end',default='2027-03-31')
    v=s.add_parser('serve');v.add_argument('--port',type=int,default=8765);v.add_argument('--host',default='127.0.0.1',help='Bind address; keep the loopback default unless hosting the demo')
    args=p.parse_args()
    if args.command=='generate':
        if Path(args.db).exists() and not args.force:p.error('Database exists. Use --force to regenerate, or choose --db.')
        meta=generate(args.db,args.scale,args.seed);result=export(args.db,args.out,meta);print(json.dumps(result,indent=2));return
    if args.command=='serve':
        from .web import serve
        serve(args.db,args.port,args.host);return
    db=connect(args.db)
    try:result=validate(db) if args.command=='validate' else recommend(db,args.employee,args.target_role,args.hours,args.period_end)
    finally:db.close()
    print(json.dumps(result,indent=2))
    if args.command=='validate' and not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
