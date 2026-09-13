from pathlib import Path
import os, sys
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parents[1]/'.mplconfig'))
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle, Arc
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'.agents/skills/mathmodel-figure/code/style'))
try:
 import seaborn
except ModuleNotFoundError:
 import types
 seaborn=types.ModuleType('seaborn'); seaborn.set_theme=lambda *a,**k: None; sys.modules['seaborn']=seaborn
from plot_style import COLOR_MAIN, COLOR_MAIN_LIGHT, COLOR_BASELINE, COLOR_BASELINE_DARK, ACCENT_ORANGE, COLOR_INK, FIG_TALL, save_fig
OUT=ROOT/'figures/final/model_mechanism_schematic'; OUT.parent.mkdir(parents=True,exist_ok=True)
plt.rcParams['font.family']='DejaVu Sans'; plt.rcParams['font.size']=9
fig=plt.figure(figsize=(8.2,5.3), constrained_layout=True)
gs=fig.add_gridspec(1,2,width_ratios=[1.65,1],wspace=.3)
ax=fig.add_subplot(gs[0,0]); ax.set_aspect('equal'); ax.axis('off'); ax.set_xlim(-3.3,3.3); ax.set_ylim(-3.0,3.1)
# air region and cylinder
ax.add_patch(Rectangle((-3.1,-2.6),6.2,5.2,facecolor='#F7F9FC',edgecolor='none',zorder=0))
ax.add_patch(Circle((0,0),2.0,facecolor='#EAF2FB',edgecolor=COLOR_MAIN,lw=2.0,zorder=2))
ax.add_patch(Circle((0,0),1.2,facecolor='#DCEBFA',edgecolor=ACCENT_ORANGE,lw=1.6,ls='--',zorder=3))
# radial moisture gradient bands
for rad,alpha in [(1.8,.08),(1.55,.07),(1.3,.06)]: ax.add_patch(Circle((0,0),rad,facecolor=COLOR_MAIN,edgecolor='none',alpha=alpha,zorder=2))
# axis and radius
ax.plot([0,0],[0,2],color=COLOR_BASELINE_DARK,lw=.8,ls=':'); ax.text(.08,.1,'r = 0',color=COLOR_BASELINE_DARK)
ax.add_patch(FancyArrowPatch((0,-.25),(1.98,-.25),arrowstyle='<->',mutation_scale=12,color=COLOR_BASELINE_DARK,lw=.9)); ax.text(1,-.48,'R(t)',ha='center',color=COLOR_BASELINE_DARK)
# heat arrows inward
for x in [-2.75,-2.35,2.35,2.75]:
 ax.add_patch(FancyArrowPatch((x,2.65 if x<0 else -2.65),(x*.72,1.85 if x<0 else -1.85),arrowstyle='-|>',mutation_scale=12,color=ACCENT_ORANGE,lw=1.5))
ax.text(0,2.78,'Hot drying air',ha='center',color=ACCENT_ORANGE,weight='bold')
# moisture arrows outward
for ang in np.linspace(25,155,5):
 th=np.deg2rad(ang); p1=(1.0*np.cos(th),1.0*np.sin(th)); p2=(2.35*np.cos(th),2.35*np.sin(th))
 ax.add_patch(FancyArrowPatch(p1,p2,arrowstyle='-|>',mutation_scale=11,color=COLOR_MAIN,lw=1.3))
ax.text(-2.95,-2.85,'Moisture diffusion to surface',color=COLOR_MAIN)
# labels
ax.text(0,0.35,'Moisture-rich\ninterior',ha='center',color=COLOR_MAIN,weight='bold')
ax.text(1.3,1.6,'Moving\nsurface',ha='center',color=ACCENT_ORANGE)
ax.text(-2.9,1.7,'Heat\nconvection',color=ACCENT_ORANGE,ha='center')
ax.text(0,-2.95,'(a) Radial heat and moisture transfer',ha='center',weight='bold',color=COLOR_INK)
# right explanatory panel
bx=fig.add_subplot(gs[0,1]); bx.axis('off'); bx.set_xlim(0,1); bx.set_ylim(0,1)
bx.text(.02,.96,'Model variables',fontsize=11,weight='bold',color=COLOR_INK,va='top')
items=[('Temperature','T(r,t)',ACCENT_ORANGE),('Moisture concentration','C(r,t)',COLOR_MAIN),('Moving radius','R(t)',COLOR_BASELINE_DARK),('Termination rule','max C ≤ 0.15',COLOR_BASELINE_DARK)]
for i,(name,sym,col) in enumerate(items):
 y=.83-i*.12; bx.add_patch(Rectangle((.03,y-.025),.055,.05,facecolor=col,alpha=.9)); bx.text(.12,y,name,color=COLOR_INK,va='center'); bx.text(.92,y,sym,color=col,ha='right',va='center',weight='bold')
# profile inset axes-like drawing
bx.text(.02,.37,'Radial profile',fontsize=10,weight='bold',color=COLOR_INK)
xx=np.linspace(0,1,100); yy=.28+.12*(1-xx**1.8)
bx.plot(.08+.82*xx,.15+.16*(1-xx**1.8),color=COLOR_MAIN,lw=2); bx.axhline(.28,color=COLOR_BASELINE,ls='--',lw=.8); bx.text(.92,.175,'C = 0.15',ha='right',va='bottom',fontsize=8,color=COLOR_BASELINE)
bx.set_xlim(0,1); bx.set_ylim(0,1)
bx.annotate('axis',(.08,.15),xytext=(.08,.09),ha='center',arrowprops={'arrowstyle':'-','color':COLOR_BASELINE_DARK},fontsize=8)
bx.annotate('surface',(.90,.15),xytext=(.90,.09),ha='center',arrowprops={'arrowstyle':'-','color':COLOR_BASELINE_DARK},fontsize=8)
bx.text(.5,.025,'(b) State variables and threshold',ha='center',weight='bold',color=COLOR_INK)
for ext in ['png','pdf','svg']:
 path=OUT.with_suffix('.'+ext)
 if ext=='png': save_fig(fig,str(path),close=False,dpi=300)
 else: fig.savefig(path,bbox_inches='tight',pad_inches=.1)
plt.close(fig)
print(OUT)
