"""Audit a self-contained EPUB reader flow, not its article truthfulness."""
from __future__ import annotations

import json
import posixpath
import sys
from pathlib import PurePosixPath, Path
from urllib.parse import urlparse, unquote
from zipfile import ZipFile
from lxml import etree


def inspect(epub):
    issues=[]
    ids_by_path={}
    nav_links=[]
    resource_external=[]
    images=0
    sections=0
    with ZipFile(epub) as archive:
        paths=set(archive.namelist())
        pages=[p for p in paths if p.endswith((".xhtml",".html"))]
        for p in pages:
            doc=etree.fromstring(archive.read(p))
            ids_by_path[p]=set(doc.xpath("//@id"))
            content=archive.read(p).decode("utf-8")
            sections+=content.count("｜Executive Brief") + content.count("｜Sources &amp; Evidence")
            for element in doc.iter():
                tag=etree.QName(element.tag).localname if isinstance(element.tag,str) else ""
                if tag in ("img","image","link","script","audio","video","source"):
                    val=element.get("src") or element.get("href") or element.get("{http://www.w3.org/1999/xlink}href")
                    if val:
                        parts=urlparse(val)
                        if parts.scheme in ("https","http","data"):
                            resource_external.append((p,tag,val[:90]))
                if tag=="img":
                    images+=1
                if tag=="a":
                    href=element.get("href","")
                    if href.startswith("#") or (href and not urlparse(href).scheme):
                        nav_links.append((p,href))
        for page,href in nav_links:
            path,sep,fragment=href.partition("#")
            if not fragment:
                continue
            target=page if not path else posixpath.normpath(posixpath.join(posixpath.dirname(page),unquote(path)))
            # An EPUB conversion may place anchors on separate package pages;
            # every internal href must lead to an existing page/id.
            if target not in ids_by_path or unquote(fragment) not in ids_by_path[target]:
                issues.append(f"broken local link: {page} -> {href}")
        if not any(p.endswith(".css") for p in paths):
            issues.append("Missing embedded CSS")
        if not pages:
            issues.append("Missing XHTML content")
        if not nav_links:
            issues.append("No local in-book navigation")
        if not any("deep-research" in values for values in ids_by_path.values()):
            issues.append("Missing frozen deep-research section")
        for bad in resource_external:
            issues.append("Requires network media: "+" ".join(bad))
    return {
        "epub":str(epub),"pages":len(pages),"embedded_images":images,
        "local_links":len(nav_links),"resource_dependencies_on_network":len(resource_external),
        "offline_in_book_navigation":len(nav_links)>0 and not issues,
        "issues":issues
    }


def main():
    paths=[Path(x) for x in sys.argv[1:]]
    if not paths:
        raise SystemExit("Usage: python scripts/check_offline_package.py <file.epub> ...")
    results=[inspect(p) for p in paths]
    print(json.dumps(results,ensure_ascii=False,indent=2))
    if any(row["issues"] for row in results):
        raise SystemExit(4)


if __name__=="__main__":
    main()
