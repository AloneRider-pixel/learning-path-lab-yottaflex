"""Regenerate two full datasets and compare all ordered-export hashes."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from learninglab.core import generate,export
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);manifests=[];counts=[]
    for run in ['one','two']:
        db=root/(run+'.sqlite');meta=generate(db,'full',20261022);report=export(db,root/run,meta);assert report['passed'];counts.append(report['row_counts']);manifests.append(json.loads((root/run/'manifest.json').read_text()))
    result={'same_seed':20261022,'all_checksums_match':manifests[0]['checksums']==manifests[1]['checksums'],'row_counts_match':counts[0]==counts[1],'files_compared':len(manifests[0]['checksums']),'row_counts':counts[0]}
    print(json.dumps(result,indent=2));assert result['all_checksums_match'] and result['row_counts_match']
