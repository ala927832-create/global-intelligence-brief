import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gib.qa_tracker import rollup
p=argparse.ArgumentParser();p.add_argument('--folder',default='qa_data/records');p.add_argument('--boox-real-pass',action='store_true');p.add_argument('--owner-approved',action='store_true');args=p.parse_args()
print(json.dumps(rollup(args.folder,device_signoff=args.boox_real_pass,owner_release_approval=args.owner_approved),ensure_ascii=False,indent=2))
