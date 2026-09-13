# 文件名：make_q3_figures.py
# 用途：第三问全域最大水分浓度、时空场及径向剖面结果图绘图程序。

"""Q3: reproduce figures from saved formal solution and validation (no solver rerun)."""
from pathlib import Path
import os
import sys
import json
import types
ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'scripts/plotting/.mplconfig'))
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from cycler import cycler
try:
    import seaborn
except ModuleNotFoundError:
    fallback = types.ModuleType('seaborn')
    def set_theme(*, style='ticks', palette=None, font_scale=1, rc=None):
        if palette is not None: plt.rcParams['axes.prop_cycle'] = cycler(color=palette)
        if rc: plt.rcParams.update(rc)
    fallback.set_theme = set_theme
    sys.modules['seaborn'] = fallback
sys.path.insert(0,str(ROOT/'.agents/skills/mathmodel-figure/code/style'))
from plot_style import (COLOR_MAIN, COLOR_BASELINE, ACCENT_ORANGE, FIG_FULL,
                        FIG_TALL, FS_ANNOT, save_fig, style_axes, tint, add_panel_label)
OUT = ROOT/'figures/final/q3'
z = np.load(ROOT/'results/q3/q3_solution.npz')
v = json.loads((ROOT/'results/q3/q3_validation.json').read_text())
t = z['time_s']/3600
r = z['output_radii_m']*100
C = z['moisture_output']
cmax = z['cmax']
end = float(z['end_time_s'])/3600
threshold = float(v['formal']['end_max_moisture'])
assert C.shape == (len(t),len(r)) == (3432,21)
assert np.all(np.isfinite(C)) and np.all(np.diff(t)>0) and np.all(np.diff(r)>0)
assert np.allclose(C[0],2.55)
assert np.isclose(cmax[-1],threshold) and np.isclose(C[-1,0],threshold)
assert np.max(z['terminal_moisture']) <= threshold+1e-9
cmap = LinearSegmentedColormap.from_list('moisture',[COLOR_MAIN,tint(COLOR_MAIN,.92)])
norm = Normalize(float(C.min()),float(C.max()))
indices = [int(np.argmin(abs(t-x))) for x in (6,18,30,42)]+[len(t)-1]
labels = ['6 h','18 h','30 h','42 h',f'{end:.2f} h']

def criterion(ax):
    ax.plot(t,cmax,color=COLOR_MAIN)
    ax.axhline(threshold,color=COLOR_BASELINE,ls='--',lw=.8)
    ax.scatter([end],[threshold],color=ACCENT_ORANGE,zorder=4)
    ax.annotate(f'{end:.2f} h', (end,threshold),xytext=(-5,20),textcoords='offset points',ha='right',fontsize=FS_ANNOT,arrowprops={'arrowstyle':'-','color':ACCENT_ORANGE})
    ax.text(.97,.30,'Threshold = 0.15',transform=ax.transAxes,ha='right',fontsize=FS_ANNOT,color=COLOR_BASELINE)
    ax.set(xlabel='Time (h)',ylabel='Maximum moisture (kg/kg)',xlim=(0,60),ylim=(0,2.7),title='Termination criterion')
    style_axes(ax,grid='y')

def field(ax):
    mesh = ax.pcolormesh(t,r,C.T,shading='auto',cmap=cmap,norm=norm,rasterized=True)
    ax.contour(t,r,C.T,levels=[threshold],colors=[ACCENT_ORANGE],linewidths=.9)
    cb=ax.figure.colorbar(mesh,ax=ax,pad=.03,fraction=.045)
    cb.set_label('Moisture (kg/kg)')
    assert cb.mappable is mesh and cb.norm is mesh.norm and cb.cmap is mesh.cmap
    ax.set(xlabel='Time (h)',ylabel='Radius (cm)',xlim=(0,end),ylim=(0,2),title='Moisture field')
    ax.text(.97,.1,'Orange: C = 0.15',transform=ax.transAxes,ha='right',fontsize=FS_ANNOT,color=ACCENT_ORANGE)
    style_axes(ax,grid=None)

def profiles(ax):
    for i,(j,label) in enumerate(zip(indices,labels)):
        ax.plot(r,C[j],color=tint(COLOR_MAIN,.65*(1-i/4)),ls=['--','-.',':','--','-'][i],label=label)
    ax.axhline(threshold,color=COLOR_BASELINE,ls='--',lw=.8)
    ax.set(xlabel='Radius (cm)',ylabel='Moisture (kg/kg)',xlim=(0,2),ylim=(0,1.1),title='Radial profiles')
    ax.legend(frameon=False,fontsize=FS_ANNOT,loc='upper right')
    style_axes(ax,grid='y')

def sensitivity(ax):
    cases=v['cases']
    ambient=[.04986,cases['post_Ca_0.07']['options']['post_moisture']]
    times=[v['formal']['end_time_h'],cases['post_Ca_0.07']['end_time_h']]
    ax.scatter(ambient,times,color=COLOR_MAIN)
    for x,y in zip(ambient,times):
        ax.annotate(f'{y:.2f} h',(x,y),xytext=(0,8),textcoords='offset points',ha='center',fontsize=FS_ANNOT)
    ax.text(.03,.12,'$C_a=0.03$: discrete Robin roots\n/ branch fold; no unique $t_e$',transform=ax.transAxes,ha='left',fontsize=FS_ANNOT,color=ACCENT_ORANGE)
    ax.set(xlabel='Ambient moisture after 4 h (kg/kg)',ylabel='Termination time (h)',xlim=(.025,.076),ylim=(0,112),title='Boundary-condition scenarios')
    ax.set_xticks([.030,.04986,.070], ['0.030','0.04986','0.070'])
    style_axes(ax,grid='y')

def save(fig,stem):
    save_fig(fig,str(OUT/f'{stem}.png'),close=False)
    for ext in ('pdf','svg'): fig.savefig(OUT/f'{stem}.{ext}',bbox_inches='tight',pad_inches=.1)
    plt.close(fig)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    # Explicitly requested cleanup, scoped to Q3 rendered figures only.
    old=[p for p in OUT.iterdir() if p.is_file() and p.suffix in ('.png','.pdf','.svg')]
    for p in old: p.unlink()
    drawers=[criterion,field,profiles,sensitivity]
    fig,axes=plt.subplots(2,2,figsize=(FIG_FULL[0]*2,FIG_TALL[1]*1.35),layout='constrained')
    for tag,ax,draw in zip('abcd',axes.flat,drawers):
        draw(ax); add_panel_label(ax,tag)
    save(fig,'q3_summary')
    for name,draw in zip(('q3_cmax_threshold','q3_spatiotemporal_field','q3_moisture_profiles','q3_ambient_sensitivity'),drawers):
        fig,ax=plt.subplots(figsize=FIG_FULL,layout='constrained')
        draw(ax); save(fig,name)
    print(f'Replaced {len(old)} old files; generated 15 files. Shape: {C.shape}; end: {end:.8f} h')
    print('Terminal C at r=0,1,2 cm:',C[-1,[0,10,20]])
if __name__=='__main__': main()
