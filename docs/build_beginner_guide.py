#!/usr/bin/env python3
"""
Fiber Tech Starter Guide — the plain-English beginner version.

A short, simple, low-jargon quick-start for a brand-new L2 fiber technician.
Big headings, plain words, analogies, and only the must-know basics.

Run:  python3 docs/build_beginner_guide.py
Out:  docs/Fiber_Tech_Starter_Guide.pdf
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Flowable, KeepTogether, ListFlowable, ListItem, NextPageTemplate,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

# ---- palette (friendly, high-contrast) ----
NAVY   = colors.HexColor("#143a5a")
BLUE   = colors.HexColor("#1f6fb2")
TEAL   = colors.HexColor("#12897f")
GREEN  = colors.HexColor("#2e8b57")
AMBER  = colors.HexColor("#e8952b")
RED    = colors.HexColor("#c0392b")
REDBG  = colors.HexColor("#fbeceb")
GREENBG= colors.HexColor("#e9f6ee")
BLUEBG = colors.HexColor("#eaf2fa")
YELBG  = colors.HexColor("#fdf3e2")
INK    = colors.HexColor("#1c1c1c")
GREY   = colors.HexColor("#5a6a7a")
LINEC  = colors.HexColor("#d3dde8")

PAGE_W, PAGE_H = letter
MARGIN = 0.9 * inch
OUT = os.path.join(os.path.dirname(__file__), "Fiber_Tech_Starter_Guide.pdf")

# ---- styles ----
body = ParagraphStyle("body", fontName="Helvetica", fontSize=11.5, leading=17,
                      textColor=INK, alignment=TA_LEFT, spaceAfter=7)
big  = ParagraphStyle("big", fontName="Helvetica", fontSize=12.5, leading=18.5,
                      textColor=INK, spaceAfter=8)
h1n  = ParagraphStyle("h1n", fontName="Helvetica-Bold", fontSize=11, textColor=AMBER,
                      spaceAfter=2)
h1   = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=24, leading=27,
                      textColor=NAVY, spaceAfter=6)
h2   = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=15, leading=19,
                      textColor=BLUE, spaceBefore=12, spaceAfter=5)
bullet = ParagraphStyle("bullet", parent=body, spaceAfter=3, leftIndent=2)
callout_t = ParagraphStyle("callout_t", fontName="Helvetica-Bold", fontSize=11.5,
                           leading=15, spaceAfter=3)
callout_b = ParagraphStyle("callout_b", fontName="Helvetica", fontSize=11, leading=15.5,
                           textColor=INK)

story = []

class ForceTwoPasses(Flowable):
    """Invisible: makes multiBuild run a 2nd pass so running headers resolve."""
    def __init__(self): super().__init__(); self._p = 0
    def isIndexing(self): return 1
    def beforeBuild(self): pass
    def afterBuild(self): pass
    def isSatisfied(self): self._p += 1; return self._p >= 2
    def notify(self, *a, **k): pass
    def wrap(self, *a): return (0, 0)
    def draw(self): pass

def para(t, s=body): story.append(Paragraph(t, s))
def spacer(h=6): story.append(Spacer(1, h))

class HR(Flowable):
    def __init__(self, t=2, c=AMBER, pad=2):
        super().__init__(); self.t=t; self.c=c; self.pad=pad; self.width=1
    def wrap(self, aw, ah): self.width=aw; return aw, self.t+self.pad*2
    def draw(self):
        self.canv.setStrokeColor(self.c); self.canv.setLineWidth(self.t)
        self.canv.line(0,self.pad,self.width,self.pad)

_sec = 0
def section_page(num_label, title):
    """New page, big friendly section header."""
    story.append(PageBreak())
    p = Paragraph(num_label, h1n); story.append(p)
    t = Paragraph(title, h1); t._chap = title; story.append(t)
    story.append(HR()); spacer(8)

def h(t): story.append(Paragraph(t, h2))

def blist(items, color=TEAL):
    flow = [ListItem(Paragraph(it, bullet), value="square", leftIndent=16,
                     bulletColor=color, spaceAfter=3) for it in items]
    story.append(ListFlowable(flow, bulletType="bullet", start="square",
                              bulletFontSize=6, bulletColor=color, leftIndent=14))
    spacer(4)

def numlist(items):
    flow = [ListItem(Paragraph(it, body), leftIndent=18, spaceAfter=4) for it in items]
    story.append(ListFlowable(flow, bulletType="1", leftIndent=16,
                              bulletFontName="Helvetica-Bold", bulletColor=BLUE))
    spacer(4)

class Callout(Flowable):
    def __init__(self, kind, title, lines):
        super().__init__()
        self.lines = lines if isinstance(lines, list) else [lines]
        self.title = title
        cfg = {"stop":(RED,REDBG,"STOP"), "do":(GREEN,GREENBG,"DO THIS"),
               "tip":(BLUE,BLUEBG,"TIP"), "think":(AMBER,YELBG,"THINK OF IT LIKE")}
        self.bar,self.bg,self.tag = cfg[kind]
        self.width=1
    def wrap(self, aw, ah):
        self.width=aw; inner=aw-26
        self._f=[]
        ts=ParagraphStyle("ct",parent=callout_t,textColor=self.bar)
        head = "%s — %s" % (self.tag, self.title) if self.title else self.tag
        self._f.append(Paragraph(head, ts))
        for ln in self.lines: self._f.append(Paragraph(ln, callout_b))
        self._sz=[]; self._h=0
        for f in self._f:
            _,hh=f.wrap(inner,ah); self._sz.append(hh); self._h+=hh+3
        self._h+=14
        return aw,self._h
    def draw(self):
        c=self.canv; c.saveState()
        c.setFillColor(self.bg); c.roundRect(0,0,self.width,self._h,5,fill=1,stroke=0)
        c.setFillColor(self.bar); c.rect(0,0,5,self._h,fill=1,stroke=0)
        y=self._h-7
        for f,hh in zip(self._f,self._sz):
            y-=hh; f.drawOn(c,16,y); y-=3
        c.restoreState()

def callout(kind,title,lines):
    spacer(2); story.append(Callout(kind,title,lines)); spacer(8)

# ---- simple 6-step link-down flowchart ----
class SimpleFlow(Flowable):
    def __init__(self):
        super().__init__(); self.width=6.5*inch; self.height=6.0*inch
    def wrap(self, aw, ah): self.width=min(aw,6.6*inch); return self.width,self.height
    def _box(self,d,cx,cy,w,hh,text,fill,fs=11):
        d.add(Rect(cx-w/2,cy-hh/2,w,hh,fillColor=fill,strokeColor=fill,rx=6,ry=6))
        lines=text.split("\n"); ty=cy+len(lines)*(fs+2)/2-fs
        for ln in lines:
            d.add(String(cx,ty,ln,fontName="Helvetica-Bold",fontSize=fs,
                         fillColor=colors.white,textAnchor="middle")); ty-=(fs+2)
    def _arrow(self,d,x1,y1,x2,y2,c=BLUE):
        import math
        d.add(Line(x1,y1,x2,y2,strokeColor=c,strokeWidth=1.4))
        a=math.atan2(y2-y1,x2-x1); ah=7
        d.add(Polygon([x2,y2,x2-ah*math.cos(a-.5),y2-ah*math.sin(a-.5),
                       x2-ah*math.cos(a+.5),y2-ah*math.sin(a+.5)],fillColor=c,strokeColor=c))
    def draw(self):
        d=Drawing(self.width,self.height); cx=self.width*0.5; w=4.2*inch; hh=0.5*inch
        steps=[("Is the link down?",NAVY),
               ("1. Look at the lights on the optic",BLUE),
               ("2. Clean BOTH ends (inspect first)",TEAL),
               ("3. Check you're on the right strand",TEAL),
               ("4. Check the labels match the record",BLUE),
               ("5. Ask someone to check light levels",BLUE),
               ("Fixed it? If not → ASK FOR HELP",GREEN)]
        n=len(steps); top=5.7*inch; gap=(top-0.4*inch)/(n-1)
        ys=[top-i*gap for i in range(n)]
        for i,(txt,col) in enumerate(steps):
            fs = 11 if i in (0,n-1) else 10.5
            self._box(d,cx,ys[i],w,hh,txt,col,fs)
            if i>0: self._arrow(d,cx,ys[i-1]-hh/2,cx,ys[i]+hh/2)
        d.drawOn(self.canv,0,0)

# ---- page furniture ----
TITLE="Fiber Tech Starter Guide"
def cover(c,doc):
    c.saveState()
    c.setFillColor(NAVY); c.rect(0,0,PAGE_W,PAGE_H,fill=1,stroke=0)
    c.setFillColor(TEAL); c.rect(0,PAGE_H-4.2*inch,PAGE_W,0.14*inch,fill=1,stroke=0)
    c.setFillColor(AMBER); c.rect(0,PAGE_H-4.2*inch-0.06*inch,PAGE_W,0.06*inch,fill=1,stroke=0)
    c.setFillColor(AMBER); c.setFont("Helvetica-Bold",13)
    c.drawString(MARGIN,PAGE_H-1.7*inch,"START HERE  •  NEW TECHNICIAN")
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",46)
    c.drawString(MARGIN,PAGE_H-2.7*inch,"Fiber Tech")
    c.drawString(MARGIN,PAGE_H-3.45*inch,"Starter Guide")
    c.setFillColor(colors.HexColor("#bcd0e4")); c.setFont("Helvetica",15)
    c.drawString(MARGIN,PAGE_H-3.95*inch,"The plain-English basics for your first days on the floor.")
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",13)
    c.drawString(MARGIN,3.2*inch,"Read this first. It keeps things simple:")
    c.setFillColor(colors.HexColor("#cddcec")); c.setFont("Helvetica",12)
    lines=["Stay safe  •  what fiber is  •  the plugs you'll touch",
           "TX and RX  •  keep it clean  •  read a work order",
           "when a link is down  •  labeling  •  words to know"]
    yy=2.85*inch
    for ln in lines: c.drawString(MARGIN,yy,ln); yy-=0.32*inch
    c.setFillColor(colors.HexColor("#8aa0b8")); c.setFont("Helvetica",10)
    c.drawString(MARGIN,0.95*inch,"When in doubt, STOP and ask. Nobody expects you to know it all on day one.")
    c.drawString(MARGIN,0.72*inch,"Always follow your site's own rules, safety steps, and records.")
    c.restoreState()

def later(c,doc):
    c.saveState()
    c.setStrokeColor(LINEC); c.setLineWidth(0.6)
    c.line(MARGIN,PAGE_H-0.6*inch,PAGE_W-MARGIN,PAGE_H-0.6*inch)
    c.setFont("Helvetica",8); c.setFillColor(GREY)
    c.drawString(MARGIN,PAGE_H-0.52*inch,TITLE)
    prev=getattr(doc,"_chap_prev",{}); title=""
    for pg in sorted(prev):
        if pg<=doc.page: title=prev[pg]
        else: break
    c.drawRightString(PAGE_W-MARGIN,PAGE_H-0.52*inch,title)
    c.line(MARGIN,0.62*inch,PAGE_W-MARGIN,0.62*inch)
    c.setFont("Helvetica",8.5); c.drawString(MARGIN,0.44*inch,"For new fiber technicians")
    c.drawRightString(PAGE_W-MARGIN,0.44*inch,"Page %d"%doc.page)
    c.setFont("Helvetica-Oblique",7.5)
    c.drawCentredString(PAGE_W/2,0.44*inch,"When in doubt, stop and ask")
    c.restoreState()

class Doc(BaseDocTemplate):
    def __init__(self,fn,**kw):
        super().__init__(fn,**kw)
        self._chap=""; self._chap_prev={}; self._chap_cur={}
        fr=Frame(MARGIN,0.8*inch,PAGE_W-2*MARGIN,PAGE_H-1.65*inch,id="m",
                 leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        cf=Frame(0,0,PAGE_W,PAGE_H,id="c")
        self.addPageTemplates([PageTemplate("Cover",[cf],onPage=cover),
                               PageTemplate("Normal",[fr],onPage=later)])
    def build(self,flowables,**kw):
        self._chap_prev=self._chap_cur; self._chap_cur={}
        return super().build(flowables,**kw)
    def afterFlowable(self,f):
        if hasattr(f,"_chap"): self._chap=f._chap; self._chap_cur[self.page]=f._chap

# =====================================================================
# CONTENT
# =====================================================================
story.append(ForceTwoPasses())
story.append(NextPageTemplate("Normal"))

# ---- Welcome ----
story.append(PageBreak())
para("Welcome!", h1)
story.append(HR()); spacer(8)
para("This little guide is for your <b>first days</b> as a fiber technician. It skips the "
     "deep theory and just tells you what things are and what to do. Keep it in your bag. "
     "Once it all feels easy, move up to the full <i>L2 Fiber Technician Field Manual</i>.", big)
callout("think","What a fiber tech really does",
        ["Your job is simple to say: <b>move light through glass, cleanly, to the right place, "
         "and write down what you did.</b> Everything in this guide supports that one idea."])
para("A few promises to make your life easy:", h2)
blist([
    "<b>You will not know everything on day one.</b> That's normal. Ask questions.",
    "<b>Slow and correct beats fast and wrong.</b> A rushed mistake can take a service down.",
    "<b>The record is the boss.</b> If the paperwork and the real world don't match, stop.",
    "<b>Clean, then connect.</b> Dirt is the #1 cause of problems. Every single time.",
])

# =====================================================================
section_page("STEP 1","Stay Safe")
para("Nothing here is worth getting hurt. Learn these few rules and you'll be fine.", big)

callout("stop","Never look into a fiber or a port",
        ["Fiber carries <b>invisible</b> laser light. You won't see it or feel it, but it can "
         "hurt your eyes. <b>Never</b> look into the end of a cable or an open port. To check "
         "an end, use a fiber scope — never your eye."])

h("The short safety list")
blist([
    "<b>Wear safety glasses</b> when you handle bare fiber.",
    "<b>Bits of fiber are like tiny glass splinters.</b> They're nearly invisible and won't "
    "come out. Work over a mat, drop scraps in the little scrap jar, and never touch your face.",
    "<b>No food or drink</b> at the fiber bench — a scrap could end up in it.",
    "<b>Ladders and lifts:</b> only use them if you're trained. Three points of contact, "
    "don't overreach.",
    "<b>See a lock or tag on something?</b> Don't touch it. Someone's safety depends on it.",
    "<b>Know your exits</b> and where the eyewash station is before you need them.",
])
callout("do","If something feels unsafe",
        ["Stop. Step back. Ask your lead. You will never get in trouble for pausing to stay safe. "
         "That's always the right call."])

# =====================================================================
section_page("STEP 2","What Is Fiber, Really?")
para("Fiber is a hair-thin strand of <b>glass</b> that carries light instead of electricity. "
     "A flash of light on means a 1, off means a 0 — that's how your data travels.", big)
callout("think","A fiber is like a garden hose for light",
        ["Shine a flashlight in one end and it comes out the other — even around gentle "
         "bends. Kink the hose (bend it too tight) and the flow chokes off. Same with fiber: "
         "<b>never bend it into a tight loop.</b>"])

h("Two big families")
blist([
    "<b>Single-mode (SMF)</b> — tiny glass core, goes really far. Jacket is usually "
    "<b>yellow</b>. Think long distances.",
    "<b>Multimode (MMF)</b> — bigger core, goes shorter distances but is cheaper. Jacket "
    "is usually <b>aqua</b> (or orange on older stuff). Think inside-the-building.",
])
callout("do","The one rule that matters most here",
        ["<b>Don't bend fiber too tight and don't crush it.</b> A good habit: never make a loop "
         "smaller than a soda can, and never cinch a zip tie down hard on it. Tight bends leak "
         "the light out and cause faults."])

# =====================================================================
section_page("STEP 3","The Plugs You'll Touch")
para("There are many connectors out there, but as a beginner you'll mostly see just two. "
     "Learn these first.", big)

h("LC — the little one (most common)")
blist([
    "Small connector, usually clipped together in <b>pairs</b> (duplex).",
    "One side sends light, the other side receives it (more on that next step).",
    "This is on almost everything you'll patch day to day.",
])
h("MPO / MTP — the wide one (many fibers in one plug)")
blist([
    "A wide, rectangular plug that holds <b>many</b> fibers at once (often 8 or 12).",
    "Used for the big, fast links. Has a little <b>key</b> (bump) on one side — it only "
    "goes in one way.",
    "MTP is just a fancy brand of MPO. They plug together.",
])

callout("stop","Green plugs and blue plugs don't mix",
        ["Connector ends are color-coded by how they're polished. <b>Green (APC)</b> only goes "
         "with green. <b>Blue (UPC)</b> only goes with blue. Forcing green into blue ruins both "
         "ends. If the colors don't match, stop."])
callout("tip","Push until it clicks",
        ["Connectors seat with a gentle <b>click</b>. If it doesn't click, it isn't seated — "
         "and a loose connector looks connected but won't work. Never force it; line it up and "
         "push straight in."])

# =====================================================================
section_page("STEP 4","TX and RX (Send and Receive)")
para("Every link needs to <b>send</b> in one direction and <b>receive</b> in the other. "
     "You'll see these two little words everywhere:", big)
blist([
    "<b>TX</b> = Transmit = the light going <b>out</b> (sending).",
    "<b>RX</b> = Receive = the light coming <b>in</b> (receiving).",
])
callout("think","Like a two-lane road, or a phone call",
        ["You talk on one line, the other person talks on the other. If both cars drove in the "
         "same lane, nobody gets anywhere. <b>TX on one end has to reach RX on the other end.</b> "
         "That crossover is called <i>polarity</i>."])

h("What this means for you")
blist([
    "On a duplex LC pair, the two fibers <b>cross over</b> so send meets receive. Usually the "
    "cable does this for you.",
    "Sometimes the work order says <b>ROLL</b>. That just means: <b>swap the two fibers</b> so "
    "send and receive line up. Use the jumper or clip that flips them.",
    "<b>Weird clue:</b> if every fiber tests fine but the link still won't come up, it's almost "
    "always a send/receive (polarity) mix-up — not a broken cable.",
])
callout("do","Don't panic about polarity",
        ["For now, just follow the work order. If it says ROLL, roll it. If the link won't come "
         "up and the fibers are clean and good, tell your lead ‘I think it's a polarity "
         "issue’ — they'll be impressed you spotted it."])

# =====================================================================
section_page("STEP 5","Keep It Clean")
para("This is the most important habit you will ever build as a fiber tech. Say it with us: "
     "<b>clean before you connect — every time.</b>", big)
callout("stop","One speck of dust = a dead link",
        ["A fiber core is thinner than a hair. A tiny speck of dust sitting on it blocks the "
         "light — or gets ground in and <b>permanently damages</b> the end when you plug "
         "in. Dirt is the #1 cause of fiber problems, by far."])

h("The three magic words: Inspect, Clean, Inspect")
numlist([
    "<b>Inspect</b> — look at the end with a fiber scope (a little microscope). Dirty?",
    "<b>Clean</b> — use a one-click cleaner (dry). Still dirty? Use the wet-then-dry method.",
    "<b>Inspect again</b> — only plug it in when it looks clean. If it won't clean up, it "
    "might be damaged — set it aside and tell your lead.",
])
callout("tip","Clean both sides",
        ["Clean the <b>connector</b> AND the <b>port/bulkhead</b> you're plugging into. Dirt "
         "hides on both. And keep a dust cap on anything that isn't plugged in right now."])

# =====================================================================
section_page("STEP 6","Read a Work Order")
para("A work order (also called a build record) tells you exactly what to do. It has two ends "
     "— an <b>A-side</b> (start) and a <b>Z-side</b> (finish). Read it slowly, top to bottom.", big)

h("The fields you'll actually use")
data=[
    ["What it says","What it means for you"],
    ["Cable ID","The name of the cable. It should match the label on the cable."],
    ["A-side","Where you start: room, rack, device, and port."],
    ["Z-side","Where you finish: the other room, rack, device, and port."],
    ["Rack","Which cabinet to walk to."],
    ["Port / Adapter","The exact hole you plug into."],
    ["Strand","Which fiber to use. Wrong strand = no light."],
    ["Notes","Read this! It's where words like ‘ROLL’ or ‘clean both ends’ live."],
]
t=Table(data,colWidths=[1.7*inch,4.9*inch])
t.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,0),BLUE),("TEXTCOLOR",(0,0),(-1,0),colors.white),
    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),10.5),
    ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
    ("GRID",(0,0),(-1,-1),0.5,LINEC),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f4f8fb")]),
]))
story.append(t); spacer(10)
callout("do","Simple habit: walk it, match it, then touch it",
        ["1) <b>Walk</b> to the rack. 2) <b>Match</b> the device, port, strand, and cable label "
         "to the record. 3) Only <b>then</b> touch anything. If something doesn't match — "
         "wrong label, no free port, colors don't match — take a photo and ask. Don't force it."])

# =====================================================================
section_page("STEP 7","When a Link Is Down")
para("A cable isn't working? Don't guess randomly. Work down this list in order — easy and "
     "cheap fixes first. Follow the arrows.", big)
spacer(2)
story.append(KeepTogether(SimpleFlow()))
spacer(8)
callout("tip","Change ONE thing at a time",
        ["Fix one thing, then check if it worked. If you swap the cable, the connector, and "
         "re-patch all at once, you'll never know what the problem was — and you might add a "
         "new one."])

# =====================================================================
section_page("STEP 8","Labeling")
para("A cable nobody can identify is a cable nobody can safely touch. Good labels keep the whole "
     "floor working. You'll often use a <b>Brady M511</b> label printer with a phone app.", big)
h("The simple version")
numlist([
    "Turn on the printer, open the <b>Brady Express Labels</b> app, connect over Bluetooth.",
    "Pick the <b>flag</b> label design.",
    "Type the <b>Cable ID from the work order</b> (only add more if your site says to).",
    "Check the preview, print a test — is it dark, centered, not cut off?",
    "Wipe the cable clean, wrap the flag on (not over a connector or a bend), press it down.",
    "Make sure it reads correctly. Label <b>both ends</b> of the cable.",
])
callout("do","Copy the site's naming exactly",
        ["Don't invent your own label format. Match how your site names things, letter for "
         "letter. That's what makes a label useful at 2 a.m. during an outage."])

# =====================================================================
section_page("WORDS","Words You'll Hear")
para("You don't need to memorize these — just know where to look. Here are the ones that "
     "come up most in your first weeks.", big)
gloss=[
    ("TX","Transmit — light going out (sending)"),
    ("RX","Receive — light coming in"),
    ("LC","The small, common connector (usually in pairs)"),
    ("MPO / MTP","The wide connector with many fibers"),
    ("SMF","Single-mode fiber — goes far (yellow)"),
    ("MMF","Multimode fiber — shorter runs (aqua/orange)"),
    ("APC","Green connector polish — only mates with green"),
    ("UPC","Blue connector polish — only mates with blue"),
    ("Strand","One single fiber inside a cable"),
    ("ROLL","Swap the two fibers so send meets receive"),
    ("Polarity","Making sure TX reaches RX (the crossover)"),
    ("A-side / Z-side","The start end / the finish end of a link"),
    ("Patch / Jumper","The cable you plug in to make a connection"),
    ("ODF","The frame/cabinet where fibers are patched"),
    ("Rack / Cabinet","The metal enclosure that holds the gear"),
    ("U (rack unit)","A slot height in a rack, counted from the bottom"),
    ("Optic / SFP","The little part that turns electricity into light"),
    ("Dust cap","The cap that keeps a connector clean when unplugged"),
    ("One-click cleaner","The pen tool you clean connectors with"),
    ("Scope","The little microscope for looking at fiber ends"),
    ("LOS","Loss of Signal — no light is getting through"),
    ("Bend radius","How tight you're allowed to bend a cable (don't kink it)"),
    ("Cold aisle / Hot aisle","The cool front of racks / the warm back"),
    ("NOC","Network Operations Center — the folks who watch the network"),
]
half=(len(gloss)+1)//2; L=gloss[:half]; Rr=gloss[half:]
rows=[]
kk=ParagraphStyle("kk",fontName="Helvetica-Bold",fontSize=9.5,leading=12,textColor=NAVY)
vv=ParagraphStyle("vv",fontName="Helvetica",fontSize=9.5,leading=12,textColor=INK)
for i in range(half):
    lk=Paragraph(L[i][0],kk); lv=Paragraph(L[i][1],vv)
    if i<len(Rr): rk=Paragraph(Rr[i][0],kk); rv=Paragraph(Rr[i][1],vv)
    else: rk=Paragraph("",vv); rv=Paragraph("",vv)
    rows.append([lk,lv,rk,rv])
gt=Table(rows,colWidths=[1.0*inch,2.35*inch,1.0*inch,2.35*inch])
gsty=[("VALIGN",(0,0),(-1,-1),"TOP"),
      ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
      ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
      ("LINEBELOW",(0,0),(-1,-1),0.4,colors.HexColor("#e4ebf2")),
      ("LINEAFTER",(1,0),(1,-1),0.7,LINEC)]
for i in range(len(rows)):
    if i%2: gsty.append(("BACKGROUND",(0,i),(-1,i),colors.HexColor("#f4f8fb")))
gt.setStyle(TableStyle(gsty)); story.append(gt)

# =====================================================================
# Closing: fridge-magnet rules
# =====================================================================
story.append(PageBreak())
para("The 8 Rules to Remember", h1)
story.append(HR()); spacer(10)
rules=[
    ("1","Never look into a fiber or a port. Use a scope."),
    ("2","Clean before you connect. Inspect, clean, inspect — every time."),
    ("3","Push until it clicks. Loose looks connected but isn't."),
    ("4","Don't bend it tight or crush it. No loops smaller than a soda can."),
    ("5","Match the colors. Green to green, blue to blue — never mix."),
    ("6","The record is the boss. If it doesn't match, stop and ask."),
    ("7","Label both ends, exactly how your site names things."),
    ("8","Change one thing at a time when fixing a problem."),
]
for num,txt in rules:
    row=Table([[Paragraph("<b>%s</b>"%num,ParagraphStyle("n",fontName="Helvetica-Bold",
                fontSize=17,textColor=colors.white,alignment=1)),
                Paragraph(txt,ParagraphStyle("r",fontName="Helvetica",fontSize=13,
                leading=17,textColor=INK))]],
               colWidths=[0.5*inch,6.1*inch])
    row.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,0),TEAL),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
        ("LEFTPADDING",(1,0),(1,0),12),
        ("BACKGROUND",(1,0),(1,0),colors.HexColor("#f4f8fb")),
        ("ROUNDEDCORNERS",[6,6,6,6]),
    ]))
    story.append(row); spacer(7)
spacer(10)
callout("do","And the most important rule of all",
        ["<b>When in doubt, stop and ask.</b> Every good senior tech was new once. Asking a "
         "question is how you learn — and how you avoid taking a service down. You've got this."])

# ---- build ----
doc=Doc(OUT,pagesize=letter,title="Fiber Tech Starter Guide",
        author="Data Center Operations",
        subject="Plain-English beginner guide for new L2 fiber technicians")
doc.multiBuild(story)
print("WROTE",OUT)
