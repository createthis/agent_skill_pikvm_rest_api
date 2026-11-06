#!/usr/bin/env python3
"""Generate the eight reproducible PiKVM computer-use teaching diagrams.

The figures illustrate how an agent uses the ../pikvm-rest-api skill end to
end; every screen and number is deliberately simulated, no PiKVM is contacted.
They back the human-facing walkthrough in the repo root README.md.

Requirements: Python 3, matplotlib, pillow (numpy ships with matplotlib).
  python -m pip install matplotlib pillow
  python docs/generate_pikvm_diagrams.py --output-dir docs/figures

Functions make01..make08 produce one step each; PNG (2080x1170) and SVG are
written per step. docs/critic_checks.py re-verifies geometry, math, and
contrast after a regeneration.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch, Circle

# Consistent high-contrast editorial design, tuned for 16:9 university slides.
NAVY = '#14273C'
TEXT = '#243447'
MUTED = '#526579'
BLUE = '#245FA0'
TEAL = '#066B66'
GOLD = '#8E5100'
RED = '#AD3D39'
PAPER = '#FFFFFF'
PALE = '#F3F7FA'
LIGHTBLUE = '#E9F2FC'
LIGHTTEAL = '#E7F5F2'
LIGHTGOLD = '#FFF5E4'
LIGHTRED = '#FDEEEE'
LINE = '#CFDAE4'

W, H = 1920, 1200
TARGET = (1440, 900)
CROP = (1340, 838, 230, 124)
SCALE = 4
SPAN = 65536

assert CROP[0] < TARGET[0] < CROP[0] + CROP[2]
assert CROP[1] < TARGET[1] < CROP[1] + CROP[3]

def kvmd(px,py, width=W,height=H,span=SPAN):
    return tuple(max(-32768,min(32767, round((p/d-0.5)*span))) for p,d in ((px,width),(py,height)))

assert kvmd(*TARGET) == (16384,16384)
assert (TARGET[0]-CROP[0], TARGET[1]-CROP[1]) == (100,62)


def canvas(step, title, subtitle, command, source='NAVIGATION.md · illustrative'):
    fig, ax = plt.subplots(figsize=(16,9), dpi=130)
    fig.patch.set_facecolor(PAPER)
    ax.set_xlim(0,16); ax.set_ylim(0,9); ax.set_aspect('equal'); ax.axis('off')
    # slide header
    ax.add_patch(FancyBboxPatch((0.62,8.05),(.56),(.56),boxstyle='round,pad=0.04,rounding_size=.14',facecolor=NAVY,edgecolor='none'))
    ax.text(.90,8.33,f'{step:02}',ha='center',va='center',size=17,weight='bold',color=PAPER)
    ax.text(1.38,8.40,title,ha='left',va='center',size=25.5,weight='bold',color=NAVY)
    ax.text(1.40,7.91,subtitle,ha='left',va='center',size=12.6,color=MUTED)
    ax.plot([.6,15.4],[7.60,7.60],color=LINE,lw=1.2)
    ax.plot([.6,15.4],[1.17,1.17],color=LINE,lw=1.2)
    ax.text(.68,.89,'EXAMPLE COMMAND / DECISION',size=9.2,weight='bold',color=MUTED)
    ax.text(.68,.53,command,size=12.1,family='DejaVu Sans Mono',color=NAVY)
    ax.text(15.35,.88,'SOURCE',ha='right',size=8.3,color=MUTED,weight='bold')
    ax.text(15.35,.53,source,ha='right',size=9.2,color=MUTED)
    return fig,ax


def box(ax,x,y,w,h,face=PALE,edge=LINE,r=.16,lw=1.4):
    ax.add_patch(FancyBboxPatch((x,y),w,h,
                 boxstyle=f'round,pad=0.01,rounding_size={r}',
                 facecolor=face,edgecolor=edge,linewidth=lw))


def label(ax,x,y,s,size=12,color=TEXT,weight='normal',ha='left',va='center',family=None):
    ax.text(x,y,s,size=size,color=color,weight=weight,ha=ha,va=va,family=family)


def arrow(ax,x1,y1,x2,y2,color=BLUE,lw=2,style='-|>',ms=14):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle=style,
                 mutation_scale=ms,linewidth=lw,color=color,shrinkA=3,shrinkB=3))


def codebox(ax,x,y,w,h,s):
    box(ax,x,y,w,h,face=NAVY,edge=NAVY,r=.12)
    ax.text(x+.24,y+h/2,s,color=PAPER,size=12.5,family='DejaVu Sans Mono',va='center')


def bullet(ax,x,y,key,value,fs=12,color=BLUE):
    ax.add_patch(Circle((x,y),.055,facecolor=color,edgecolor='none'))
    label(ax,x+.20,y,key,size=fs,weight='bold')
    label(ax,x+.20,y-.37,value,size=fs-1.2,color=MUTED)


def desktop(ax,x,y,w,h,after=False,annotate=False,small=False):
    """Simulated target screen; input positions use screen pixels, origin top-left."""
    fx=lambda p: x+w*p/W
    fy=lambda p: y+h*(1-p/H)
    def rect(left,top,width,height,face,edge=LINE,lw=1.0,r=.03):
        box(ax,fx(left),fy(top+height),w*width/W,h*height/H,face,edge,r,lw)
    def t(px,py,s,size=11,color=TEXT,weight='normal',ha='left'):
        label(ax,fx(px),fy(py),s,size=size,color=color,weight=weight,ha=ha)
    rect(0,0,W,H, '#E7EDF2', '#9AAEC2',lw=1.3)
    rect(0,0,W,60, NAVY,NAVY)
    t(50,30,'LAB / WORKSTATION' if small else 'LAB COMPUTER / WORKSTATION',size=(8.0 if small else 12),color=PAPER,weight='bold')
    t(1790,30,'●',size=12,color='#78C7B2',ha='center')
    rect(500,205,1210,820,PAPER,LINE,lw=1.5)
    rect(500,205,1210,85,'#E8F0F6',LINE)
    t(555,248,'Device overview',size=(8.3 if small else 14.2),weight='bold')
    t(560,380,'Status' if small else 'System status',size=(7.7 if small else 12),weight='bold')
    rect(560,425,930,95,LIGHTTEAL, '#B3DBD2')
    t(600,475,'Connected' if small else 'Connection active',size=(7.1 if small else 11.5),color=TEAL,weight='bold')
    rect(560,585,930,95,PALE,LINE)
    t(600,636,'Device: sample-01' if small else 'Current device: Example workstation',size=(6.8 if small else 11))
    if not after:
        rect(1360,874,160,52,BLUE,BLUE,r=.03)
        t(1440,900,'Details',size=(7.0 if small else 11.5),color=PAPER,weight='bold',ha='center')
    else:
        rect(1050,700,585,260,LIGHTBLUE,BLUE,r=.03)
        t(1090,757,'DETAILS OPEN',size=(7.4 if small else 13),color=BLUE,weight='bold')
        t(1090,826,'Status: connected',size=(7.1 if small else 11))
        t(1090,886,'Device ID: sample-01',size=(7.1 if small else 11))
    if annotate and not after:
        ax.add_patch(Circle((fx(TARGET[0]),fy(TARGET[1])),.065,edgecolor=RED,facecolor=GOLD,lw=1.4,zorder=8))
        ax.plot([fx(TARGET[0])-.11,fx(TARGET[0])+.11],[fy(TARGET[1]),fy(TARGET[1])],color=RED,lw=1.4,zorder=8)
        ax.plot([fx(TARGET[0]),fx(TARGET[0])],[fy(TARGET[1])-.11,fy(TARGET[1])+.11],color=RED,lw=1.4,zorder=8)
    return fx,fy


def make01(out):
    fig,ax=canvas(1,'Activate the skill and resolve the endpoint',
        'The agent first identifies a PiKVM task; the client never assumes an address.',
        'No configured URL or credentials  →  stop and ask the user',
        'SKILL.md §§ endpoint & credentials')
    box(ax,.72,4.12,3.15,1.75,face=LIGHTBLUE,edge=BLUE)
    label(ax,2.29,5.31,'USER REQUEST',size=11,color=BLUE,ha='center',weight='bold')
    label(ax,2.29,4.70,'"Open details"',size=14.4,ha='center',weight='bold')
    arrow(ax,3.93,4.99,5.25,4.99)
    box(ax,5.36,4.12,3.13,1.75,face=PALE)
    label(ax,6.92,5.31,'LLM + SKILL.md',size=11,color=BLUE,ha='center',weight='bold')
    label(ax,6.92,4.77,'Select PiKVM skill',size=15,ha='center',weight='bold')
    arrow(ax,8.55,4.99,9.84,4.99)
    box(ax,9.95,4.05,5.22,1.90,face=LIGHTTEAL,edge=TEAL)
    label(ax,12.55,5.48,'CONFIGURATION PRECEDENCE',size=11,color=TEAL,ha='center',weight='bold')
    label(ax,10.40,5.02,'1  Flags passed to pikvm.sh',size=12.7)
    label(ax,10.40,4.66,'2  PIKVM_* environment variables',size=12.7)
    label(ax,10.40,4.30,'3  pikvm.local / user config',size=12.7)
    box(ax,1.25,2.03,6.3,1.15,face=LIGHTRED,edge=RED)
    label(ax,1.56,2.76,'BLOCKED',size=11,weight='bold',color=RED)
    label(ax,1.56,2.36,'No host / no credentials → do not guess',size=12.4)
    box(ax,8.44,2.03,6.3,1.15,face=LIGHTTEAL,edge=TEAL)
    label(ax,8.75,2.76,'READY',size=11,weight='bold',color=TEAL)
    label(ax,8.75,2.36,'Resolved HTTP(S) origin + valid authentication',size=12.4)
    arrow(ax,12.55,4.0,11.55,3.23,color=TEAL)
    arrow(ax,10.55,4.0,5.56,3.23,color=RED)
    out(1,fig)


def make02(out):
    fig,ax=canvas(2,'Read state before sending input',
        'Read-only REST queries establish which device was reached and whether HID is usable.',
        'scripts/pikvm.sh info   |   scripts/pikvm.sh hid   |   scripts/pikvm.sh power',
        'SKILL.md §§ usage & field notes')
    checks=[('info','GET /api/info','Identify the PiKVM',LIGHTBLUE,BLUE),
            ('hid','GET /api/hid','Check keyboard and mouse',LIGHTTEAL,TEAL),
            ('power','GET /api/atx','Inspect ATX state',LIGHTGOLD,GOLD)]
    for i,(cmd,endpoint,desc,fc,cc) in enumerate(checks):
        x=.8+i*5.08
        box(ax,x,3.68,4.44,2.35,face=fc,edge=cc)
        label(ax,x+.28,5.54,cmd,size=20,weight='bold',color=cc)
        label(ax,x+.28,4.98,endpoint,size=12.2,family='DejaVu Sans Mono')
        label(ax,x+.28,4.34,desc,size=12.5)
        arrow(ax,x+2.22,3.60,x+2.22,2.70,color=cc)
    box(ax,2.0,1.91,12.0,.66,face=PALE,edge=LINE)
    label(ax,8.0,2.24,'Important: ATX LED state may be misleading when the ATX cable is not wired.',size=12,ha='center')
    label(ax,8.0,6.79,'Three independent API checks — no screenshot or DOM is returned by these calls.',size=12.6,ha='center',color=MUTED)
    out(2,fig)


def make03(out):
    fig,ax=canvas(3,'Capture a fresh visual observation',
        'The target is a real computer. PiKVM samples its video and serves a JPEG frame.',
        'scripts/pikvm.sh snapshot snap.jpg    # GET /api/streamer/snapshot',
        'pikvm.sh · NAVIGATION.md § core loop')
    box(ax,.65,2.57,3.28,3.45,face=PALE)
    label(ax,2.29,5.62,'TARGET COMPUTER',size=11,ha='center',weight='bold',color=BLUE)
    desktop(ax,.98,3.34,2.65,1.66,small=True)
    label(ax,2.29,2.91,'Hardware video output',size=11.4,ha='center')
    arrow(ax,3.97,4.25,5.40,4.25)
    box(ax,5.52,2.56,3.42,3.47,face=LIGHTTEAL,edge=TEAL)
    label(ax,7.23,5.60,'PiKVM / KVMD',size=15.5,ha='center',weight='bold',color=TEAL)
    label(ax,7.23,4.70,'Video capture / streamer',size=12.2,ha='center')
    label(ax,7.23,3.96,'HTTP REST snapshot',size=12.2,ha='center')
    label(ax,7.23,3.20,'Authentication required',size=11.1,ha='center',color=MUTED)
    arrow(ax,9.02,4.25,10.36,4.25)
    box(ax,10.50,2.57,4.83,3.45,face=LIGHTBLUE,edge=BLUE)
    label(ax,12.92,5.60,'AGENT OBSERVATION',size=11,ha='center',weight='bold',color=BLUE)
    desktop(ax,11.00,3.28,3.86,2.42,small=True)
    label(ax,12.92,2.91,'JPEG frame · 1920 × 1200 px',size=11.4,ha='center')
    label(ax,8,6.66,'A snapshot is pixel data, not an accessible browser element tree.',size=13.5,ha='center',color=MUTED)
    out(3,fig)


def make04(out):
    fig,ax=canvas(4,'Locate, crop, and measure the target',
        'Zoom is a visual aid. The click point must be mapped back to full-frame pixels.',
        'python3 scripts/zoom.py snap.jpg crop.png --box 1340 838 230 124 --scale 4',
        'NAVIGATION.md § zoom · zoom.py')
    label(ax,3.55,6.99,'FULL SNAPSHOT  (1920 × 1200)',size=12.7,ha='center',weight='bold',color=BLUE)
    fx,fy=desktop(ax,.78,2.39,6.10,3.81,annotate=False,small=True)
    x0,y0,cw,ch=CROP
    croprect=Rectangle((fx(x0),fy(y0+ch)),6.10*cw/W,3.81*ch/H,fill=False,edgecolor=GOLD,lw=3)
    ax.add_patch(croprect)
    label(ax,3.75,1.95,'Crop origin = (1340, 838)',size=12,ha='center',color=GOLD,weight='bold')
    arrow(ax,6.91,4.31,8.19,4.31,color=GOLD)
    box(ax,8.32,2.22,6.87,4.58,face=PALE)
    label(ax,11.75,6.40,'ZOOMED ROI  (230 × 124 → 920 × 496)',size=12.3,ha='center',weight='bold',color=BLUE)
    # enlarged crop, with a single target in the original image's style
    box(ax,9.15,3.39,5.19,2.12,face='#EDF2F6',edge=LINE)
    box(ax,10.16,4.10,3.18,1.02,face=BLUE,edge=BLUE,r=.13)
    label(ax,11.75,4.60,'Details',size=21,color=PAPER,weight='bold',ha='center')
    ax.add_patch(Circle((11.75,4.60),.045,edgecolor=RED,facecolor=GOLD,lw=1.2))
    arrow(ax,11.75,4.43,11.75,3.74,color=RED,ms=12)
    label(ax,11.75,3.53,'crop-local center (100, 62)',size=11.3,ha='center',color=RED,weight='bold')
    box(ax,8.70,2.49,6.1,.65,face=LIGHTTEAL,edge=TEAL,r=.08)
    label(ax,11.75,2.82,'full frame: (1340+100, 838+62) = (1440, 900)',size=10.1,ha='center',weight='bold')
    out(4,fig)


def draw_coordinate_plane(ax,x,y,w,h,centered=False):
    box(ax,x,y,w,h,face=PALE,edge=LINE,r=.08)
    for v in (.25,.5,.75):
        ax.plot([x+w*v,x+w*v],[y,y+h],color=LINE,lw=1.05,ls='--')
        ax.plot([x,x+w],[y+h*v,y+h*v],color=LINE,lw=1.05,ls='--')
    px=x+w*.75; py=y+h*.25
    ax.scatter([px],[py],s=155,c=GOLD,edgecolors=RED,lw=1.1,zorder=5)
    ax.plot([px,px],[y,py],color=GOLD,lw=2,ls=':')
    ax.plot([x,px],[py,py],color=GOLD,lw=2,ls=':')
    if centered:
        label(ax,x+w*.51,y+h*.52,'(0,0)',size=11,color=MUTED)
        label(ax,x+w*.75,y+h*.22,'(16384, 16384)',size=10.3,color=GOLD,weight='bold',ha='center')
        label(ax,x,y+h+.19,'-32768',size=9.5,color=MUTED)
        label(ax,x+w,y+h+.19,'+32767',size=9.5,color=MUTED,ha='right')
        label(ax,x,y-.20,'-32768',size=9.5,color=MUTED)
        label(ax,x+w,y-.20,'+32767',size=9.5,color=MUTED,ha='right')
    else:
        label(ax,x,y+h+.19,'(0,0)',size=10,color=MUTED)
        label(ax,x+w,y+h+.19,'(1920,0)',size=10,color=MUTED,ha='right')
        label(ax,x,y-.20,'(0,1200)',size=10,color=MUTED)
        label(ax,x+w,y-.20,'(1920,1200)',size=10,color=MUTED,ha='right')
        label(ax,px-.04,py-.31,'(1440,900)',size=11,ha='center',color=GOLD,weight='bold')


def make05(out):
    fig,ax=canvas(5,'Convert pixels to native KVMD coordinates',
        'The mouse API is center-origin, not top-left-origin pixel space.',
        'python3 scripts/kvmcoords.py snap.jpg 1440 900    # move 16384 16384',
        'kvmcoords.py · SKILL.md § mouse')
    label(ax,3.14,6.66,'IMAGE PIXELS  /  origin top left',size=12.2,weight='bold',ha='center',color=BLUE)
    draw_coordinate_plane(ax,.79,3.03,4.72,2.96,False)
    label(ax,12.88,6.66,'KVMD ABSOLUTE SPACE  /  origin center',size=12.2,weight='bold',ha='center',color=TEAL)
    draw_coordinate_plane(ax,10.51,3.03,4.72,2.96,True)
    box(ax,5.90,4.73,4.18,1.34,face=LIGHTTEAL,edge=TEAL)
    label(ax,8.0,5.66,'NORMALIZE + CENTER + SCALE',size=11,weight='bold',color=TEAL,ha='center')
    label(ax,8.0,5.24,'((pixel / dimension) - 0.5) × 65536',size=10.35,ha='center',family='DejaVu Sans Mono')
    arrow(ax,5.63,4.23,10.40,4.23,color=TEAL,lw=2)
    box(ax,5.80,2.77,4.40,.99,face=PAPER,edge=LINE,r=.10)
    label(ax,8.0,3.44,'x: (1440/1920 - 0.5) × 65536 = +16384',size=9.8,ha='center',weight='bold')
    label(ax,8.0,3.04,'y: (900/1200 - 0.5) × 65536 = +16384',size=9.8,ha='center',weight='bold')
    label(ax,8.0,1.85,'The helper detects W × H from snap.jpg and clamps values to −32768…32767.',size=11.4,ha='center',color=MUTED)
    out(5,fig)


def make06(out):
    fig,ax=canvas(6,'Move and click via REST → USB HID',
        'The agent calls the Bash client; PiKVM emulates a mouse to the target computer.',
        'scripts/pikvm.sh move 16384 16384    ;    scripts/pikvm.sh click left',
        'pikvm.sh §§ move/click · NAVIGATION.md')
    stages=[('1  AGENT','Choose pixel center','(1440, 900)',LIGHTBLUE,BLUE),
            ('2  CLI WRAPPER','pikvm.sh','move + click',PALE,BLUE),
            ('3  PiKVM / KVMD','HTTP REST events','send_mouse_*',LIGHTTEAL,TEAL),
            ('4  TARGET OS','USB HID input','Cursor + button',LIGHTGOLD,GOLD)]
    for i,(heading,sub,detail,fc,ec) in enumerate(stages):
        x=.68+i*3.92
        box(ax,x,4.05,3.32,2.13,face=fc,edge=ec)
        label(ax,x+1.66,5.72,heading,size=12.4,color=ec,weight='bold',ha='center')
        label(ax,x+1.66,5.05,sub,size=13.8,weight='bold',ha='center')
        label(ax,x+1.66,4.54,detail,size=11.6,ha='center',color=MUTED)
        if i<3:arrow(ax,x+3.37,5.11,x+3.89,5.11,color=BLUE,ms=12)
    box(ax,1.13,2.30,6.84,1.20,face=NAVY,edge=NAVY)
    label(ax,1.42,3.25,'HTTP requests (simplified)',size=10.8,weight='bold',color='#9BC3EE')
    label(ax,1.42,2.87,'POST /api/hid/events/send_mouse_move',size=10.5,color=PAPER,family='DejaVu Sans Mono')
    label(ax,1.42,2.54,'?to_x=16384&to_y=16384   (then send_mouse_button)',size=10.3,color=PAPER,family='DejaVu Sans Mono')
    box(ax,8.20,2.42,6.63,.99,face=LIGHTGOLD,edge=GOLD)
    label(ax,8.51,3.05,'Optional keyboard branch after focus check',size=11.0,weight='bold',color=GOLD)
    label(ax,8.51,2.69,'type TEXT   /   key Enter   /   shortcut MetaLeft KeyA',size=11.4)
    label(ax,8.0,1.79,'Do not assume focus: keyboard input goes to whatever the operating system has focused.',size=11.3,ha='center',color=MUTED)
    out(6,fig)


def make07(out):
    fig,ax=canvas(7,'Verify the result with another snapshot',
        'A successful API response only confirms a request; observe the GUI to confirm the task outcome.',
        'scripts/pikvm.sh snapshot after.jpg   →   inspect the new frame',
        'NAVIGATION.md § core loop & recipes')
    label(ax,4.25,6.96,'BEFORE  ·  button available',size=12.4,ha='center',weight='bold',color=BLUE)
    label(ax,11.73,6.96,'AFTER  ·  expected details panel',size=12.4,ha='center',weight='bold',color=TEAL)
    desktop(ax,.93,2.89,6.10,3.81,after=False,annotate=True,small=True)
    desktop(ax,8.94,2.89,6.10,3.81,after=True,annotate=False,small=True)
    arrow(ax,7.10,4.82,8.85,4.82,color=TEAL,lw=2)
    box(ax,1.18,1.92,13.64,.85,face=LIGHTTEAL,edge=TEAL)
    label(ax,8,2.35,'Compare intended state vs. observed state. No change? Re-snapshot and re-measure; do not blind-retry.',size=11.9,ha='center',weight='bold')
    out(7,fig)


def make08(out):
    fig,ax=canvas(8,'Branch safely: retry, stop, or report',
        'The observation loop is iterative, but not all failures should trigger another click.',
        'Success: report  |  Miss: new snapshot  |  Lock screen: stop',
        'NAVIGATION.md § hard-won lessons · SKILL.md § safety')
    items=[
        ('EXPECTED CHANGE','Complete the task','Report visible evidence',LIGHTTEAL,TEAL),
        ('NO CHANGE / MISS','Re-snapshot and re-zoom','Recalculate from the fresh frame',LIGHTBLUE,BLUE),
        ('SNAPSHOT HTTP 503','Check streamer/display','Open viewer if available; retry',LIGHTGOLD,GOLD),
        ('LOCK SCREEN / RISK','Stop and ask the user','Do not guess credentials',LIGHTRED,RED),
    ]
    for i,(event,action,note,fc,ec) in enumerate(items):
        x=.70 + (i%2)*7.66
        y=4.55 if i<2 else 2.29
        box(ax,x,y,6.91,1.79,face=fc,edge=ec)
        label(ax,x+.29,y+1.41,event,size=12,weight='bold',color=ec)
        label(ax,x+.29,y+.95,action,size=15.5,weight='bold')
        label(ax,x+.29,y+.47,note,size=11.5,color=MUTED)
    label(ax,8,6.97,'Decision after inspecting the latest observation',size=13.8,ha='center',weight='bold',color=NAVY)
    box(ax,3.05,1.48,9.9,.49,face=PALE,edge=LINE,r=.07)
    label(ax,8,1.73,'Power-off / reset is a separate destructive branch → confirm intent before use.',size=10.8,ha='center',color=RED)
    out(8,fig)


def render(outdir):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    outputs=[]
    def out(i,fig):
        p=outdir/f'{i:02d}_{["activate_and_configure", "preflight_checks", "fresh_snapshot", "crop_zoom_measure", "pixel_to_kvmd", "send_hid_events", "verify_result", "safe_recovery"][i-1]}.png'
        fig.savefig(p, dpi=130, facecolor=PAPER, bbox_inches=None)
        fig.savefig(p.with_suffix('.svg'), facecolor=PAPER, bbox_inches=None)
        plt.close(fig)
        outputs.append(p)
    for fn in (make01,make02,make03,make04,make05,make06,make07,make08):
        fn(out)
    return outputs


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output-dir',default='figures')
    a=ap.parse_args()
    for path in render(a.output_dir):print(path)

if __name__=='__main__':main()
