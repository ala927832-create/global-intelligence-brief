"""Build source-backed, human-curated sample issue. Never used as live news."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from gib.editorial_rebuild import export_packet
from gib.quality_gate import report_checks,write_report
ROOT=Path(__file__).resolve().parent
AS=ROOT/'assets'/'editorial'
AS.mkdir(parents=True,exist_ok=True)
# Use local CJK font, do not bundle/share font files.
cjk='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if Path(cjk).exists():
    font_manager.fontManager.addfont(cjk)
    family=font_manager.FontProperties(fname=cjk).get_name()
    plt.rcParams['font.family']=family
plt.rcParams['axes.unicode_minus']=False
plt.rcParams['font.size']=12
paper='#FAF8F1'; navy='#1B344C'; teal='#2C6F73';amber='#A27420'; graph='#AEC2C1'
fig,ax=plt.subplots(figsize=(9.3,4.5),dpi=160)
fig.patch.set_facecolor(paper);ax.set_facecolor(paper)
y=[3.1,3.4]; x=[0,1]; ax.bar([-.13,.87],y,width=.27,color=navy,label='實質 GDP 成長 (%)')
ax.bar([.17,1.17],[4.7,4.1],width=.27,color=teal,label='整體通膨 (%)')
for xpos,val in [(-.13,3.1),(.87,3.4),(.17,4.7),(1.17,4.1)]:ax.text(xpos,val+.12,f'{val:.1f}%',ha='center',color=navy,fontweight='bold',fontsize=12)
ax.set_xticks([0,1],['2026（預測）','2027（預測）']);ax.set_ylim(0,5.6);ax.set_yticks([0,2,4]); ax.grid(axis='y',color=graph,alpha=.5)
for s in ax.spines.values():s.set_visible(False)
ax.set_axisbelow(True);ax.legend(frameon=False,ncol=2,loc='upper center',bbox_to_anchor=(.5,1.14),fontsize=11)
fig.text(.10,.99,'IMF 2026 年 10 月 WEO｜全球預測',ha='left',va='top',fontsize=16,color=navy,fontweight='bold')
fig.tight_layout(rect=[0,.02,1,.87]);fig.savefig(AS/'weo-2026-outlook.png',dpi=160,facecolor=paper,bbox_inches='tight');plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(9.3,4.8),dpi=160);fig.patch.set_facecolor(paper)
for ax in axes:ax.set_facecolor(paper); ax.grid(axis='y',color=graph,alpha=.4);ax.set_axisbelow(True);[s.set_visible(False) for s in ax.spines.values()]
axes[0].bar([0,1],[.6,3.7],color=[teal,navy],width=.55)
axes[0].set_xticks([0,1],['月增（季調）','年增（未季調）']);axes[0].set_title('整體 CPI：不同期間',color=navy,fontsize=13)
for i,v in enumerate([.6,3.7]):axes[0].text(i,v+.12,f'{v}%',ha='center',color=navy,fontweight='bold')
axes[0].set_ylim(0,5)
axes[1].bar([0,1],[9.1,5.2],color=[amber,teal],width=.55)
axes[1].set_xticks([0,1],['汽油','能源']);axes[1].set_title('分類價格：9 月月增',color=navy,fontsize=13)
for i,v in enumerate([9.1,5.2]):axes[1].text(i,v+.17,f'{v}%',ha='center',color=navy,fontweight='bold')
axes[1].set_ylim(0,11)
fig.suptitle('BLS｜2026 年 9 月美國 CPI',fontsize=16,color=navy,fontweight='bold',y=1.0)
fig.tight_layout(rect=[0,0,1,.92]);fig.savefig(AS/'us-cpi-sep2026.png',dpi=160,facecolor=paper,bbox_inches='tight');plt.close(fig)

packet=json.loads((ROOT/'samples'/'official_research_2026-10-23.json').read_text())
res=export_packet(packet,root=ROOT,edition='morning',validate_deep_min=7500)
quality=report_checks(packet,res,ROOT)
write_report(quality,ROOT/'reports'/packet['date']/'EDITORIAL_QUALITY_REPORT.json')
if not quality['all_passed']:
    raise SystemExit('QUALITY_HOLD: '+str([x for x in quality['checks'] if not x['passed']]))
print(json.dumps({'output':res,'quality_passed':quality['passed'],'quality_total':quality['total']},ensure_ascii=False,indent=2))
