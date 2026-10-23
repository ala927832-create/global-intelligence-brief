"""BOOX Note Air4 C readable reflowable EPUB 3 output.

Palette uses restrained high-contrast colour and is readable in grayscale.
The cover is an offline generated bitmap; the body uses reflowable EPUB CSS.
No external font download, JavaScript, tracking, or remote resource is embedded.
"""
from __future__ import annotations

import datetime as dt
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ASSET_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'epub'
EPUB_CSS = ASSET_DIR / 'boox-air4c.css'
COVER_SIZE = (900, 1200)


def _font(size: int, bold: bool = False):
    fonts = [
        ('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc' if bold
         else '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold
        else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for font in fonts:
        if Path(font).exists():
            return ImageFont.truetype(font, size)
    return ImageFont.load_default()


def make_cover(path: Path, edition: str, level: str, date: str) -> None:
    """3:4 editorial cover inspired by approved layout 01 (no invented market data).

    Keep the cover a decorative preview; all substantive reading content is
    reflowable selectable text in the EPUB body.
    """
    w, h = COVER_SIZE  # 900 x 1200 = 3:4
    paper = '#FAF8F1'
    navy = '#203C56'
    ink = '#233642'
    teal = '#356F71'
    amber = '#9A722C'
    sage = '#E9EEE8'
    gray = '#546269'
    dimg = Image.new('RGB', (w,h), paper)
    d = ImageDraw.Draw(dimg)

    # Global masthead and simple line-globe logo.
    d.line([(50,48),(850,48)], fill='#AEB9B7', width=2)
    cx, cy, r = 103, 151, 49
    d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=navy,width=4)
    d.ellipse((cx-22,cy-r,cx+22,cy+r),outline=navy,width=2)
    d.line([(cx-r,cy),(cx+r,cy)],fill=navy,width=3)
    d.arc((cx-r,cy-r//2,cx+r,cy+r//2),0,180,fill=navy,width=2)
    d.arc((cx-r,cy-r//2,cx+r,cy+r//2),180,360,fill=navy,width=2)
    d.text((178,91),'Global',font=_font(56,True),fill=navy)
    d.text((178,155),'Intelligence Brief',font=_font(48,True),fill=navy)
    d.text((180,218),'全球情報簡報  ·  EVIDENCE / CONTEXT / INSIGHT',font=_font(23),fill=gray)
    d.line([(50,265),(850,265)], fill='#BAC4C2',width=2)

    tabs = [('全球政經','#DCE9EE'),('市場經濟','#E4EBE9'),('科技創新','#F3E9D5'),('社會與風險','#E9EDE1')]
    for i,(label,color) in enumerate(tabs):
        x=50+i*202
        d.rounded_rectangle((x,288,x+190,357),radius=9,fill=color)
        # typographic symbols replace color-only labels
        d.text((x+14,309),f'{i+1:02d}',font=_font(23,True),fill=navy if i<2 else amber)
        d.text((x+56,306),label,font=_font(24,True),fill=ink)
    d.line([(50,384),(850,384)],fill='#BBC7C4',width=2)

    # The body is a clean typographic edition identity, not fake news.
    morning=(edition=='morning')
    short=(level=='essential')
    kicker='MORNING  /  ESSENTIAL' if morning and short else (
           'MORNING  /  DEEP RESEARCH' if morning else (
           'EVENING  /  ESSENTIAL' if short else 'EVENING  /  DEEP RESEARCH'))
    d.rounded_rectangle((50,420,378,469),radius=6,fill=navy)
    d.text((67,430),kicker,font=_font(20,True),fill=paper)
    d.text((53,510),'全球財經'+('晨報' if morning else '晚報'),font=_font(84,True),fill=navy)
    d.text((53,627), '速讀精選' if short else '深度研究',font=_font(63,True),fill=teal)
    d.text((54,711),date,font=_font(43,True),fill=ink)
    d.line([(50,789),(850,789)],fill='#BAC4C2',width=2)

    # Key insight area echoes layout 1's sidebar, without invented quotes.
    d.rounded_rectangle((50,824,850,1027),radius=10,fill='#E6EFEB')
    d.text((78,850),'本期閱讀指南   /   KEY QUESTIONS',font=_font(24,True),fill=teal)
    for i,line in enumerate(['今天世界發生了什麼？','為什麼值得深入理解？','接下來應持續觀察什麼？']):
        y=894+i*40
        d.ellipse((77,y+3,104,y+30),fill=navy if i==0 else teal if i==1 else amber)
        d.text((84,y+3),str(i+1),font=_font(17,True),fill=paper)
        d.text((124,y),line,font=_font(28),fill=ink)
    d.text((53,1064),'BOOX NOTE AIR4 C   ·   RE-FLOWABLE EPUB 3',font=_font(22,True),fill=navy)
    d.text((53,1110),'適合電子墨水閱讀 · 暖白／深藍／青綠／琥珀',font=_font(20),fill=gray)
    d.line([(50,1152),(850,1152)],fill='#AEB9B7',width=2)
    path.parent.mkdir(parents=True,exist_ok=True)
    dimg.save(path,format='PNG',optimize=True)

def validate_epub(path: Path) -> None:
    """Lightweight structural sanity check; not a substitute for W3C EPUBCheck."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if not names or names[0] != 'mimetype' or z.read('mimetype') != b'application/epub+zip':
            raise ValueError('EPUB mimetype missing or out of order')
        container = ET.fromstring(z.read('META-INF/container.xml'))
        ns = '{urn:oasis:names:tc:opendocument:xmlns:container}'
        rootfile = container.find(f'.//{ns}rootfile')
        if rootfile is None: raise ValueError('EPUB package document missing')
        opf = ET.fromstring(z.read(rootfile.attrib['full-path']))
        pkg_ns = '{http://www.idpf.org/2007/opf}'
        manifest = opf.find(pkg_ns+'manifest')
        if manifest is None: raise ValueError('EPUB manifest missing')
        items = manifest.findall(pkg_ns+'item')
        if not any('nav' in x.get('properties','').split() for x in items):
            raise ValueError('EPUB 3 nav missing')
        if not any(x.get('media-type') == 'text/css' for x in items):
            raise ValueError('EPUB CSS missing')
        if not any(x.get('media-type') == 'image/png' for x in items):
            raise ValueError('EPUB cover missing')


def render_epub(markdown: Path, target: Path, edition: str, level: str, date: str,
                timeout_seconds: int = 90) -> None:
    if not shutil.which('pandoc'):
        raise RuntimeError('Pandoc is required for BOOX EPUB output')
    if not EPUB_CSS.is_file():
        raise FileNotFoundError(EPUB_CSS)
    kind = '晨報' if edition == 'morning' else '晚報'
    depth = '10–15 分鐘速讀' if level == 'essential' else '30–45 分鐘深度研究'
    title = f'Global Intelligence Brief｜{date}｜{kind}｜{depth}'
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gib-epub-') as temp:
        cover = Path(temp) / 'cover.png'
        tmpout = Path(temp) / 'brief.epub'
        make_cover(cover, edition, level, date)
        args = [
            'pandoc', str(markdown), '-f', 'markdown', '-t', 'epub3',
            '--standalone', '--toc', '--toc-depth=2', '--epub-chapter-level=2',
            '--css', str(EPUB_CSS), '--epub-cover-image', str(cover),
            '--metadata=lang:zh-TW', f'--metadata=title:{title}',
            '--metadata=author:Global Intelligence Brief',
            f'--metadata=date:{date}',
            '--metadata=description:全球重要新聞與證據導向研究；為彩色電子墨水閱讀器優化。',
            '-o', str(tmpout),
        ]
        subprocess.run(args, check=True, timeout=timeout_seconds,
                       capture_output=True, text=True)
        validate_epub(tmpout)
        shutil.copyfile(tmpout, target)
