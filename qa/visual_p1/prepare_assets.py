"""P1 only: retrieve licensed historical documentary photographs for QA.
No edits to published issues, no fabricated event photography, no publication.
"""
from pathlib import Path
from urllib.parse import urlparse
from hashlib import sha256
import json,io,html
import requests
from PIL import Image,ImageOps
ROOT=Path("qa_out/p1_visual")
MANIFEST=Path("qa/visual_p1/assets_manifest.json")
def main():
 manifest=json.loads(MANIFEST.read_text())
 assert manifest["release"]=="OFF"
 assert len(manifest["images"])==3 and len(manifest["charts"])==4
 ROOT.mkdir(parents=True,exist_ok=True)
 assets=ROOT/"images";assets.mkdir(exist_ok=True)
 items=[]
 for photo in manifest["images"]:
  assert photo["rights_status"]=="SOURCE_LICENSE_VERIFIED"
  assert photo["license"] in ("US-GOV-PUBLIC-DOMAIN","UNSPLASH")
  assert photo["date"]<"2026-10-30", "Cannot imply future photo was historic"
  assert urlparse(photo["download_url"]).hostname in ("d1ldvf68ux039x.cloudfront.net","images.unsplash.com")
  assert urlparse(photo["source_page"]).hostname in ("www.dvidshub.net","unsplash.com")
  assert any(x in photo["caption_zh"] for x in ("資料照片","背景照片","歷史"))
  assert "非" in photo["caption_zh"]
  response=requests.get(photo["download_url"],timeout=(12,60),
     headers={"User-Agent":"GIB-QA-PhotoRights/1.0 (offline editorial validation)"})
  response.raise_for_status()
  assert urlparse(response.url).hostname in ("d1ldvf68ux039x.cloudfront.net","images.unsplash.com")
  assert len(response.content)>10000 and len(response.content)<16_000_000
  assert response.headers.get("content-type","").lower().startswith("image/")
  im=Image.open(io.BytesIO(response.content)); im.load()
  assert im.width>=750 and im.height>=600
  with (assets/photo["file"]).open("wb") as fh: fh.write(response.content)
  optimized=ImageOps.exif_transpose(im).convert("RGB")
  optimized.thumbnail((1280,1280),Image.Resampling.LANCZOS)
  output=assets/(photo["id"]+".jpg")
  optimized.save(output,format="JPEG",quality=86,optimize=True)
  grey=ImageOps.grayscale(optimized).convert("RGB")
  grey.save(assets/(photo["id"]+"_gray.jpg"),quality=82,optimize=True)
  items.append({**photo,"sha256_source":sha256(response.content).hexdigest(),
    "sha256_optimized":sha256(output.read_bytes()).hexdigest(),
    "original_width":im.width,"original_height":im.height,
    "boox_color_width":optimized.width,"boox_color_height":optimized.height,
    "original_bytes":len(response.content),
    "optimized_bytes":output.stat().st_size,"locally_acquired":True,
    "derivative_note":"Reduced resolution / recompressed; no fabricated objects or altered events"})
 manifest["image_processing"]=items
 manifest["all_background_photos_verified"]=len(items)==3
 manifest["cover_photo_pass"]=manifest.get("cover_image_status")=="PASS_EVENT_SPECIFIC_LICENSED_PHOTO"
 manifest["p1_acquisition_pass"]=len(items)==3 and manifest["cover_photo_pass"]
 manifest["p1_overall"]="PASS" if manifest["p1_acquisition_pass"] else "HOLD"
 (ROOT/"provenance.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
 page=['<!DOCTYPE html><html lang="zh-Hant"><meta charset="UTF-8">',
 '<meta name="viewport" content="width=device-width,initial-scale=1">',
 '<title>GIB P1 | Photo rights and BOOX QA</title>',
 '<style>body{background:#faf8f2;color:#24333d;max-width:880px;margin:0 auto;padding:24px;font-family:system-ui,sans-serif;line-height:1.65}h1,h2{color:#142d46}.eyebrow{font-size:12px;color:#285c6e;letter-spacing:.13em;font-weight:700}.photo{border-top:2px solid #17354d;margin-top:30px;padding-top:16px}img{display:block;width:100%;height:auto;border-radius:4px}figcaption{font-size:13px;color:#4e6067;margin-top:8px}a{overflow-wrap:anywhere;color:#1c5967}.meta{font-size:13px;color:#42535d}.notice{background:#ece8df;border-left:4px solid #a47722;padding:12px}</style>',
 '<div class="eyebrow">GLOBAL INTELLIGENCE BRIEF · QA ONLY</div>',
 '<h1>P1 真實新聞影像素材｜版權與圖說審查</h1>',
 '<p class="notice">歷史／背景照片，不是 2026-10-30 報導的現場；未修改已核准新聞正文與凍結 Style C。正式發刊維持 OFF。</p>']
 for idx,item in enumerate(items,1):
  page.extend(['<section class="photo"><div class="eyebrow">PHOTO '+str(idx).zfill(2)+'</div>',
  '<figure><img loading="lazy" src="images/'+html.escape(item["id"])+'.jpg" alt="'+html.escape(item["caption_zh"])+'">',
  '<figcaption>'+html.escape(item["caption_zh"])+'</figcaption></figure>',
  '<p class="meta">攝影／來源：'+html.escape(item["creator"])+' · 日期：'+item["date"]+' · 授權：<a href="'+item["license_url"]+'">'+html.escape(item["license"])+'</a> · <a href="'+html.escape(item["source_page"],quote=True)+'">原始圖片與授權頁</a></p>',
  '<p class="meta">影像已轉為 BOOX 友善尺寸；<a href="images/'+item["id"]+'_gray.jpg">灰階版本</a>。附來源圖片 SHA-256。</p></section>'])
 page.extend(['<h2>採用的四種圖表</h2><p>本批僅確認資料規格與來源，尚未生成任何沒有數據支持的圖表。</p><ul>'])
 for c in manifest["charts"]: page.append('<li>'+c["id"]+' · '+html.escape(c["name"])+'（'+c["phase"]+'）</li>')
 page.append('</ul></html>')
 (ROOT/"P1_photo_license_preview.html").write_text("\n".join(page),encoding="utf-8")
 print(json.dumps({"image_count":len(items),"chart_specs":4,
   "status":manifest["p1_overall"],"cover_photo_pass":manifest["cover_photo_pass"],"publication":"OFF"},ensure_ascii=False))
 if not manifest["p1_acquisition_pass"]:
  raise SystemExit("P1_HOLD_EVENT_SPECIFIC_LICENSED_COVER_REQUIRED_NO_P2")
if __name__=="__main__": main()
