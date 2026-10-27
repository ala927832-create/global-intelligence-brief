"""Fail-closed HTML QA checks, not fact certification."""
import hashlib,json,sys
from html.parser import HTMLParser
from pathlib import Path
class Markup(HTMLParser):
 def __init__(self):
  super().__init__();self.ids=set();self.anchors=[];self.images=[]
 def handle_starttag(self,tag,attrs):
  x=dict(attrs)
  if x.get("id"):self.ids.add(x["id"])
  if tag=="a" and x.get("href","").startswith("#"):self.anchors.append(x["href"][1:])
  if tag=="img":self.images.append(x.get("src",""))
def check(folder):
 root=Path(folder);qa=json.loads((root/"qa_report.json").read_text(encoding="utf-8"))
 page=(root/("morning.html" if qa.get("edition")=="morning" else "evening.html")).read_text(encoding="utf-8")
 html=Markup();html.feed(page);err=[]
 if any(x and x not in html.ids for x in html.anchors):err.append("BROKEN_LINK")
 if any(not x.startswith("data:image/") for x in html.images):err.append("NON_OFFLINE_IMAGE")
 if page.lower().count("<!doctype html>")!=1:err.append("DOCTYPE")
 if qa.get("html_sha256")!=hashlib.sha256(page.encode()).hexdigest():err.append("HASH")
 if qa.get("release_approved") is not False:err.append("RELEASE_FLAG")
 if not (root/"issue.json").is_file() or not (root/"source_packet.json").is_file():err.append("MISSING_SOURCE_FILES")
 print(json.dumps({"pass":not err,"problems":err,"release_approved":False},ensure_ascii=False))
 return not err
if __name__=="__main__":sys.exit(0 if check(sys.argv[1]) else 1)
