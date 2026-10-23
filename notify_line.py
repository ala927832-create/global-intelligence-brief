"""Optional one LINE text per edition; no trade alerts and no payment fallback."""
import json
import os
from pathlib import Path
import requests
import time

def send():
    if os.environ.get('ENABLE_LINE')!='1':
        print('LINE disabled; no message sent')
        return
    token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    user=os.getenv('LINE_USER_ID')
    if not token or not user:
        print('LINE secrets not configured; no message sent')
        return
    d=json.loads((Path(__file__).parent/'data'/'last_run.json').read_text(encoding='utf-8'))
    label='晨報' if d['edition']=='morning' else '晚報'
    lines=[f'Global Intelligence {label}｜{d["date"]}']
    for a in d['events'][:3]: lines.append('• '+a['title'][:150])
    if not d['events']:lines.append('本期未找到足夠新增且可追溯來源的事件，不重複轉載舊聞。')
    base=os.getenv('PUBLIC_REPORT_BASE_URL','').rstrip('/')
    if base.startswith('https://'):
        links=[f'{base}/archive/{d["date"]}/{d["edition"]}-{level}.html' for level in ('essential','deep')]
        ebooks=[f'{base}/archive/{d["date"]}/{d["edition"]}-{level}.epub' for level in ('essential','deep')]
        ok=False
        for attempt in range(3):
            try:
                statuses=[requests.get(url,timeout=10).status_code==200 for url in links]
                if all(statuses): ok=True;break
            except requests.RequestException: pass
            if attempt<2: time.sleep(5)
        if ok:
            lines += ['速讀：'+links[0],'深讀：'+links[1]]
            try:
                epub_ok=[]
                for url in ebooks:
                    with requests.get(url,timeout=10,stream=True) as response:
                        epub_ok.append(response.status_code==200)
                if all(epub_ok):
                    lines += ['BOOX 速讀 EPUB：'+ebooks[0], 'BOOX 深讀 EPUB：'+ebooks[1]]
            except requests.RequestException:
                pass
        else: lines.append('閱讀版尚未確認完成部署；請稍後由晨報首頁查看。')
    lines.append('本訊息僅全球新聞；Zinc 特定市場警示依原系統另行通知。')
    msg='\n'.join(lines)[:4500]
    response=requests.post('https://api.line.me/v2/bot/message/push',
        headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'},
        json={'to':user,'messages':[{'type':'text','text':msg}]},timeout=20)
    response.raise_for_status()
    print('LINE delivered (API accepted response)')

if __name__=='__main__':send()
