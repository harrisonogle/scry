"""Replay a recorded search against a copy of a run's index (lexical, no model). Usage: replay.py <run dir> <query> [level]"""
import sys, shutil, json, os, hashlib
from pathlib import Path
from scry.index import open_db, search as index_search, get_embedder
from scry.ask import hit_summary
from scry.config import load_config
SP=Path(os.path.dirname(__file__))
run=Path(sys.argv[1]); q=sys.argv[2]; level=sys.argv[3] if len(sys.argv)>3 else None
dst=SP/'dbs'/(hashlib.sha1(str(run).encode()).hexdigest()[:10]+'.sqlite')
if not dst.exists(): shutil.copy(run/'index.sqlite',dst)
cfg=load_config(None)
db=open_db(dst)
hits=index_search(db,q,cfg.index,get_embedder(cfg.index),level=level)
for i,h in enumerate(hits,1):
    s=hit_summary(h)
    print(i,s['node_id'],s['level'],s['frames'],'|',json.dumps(s.get('text'),ensure_ascii=False)[:int(os.environ.get('W','300'))], '| ent=%r sub=%r'%(s.get('entered_text'),s.get('submitted')) if s['level']=='transition' else '')
