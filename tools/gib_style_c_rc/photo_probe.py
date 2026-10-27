"""Network-side Commons photo readiness gate. QA-only: no publication actions."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.gib_style_c_rc.live_html_qa import PHOTOS, get_photo

def run(out:Path, strict:bool):
    out.mkdir(parents=True,exist_ok=True)
    images=out/"image_cache";records=[];figs=[]
    for item in PHOTOS:
        data,status=get_photo(item,images,True)
        records.append(status)
        if data:
            figs.append(f'<figure><img alt="Historical context: {item["id"]}" src="{data}"><figcaption>'
                        f'Context photo, NOT same-day coverage · {item["author"]} · {item["date"]} · '
                        f'{item["licence"]} · <a href="{item["page"]}">Original / licence</a></figcaption></figure>')
    ok=sum(bool(x.get("embedded_sha256")) for x in records)
    result={"embedded_photos":ok,"required_photos":len(PHOTOS),"photo_gate_pass":ok==len(PHOTOS),
            "editorial_release_approved":False,"photos":records}
    (out/"photo_readiness.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    page='<!doctype html><html lang="en"><head><meta charset="utf-8"><title>GIB licensed context photo QA</title><style>body{font:16px Georgia;background:#faf5eb;color:#172e42;max-width:1000px;margin:25px auto}figure{margin:24px 0;padding:18px;border:1px solid #ccd}img{max-width:100%;max-height:360px}figcaption{font-size:12px}h1{font-size:32px}</style></head><body><h1>GIB Photo QA · No published edition</h1><p>Verified decodable bytes: '+str(ok)+'/3. Context photographs, not live news imagery.</p>'+''.join(figs)+'</body></html>'
    (out/"photo_embedded_preview.html").write_text(page,encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    return ok==len(PHOTOS) or not strict

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="qa_outputs/consolidated_photo_gate")
    p.add_argument("--strict",action="store_true")
    a=p.parse_args();sys.exit(0 if run(Path(a.out),a.strict) else 1)
