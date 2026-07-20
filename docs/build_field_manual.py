#!/usr/bin/env python3
"""
L2 Fiber Technician Field Manual — PDF generator.

Builds a comprehensive, print-ready field manual for an L2 fiber technician
working in a large data center environment. Uses ReportLab Platypus with a
two-pass build so the Table of Contents resolves real page numbers.

Run:  python3 docs/build_field_manual.py
Out:  docs/L2_Fiber_Technician_Field_Manual.pdf
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, NextPageTemplate, Flowable, KeepTogether, ListFlowable, ListItem,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, PolyLine
from reportlab.pdfgen import canvas

# ----------------------------------------------------------------------------
# Palette
# ----------------------------------------------------------------------------
NAVY   = colors.HexColor("#12233b")
STEEL  = colors.HexColor("#1f4e79")
TEAL   = colors.HexColor("#137a7f")
ACCENT = colors.HexColor("#e8952b")   # amber accent
LIGHT  = colors.HexColor("#eef3f8")
LIGHT2 = colors.HexColor("#f6f8fb")
GRIDLN = colors.HexColor("#c9d5e3")
INK    = colors.HexColor("#1a1a1a")
GREY   = colors.HexColor("#5a6a7a")
DANGER = colors.HexColor("#a3271f")
DANGERBG = colors.HexColor("#fbeceb")
TIPBG  = colors.HexColor("#e9f4f0")
NOTEBG = colors.HexColor("#eef3f8")

PAGE_W, PAGE_H = letter
MARGIN = 0.85 * inch

OUT = os.path.join(os.path.dirname(__file__), "L2_Fiber_Technician_Field_Manual.pdf")

# ----------------------------------------------------------------------------
# Styles
# ----------------------------------------------------------------------------
ss = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

body = S("body", fontName="Helvetica", fontSize=9.7, leading=13.6,
         textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6)
body_l = S("body_l", parent=body, alignment=TA_LEFT)
lead = S("lead", fontName="Helvetica", fontSize=10.5, leading=15,
         textColor=colors.HexColor("#33414f"), alignment=TA_LEFT, spaceAfter=8)

h_chapter_num = S("h_chapter_num", fontName="Helvetica-Bold", fontSize=11,
                  textColor=ACCENT, spaceAfter=2, tracking=2)
h_chapter = S("h_chapter", fontName="Helvetica-Bold", fontSize=22, leading=25,
              textColor=NAVY, spaceAfter=4)
h2 = S("h2", fontName="Helvetica-Bold", fontSize=13, leading=16,
       textColor=STEEL, spaceBefore=12, spaceAfter=5)
h3 = S("h3", fontName="Helvetica-Bold", fontSize=10.6, leading=13.5,
       textColor=TEAL, spaceBefore=8, spaceAfter=3)

bullet = S("bullet", parent=body_l, spaceAfter=2, leftIndent=2)
tbl_cell = S("tbl_cell", fontName="Helvetica", fontSize=8.6, leading=11, textColor=INK)
tbl_cell_b = S("tbl_cell_b", parent=tbl_cell, fontName="Helvetica-Bold")
tbl_head = S("tbl_head", fontName="Helvetica-Bold", fontSize=8.8, leading=11,
             textColor=colors.white)
mono = S("mono", fontName="Courier", fontSize=8.4, leading=11, textColor=INK)
mono_b = S("mono_b", parent=mono, fontName="Courier-Bold")

callout_title = S("callout_title", fontName="Helvetica-Bold", fontSize=9.6,
                  leading=12, textColor=INK, spaceAfter=2)
callout_body = S("callout_body", fontName="Helvetica", fontSize=9.2, leading=12.6,
                 textColor=INK)

toc_h = S("toc_h", fontName="Helvetica-Bold", fontSize=20, textColor=NAVY, spaceAfter=10)

# ----------------------------------------------------------------------------
# Story-building helpers
# ----------------------------------------------------------------------------
story = []
_chapter_seq = 0

def para(txt, style=body):
    story.append(Paragraph(txt, style))

def spacer(h=6):
    story.append(Spacer(1, h))

def h(txt, style):
    story.append(Paragraph(txt, style))

class HR(Flowable):
    def __init__(self, width, thickness=1, color=GRIDLN, pad=3):
        super().__init__()
        self.width = width; self.thickness = thickness
        self.color = color; self.pad = pad
    def wrap(self, aw, ah):
        self.width = aw
        return aw, self.thickness + self.pad * 2
    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.pad, self.width, self.pad)

def hr(color=GRIDLN, thickness=1):
    story.append(HR(1, thickness, color))

def chapter(title, subtitle=None):
    """Start a new chapter on a fresh page; registers a TOC level-0 entry."""
    global _chapter_seq
    _chapter_seq += 1
    story.append(PageBreak())
    story.append(Paragraph("CHAPTER&nbsp;%d" % _chapter_seq, h_chapter_num))
    p = Paragraph(title, h_chapter)
    # tag for TOC via bookmark
    p._bookmark = ("chap", _chapter_seq, title)
    story.append(p)
    story.append(HR(1, 2, ACCENT, pad=2))
    if subtitle:
        story.append(Spacer(1, 4))
        story.append(Paragraph(subtitle, lead))
    story.append(Spacer(1, 6))

def section(title):
    p = Paragraph(title, h2)
    p._bookmark = ("sec", 0, title)
    story.append(p)

def sub(title):
    story.append(Paragraph(title, h3))

def blist(items, style=bullet, bcolor=TEAL, leading_after=4):
    flow = []
    for it in items:
        flow.append(ListItem(Paragraph(it, style),
                             value="square", leftIndent=14,
                             bulletColor=bcolor, spaceAfter=2))
    story.append(ListFlowable(flow, bulletType="bullet", start="square",
                              bulletFontSize=5, bulletColor=bcolor,
                              leftIndent=12))
    story.append(Spacer(1, leading_after))

def numlist(items):
    flow = []
    for it in items:
        flow.append(ListItem(Paragraph(it, body_l), leftIndent=16, spaceAfter=3))
    story.append(ListFlowable(flow, bulletType="1", leftIndent=14,
                              bulletFontName="Helvetica-Bold",
                              bulletColor=STEEL))
    story.append(Spacer(1, 4))

def ref_table(header, rows, col_widths, font=8.6, head_bg=STEEL, zebra=True):
    """Build a styled reference table. Cells may be str or Paragraph."""
    data = []
    data.append([Paragraph(c, tbl_head) for c in header])
    for r in rows:
        row = []
        for c in r:
            if isinstance(c, Flowable):
                row.append(c)
            else:
                row.append(Paragraph(c, ParagraphStyle("c", parent=tbl_cell, fontSize=font)))
        data.append(row)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    styc = [
        ("BACKGROUND", (0, 0), (-1, 0), head_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, GRIDLN),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, GRIDLN),
    ]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0:
                styc.append(("BACKGROUND", (0, i), (-1, i), LIGHT2))
    t.setStyle(TableStyle(styc))
    story.append(t)
    story.append(Spacer(1, 8))

class Callout(Flowable):
    """Colored side-bar callout box (Safety / Tip / Note)."""
    def __init__(self, kind, title, lines, width=None):
        super().__init__()
        self.kind = kind
        self.title = title
        self.lines = lines if isinstance(lines, list) else [lines]
        self.width = width
        cfg = {
            "danger": (DANGER, DANGERBG, "SAFETY"),
            "tip":    (TEAL,   TIPBG,   "FIELD TIP"),
            "note":   (STEEL,  NOTEBG,  "NOTE"),
        }
        self.bar, self.bg, self.tag = cfg[kind]
        self._para = None

    def wrap(self, aw, ah):
        self.width = aw
        inner = aw - 22
        self._flows = []
        ts = ParagraphStyle("cot", parent=callout_title, textColor=self.bar)
        head = Paragraph("%s &nbsp;&mdash;&nbsp; %s" % (self.tag, self.title), ts) \
            if self.title else Paragraph(self.tag, ts)
        self._flows.append(head)
        for ln in self.lines:
            self._flows.append(Paragraph(ln, callout_body))
        self._h = 0
        self._sizes = []
        for f in self._flows:
            w, hh = f.wrap(inner, ah)
            self._sizes.append(hh)
            self._h += hh + 2
        self._h += 12
        return aw, self._h

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self.bg)
        c.setStrokeColor(self.bg)
        c.roundRect(0, 0, self.width, self._h, 4, fill=1, stroke=0)
        c.setFillColor(self.bar)
        c.rect(0, 0, 4, self._h, fill=1, stroke=0)
        y = self._h - 6
        for f, hh in zip(self._flows, self._sizes):
            y -= hh
            f.drawOn(c, 14, y)
            y -= 2
        c.restoreState()

def callout(kind, title, lines):
    story.append(Spacer(1, 2))
    story.append(Callout(kind, title, lines))
    story.append(Spacer(1, 8))

# ----------------------------------------------------------------------------
# Flowchart flowable (Link-Down decision tree)
# ----------------------------------------------------------------------------
class LinkDownFlowchart(Flowable):
    def __init__(self, width=6.6*inch):
        super().__init__()
        self.width = width
        self.height = 6.7 * inch

    def wrap(self, aw, ah):
        self.width = min(aw, 6.7 * inch)
        return self.width, self.height

    def _box(self, d, cx, cy, w, hh, text, fill, stroke, tcolor=colors.white,
             fs=8.2, rounded=True):
        x = cx - w / 2; y = cy - hh / 2
        r = Rect(x, y, w, hh, fillColor=fill, strokeColor=stroke, strokeWidth=1.1)
        if rounded:
            r.rx = 5; r.ry = 5
        d.add(r)
        lines = text.split("\n")
        total = len(lines) * (fs + 2)
        ty = cy + total / 2 - fs
        for ln in lines:
            s = String(cx, ty, ln, fontName="Helvetica-Bold", fontSize=fs,
                       fillColor=tcolor, textAnchor="middle")
            d.add(s)
            ty -= (fs + 2)

    def _diamond(self, d, cx, cy, w, hh, text, fs=7.8):
        pts = [cx, cy + hh/2, cx + w/2, cy, cx, cy - hh/2, cx - w/2, cy]
        d.add(Polygon(pts, fillColor=ACCENT, strokeColor=colors.HexColor("#b06f10"),
                      strokeWidth=1.1))
        lines = text.split("\n")
        total = len(lines) * (fs + 1)
        ty = cy + total / 2 - fs
        for ln in lines:
            d.add(String(cx, ty, ln, fontName="Helvetica-Bold", fontSize=fs,
                         fillColor=NAVY, textAnchor="middle"))
            ty -= (fs + 1)

    def _arrow(self, d, x1, y1, x2, y2, color=STEEL, label=None, lcolor=GREY):
        d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.2))
        import math
        ang = math.atan2(y2 - y1, x2 - x1)
        ah = 6
        left = (x2 - ah * math.cos(ang - 0.5), y2 - ah * math.sin(ang - 0.5))
        right = (x2 - ah * math.cos(ang + 0.5), y2 - ah * math.sin(ang + 0.5))
        d.add(Polygon([x2, y2, left[0], left[1], right[0], right[1]],
                      fillColor=color, strokeColor=color))
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            d.add(String(mx + 6, my, label, fontName="Helvetica-Bold",
                         fontSize=7, fillColor=lcolor, textAnchor="start"))

    def draw(self):
        d = Drawing(self.width, self.height)
        W = self.width
        cx = W * 0.42
        bw, bh = 2.5 * inch, 0.4 * inch
        # vertical layout coordinates (top to bottom), compressed to fit page
        ys = [6.42, 5.72, 5.02, 4.32, 3.62, 2.92, 2.18, 1.18, 0.34]
        ys = [v * inch for v in ys]

        # Start
        self._box(d, cx, ys[0], bw, bh, "LINK DOWN / NO LINK", NAVY, NAVY, fs=9)
        # Steps as process boxes with an escalate branch on the right
        steps = [
            ("1. Check optic status LEDs\n(both ends: is the port powered/enabled?)", STEEL),
            ("2. Confirm optic seated & compatible\n(right type: SR/LR/DR, speed, vendor)", STEEL),
            ("3. Inspect + clean both end-faces\n(scope first, one-click / wet-dry)", TEAL),
            ("4. Verify polarity & correct strand\n(TX->RX, A/B/C, ROLL if needed)", TEAL),
            ("5. Inspect labels & build record\n(A-side / Z-side match?)", STEEL),
            ("6. Measure light levels\n(power meter: dBm in spec? loss OK?)", STEEL),
        ]
        for i, (txt, col) in enumerate(steps):
            self._arrow(d, cx, ys[i] - bh/2, cx, ys[i+1] + bh/2)
            self._box(d, cx, ys[i+1], bw, bh, txt, col, col, fs=7.6)

        # Decision diamond
        dy = ys[7]
        self._arrow(d, cx, ys[6] - bh/2, cx, dy + 0.34*inch)
        self._diamond(d, cx, dy, 2.3*inch, 0.9*inch, "Link\nrestored?")

        # YES -> done (left/down)
        done_y = ys[8]
        self._arrow(d, cx, dy - 0.45*inch, cx, done_y + bh/2, color=TEAL, label="YES")
        self._box(d, cx, done_y, bw, bh,
                  "DOCUMENT & CLOSE\n(before/after photos, update records)",
                  TEAL, TEAL, fs=7.6)

        # NO -> escalate (right side)
        ex = W - 1.15 * inch
        self._arrow(d, cx + 1.15*inch, dy, ex, dy, color=DANGER, label="NO")
        self._box(d, ex, dy, 2.0*inch, 0.75*inch,
                  "ESCALATE\nOpen/loop-back test,\ntag bad optic or\njumper, notify NOC",
                  DANGER, DANGER, fs=7.4)
        d.drawOn(self.canv, 0, 0)

# ----------------------------------------------------------------------------
# Page furniture (cover, header/footer)
# ----------------------------------------------------------------------------
MANUAL_TITLE = "L2 Fiber Technician Field Manual"

def cover(canvas_obj, doc):
    c = canvas_obj
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # accent band
    c.setFillColor(TEAL)
    c.rect(0, PAGE_H - 3.9*inch, PAGE_W, 0.12*inch, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.rect(0, PAGE_H - 3.9*inch - 0.05*inch, PAGE_W, 0.05*inch, fill=1, stroke=0)

    # decorative fiber strands
    c.setStrokeColor(colors.HexColor("#26476b"))
    c.setLineWidth(1)
    for i in range(14):
        yy = 1.0*inch + i * 0.28*inch
        c.line(0, yy, PAGE_W, yy - 0.5*inch)

    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN, PAGE_H - 1.5*inch, "DATA CENTER OPERATIONS")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 40)
    c.drawString(MARGIN, PAGE_H - 2.35*inch, "L2 Fiber Technician")
    c.setFont("Helvetica-Bold", 40)
    c.drawString(MARGIN, PAGE_H - 3.0*inch, "Field Manual")

    c.setFillColor(colors.HexColor("#b9cbe0"))
    c.setFont("Helvetica", 13)
    c.drawString(MARGIN, PAGE_H - 3.55*inch,
                 "Your first 90 days — and a reference for years after.")

    # subtitle block near lower third
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, 3.15*inch, "Inside this manual:")
    c.setFillColor(colors.HexColor("#c9d7e8"))
    c.setFont("Helvetica", 10)
    lines = [
        "Data center layout, safety & PPE  •  fiber types & connectors  •  optics & polarity",
        "MPO deep-dive  •  reading build records  •  cleaning, testing & troubleshooting",
        "switching & networking basics  •  labeling with the Brady M511  •  documentation",
        "field checklists  •  200+ acronym glossary  •  hands-on practice labs",
    ]
    yy = 2.8*inch
    for ln in lines:
        c.drawString(MARGIN, yy, ln)
        yy -= 0.26*inch

    c.setFillColor(colors.HexColor("#7f95ad"))
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN, 0.85*inch,
                 "Vendor-neutral reference — always follow the approved engineering record, "
                 "site naming standard, and local safety procedure.")
    c.drawString(MARGIN, 0.62*inch, "Edition 1.0")
    c.restoreState()

def later_pages(canvas_obj, doc):
    c = canvas_obj
    c.saveState()
    # header
    c.setStrokeColor(GRIDLN)
    c.setLineWidth(0.6)
    c.line(MARGIN, PAGE_H - 0.62*inch, PAGE_W - MARGIN, PAGE_H - 0.62*inch)
    c.setFont("Helvetica", 7.7)
    c.setFillColor(GREY)
    c.drawString(MARGIN, PAGE_H - 0.55*inch, MANUAL_TITLE)
    prev = getattr(doc, "_chap_prev", {})
    title = ""
    for pg in sorted(prev):
        if pg <= doc.page:
            title = prev[pg]
        else:
            break
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.55*inch, title)
    # footer
    c.line(MARGIN, 0.62*inch, PAGE_W - MARGIN, 0.62*inch)
    c.setFont("Helvetica", 8)
    c.setFillColor(GREY)
    c.drawString(MARGIN, 0.44*inch, "Data Center Operations")
    c.drawRightString(PAGE_W - MARGIN, 0.44*inch, "Page %d" % doc.page)
    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(PAGE_W/2, 0.44*inch, "Verify against site records before any work")
    c.restoreState()

# ----------------------------------------------------------------------------
# Custom doc template to track current chapter + collect TOC entries
# ----------------------------------------------------------------------------
class ManualDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        super().__init__(filename, **kw)
        self._cur_chapter = ""
        self._chap_prev = {}
        self._chap_cur = {}
        fw = PAGE_W - 2*MARGIN
        fh = PAGE_H - 1.7*inch
        frame = Frame(MARGIN, 0.8*inch, fw, fh, id="main",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        cover_frame = Frame(0, 0, PAGE_W, PAGE_H, id="cover")
        self.addPageTemplates([
            PageTemplate(id="Cover", frames=[cover_frame], onPage=cover),
            PageTemplate(id="Normal", frames=[frame], onPage=later_pages),
        ])

    def build(self, flowables, **kw):
        # multiBuild runs this once per pass; carry the prior pass's page->chapter
        # map so the running header is correct on each chapter's first page.
        self._chap_prev = self._chap_cur
        self._chap_cur = {}
        return super().build(flowables, **kw)

    def afterFlowable(self, flowable):
        if hasattr(flowable, "_bookmark"):
            kind, num, title = flowable._bookmark
            if kind == "chap":
                self._cur_chapter = title
                self._chap_cur[self.page] = title
                key = "ch%d" % num
                self.canv.bookmarkPage(key)
                self.notify("TOCEntry", (0, "%d.  %s" % (num, title), self.page, key))
            elif kind == "sec":
                key = "sec%d" % id(flowable)
                self.canv.bookmarkPage(key)
                self.notify("TOCEntry", (1, title, self.page, key))

# ----------------------------------------------------------------------------
# ============================  CONTENT  =====================================
# ----------------------------------------------------------------------------

# ---- Front matter: TOC ----
story.append(NextPageTemplate("Normal"))
story.append(PageBreak())  # leave cover template
h("Table of Contents", toc_h)
story.append(HR(1, 2, ACCENT, pad=2))
spacer(8)
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle("toc0", fontName="Helvetica-Bold", fontSize=10.5, leading=17,
                   textColor=NAVY),
    ParagraphStyle("toc1", fontName="Helvetica", fontSize=8.8, leading=12.5,
                   textColor=GREY, leftIndent=18),
]
story.append(toc)

story.append(PageBreak())
h("How to use this manual", h2)
para("This manual is written for a Level-2 (L2) fiber technician working in a large "
     "enterprise or hyperscale data center. It is built to do two jobs at once: get a "
     "brand-new technician safely productive in their first 90 days, and serve as a "
     "quick-reference a senior technician can still reach for on the floor.", body)
para("Each chapter is self-contained. Reference tables, safety callouts, field tips, "
     "and checklists are designed to be found fast and read at a glance. The "
     "troubleshooting chapter includes a full yes/no decision flowchart so you can work "
     "a down link methodically without skipping steps.", body)
callout("note", "Vendor-neutral by design",
        ["This guide does not assume any single network-equipment vendor. Naming, port "
         "layouts, and acceptable values vary by site. <b>Always follow the approved "
         "engineering record, the site naming standard, and local safety procedure</b> "
         "over any general value printed here."])
callout("danger", "When in doubt, stop",
        ["If a step feels unsafe, if optics may be energized and you are unsure of the "
         "laser class, or if the build record does not match what you see in the field — "
         "<b>stop and escalate</b>. A five-minute question is cheaper than an outage or an eye injury."])

# =====================================================================
# CHAPTER 1 — DATA CENTER BASICS
# =====================================================================
chapter("Data Center Basics",
        "Orient yourself in the room before you touch a single fiber. Knowing the spaces, "
        "aisles, and coordinate system is how you find the right rack the first time.")

section("Data center spaces &mdash; the distribution hierarchy")
para("Structured cabling in a data center follows a hierarchy defined by TIA-942. Cabling "
     "flows from the entrance facility, through main and horizontal distribution areas, out "
     "to the equipment. Learn these zones — build records and cross-connect paths are "
     "described in these terms.", body)
ref_table(
    ["Zone", "Name", "What lives there"],
    [
        ["<b>MDA</b>", "Main Distribution Area", "Core routers/switches, the main cross-connect (MC), and often the carrier/entrance demarcation. The top of the cabling hierarchy."],
        ["<b>HDA</b>", "Horizontal Distribution Area", "Aggregation/leaf switches and the horizontal cross-connect (HC) that feeds a group of rows or a pod."],
        ["<b>EDA</b>", "Equipment Distribution Area", "The equipment cabinets themselves — servers, storage, top-of-rack switches. Where horizontal cabling terminates at the gear."],
        ["<b>ZDA</b>", "Zone Distribution Area", "An optional consolidation point between HDA and EDA — a passive patch zone that lets you re-home cabinets without re-pulling to the HDA."],
        ["<b>EF / MMR</b>", "Entrance Facility / Meet-Me Room", "Where outside-plant and carrier circuits enter and hand off to the data center. See Chapter 9."],
    ],
    [0.9*inch, 1.9*inch, 4.0*inch])

section("Hot aisle vs. cold aisle")
para("Cabinets are arranged so equipment air intakes face each other and exhausts face "
     "each other, creating alternating aisles:", body)
blist([
    "<b>Cold aisle</b> — the front of the cabinets. Cool supply air is delivered here "
    "(through perforated floor tiles or overhead). This is normally where you patch, because "
    "front-facing ports and the structured-cabling side usually live here.",
    "<b>Hot aisle</b> — the rear of the cabinets. Heated exhaust air collects here and "
    "returns to the CRAC/CRAH units. It can be significantly warmer and noisier. Power (PDUs) "
    "and rear cable management are often accessed here.",
    "<b>Containment</b> — many sites physically seal one aisle (doors + roof panels) to "
    "stop hot and cold air mixing. Close containment doors behind you; leaving them open hurts "
    "cooling for the whole row.",
])
callout("tip", "Read the airflow before you plan cabling",
        ["Slack loops, jumpers, and label flags should never block a perforated cold-aisle "
         "tile or a cabinet exhaust. Blocked airflow is one of the most common avoidable "
         "problems a cabling tech creates."])

section("White space vs. gray space")
blist([
    "<b>White space</b> — the raised-floor / equipment area where IT gear lives: "
    "cabinets, network rows, the cabling you work on daily.",
    "<b>Gray space</b> — the back-of-house infrastructure that supports white space: "
    "UPS rooms, switchgear, generators, CRAC/CRAH and chiller plant, battery rooms. Usually "
    "off-limits without specific authorization.",
])

section("Raised floor vs. overhead cable trays")
ref_table(
    ["Pathway", "Description", "Watch for"],
    [
        ["Raised floor", "Cabling (and sometimes cooling) runs in the plenum under removable floor tiles. Common in legacy and mixed facilities.", "Never leave a tile out of place; use a tile lifter; watch the open-tile fall hazard and airflow leakage."],
        ["Overhead trays", "Ladder rack and basket (wire) tray carry cabling above the cabinets. Common in modern high-density builds.", "Separate fiber, copper, and power layers; respect fill limits and bend radius at drop-offs."],
    ],
    [1.3*inch, 3.3*inch, 2.2*inch])

section("Cabinets, cages, suites, and rows")
blist([
    "<b>Cabinet / rack</b> — the individual enclosure (typically 42U–52U) holding "
    "equipment. A <i>cabinet</i> has doors and sides; an open <i>rack</i> (two- or four-post) "
    "does not.",
    "<b>Row</b> — a line of cabinets sharing hot/cold aisles, usually given a letter or "
    "number.",
    "<b>Cage</b> — a fenced, physically secured area enclosing one customer's cabinets in "
    "a shared (colocation) facility.",
    "<b>Suite / hall / data room</b> — a larger walled room containing many rows, often "
    "dedicated to one customer or one power/cooling domain.",
])

section("Rack numbering & reading room coordinates")
para("Every cabinet has an address. Conventions vary, but most sites use a grid: a "
     "row/column tile coordinate plus a cabinet ID, and a rack-unit (U) position inside the "
     "cabinet. Rack units are numbered <b>from the bottom up</b> (U1 at the floor).", body)
ref_table(
    ["Element", "Example", "Meaning"],
    [
        ["Room / hall", "DH2", "Data hall 2 within the building."],
        ["Grid tile", "AK14", "Floor-grid coordinate: column AK, row 14 — like reading a map."],
        ["Cabinet ID", "R07-C12", "Row 07, cabinet 12."],
        ["Rack position", "U34–U37", "Occupies rack units 34 through 37 (counted from the bottom)."],
        ["Full locate", "DH2 / R07-C12 / U34", "Combine them to walk straight to the device."],
    ],
    [1.4*inch, 1.7*inch, 3.7*inch])
callout("tip", "Confirm the aisle letter before you walk off",
        ["Grid labels are usually printed on floor tiles and on the tops/corners of cabinets. "
         "Note both the cold-aisle and hot-aisle face labels — they may differ, and a "
         "record may reference either side."])

# =====================================================================
# CHAPTER 2 — SAFETY
# =====================================================================
chapter("Safety",
        "Fiber, optics, lasers, ladders, lifts, and electricity all share your workspace. "
        "None of the work in this manual is worth an injury. Safety comes before schedule.")

callout("danger", "Never look into the end of a fiber or a live port",
        ["Optical transmitters emit <b>invisible</b> infrared light. You will see nothing and "
         "feel nothing while it damages your retina. Assume every fiber and every port is live "
         "until proven dark. Inspect end-faces only with a fiber scope — never with your eye."])

section("Laser safety (Class 1 optics)")
para("Most data center optics are <b>Class 1</b> — safe under normal operating conditions "
     "because power is low and the beam diverges quickly once it leaves the fiber. “Class 1” "
     "does <i>not</i> mean “no laser present.” Higher-power DWDM, amplified, or "
     "long-haul systems can reach hazardous classes (1M, 3R). Treat the class rating as a floor, "
     "not a guarantee.", body)
blist([
    "Know the system before you unplug it. Amplified/DWDM links carry far more power than a short-reach data link.",
    "Cap unused connectors and bulkheads. Dust caps also block stray light.",
    "Use a fiber inspection scope with built-in laser filtering — never a bare loupe or your eye.",
    "Follow any posted laser-safety signage and the site's optical-safety procedure.",
])

section("Eye safety & broken-fiber shard handling")
para("A cleaved or broken glass fiber is a nearly invisible splinter that will not work its way "
     "out and can enter the bloodstream. Treat scraps as sharp hazardous waste.", body)
blist([
    "Wear safety glasses whenever cleaving, cleaning, or handling bare fiber.",
    "Work over a dark, tacky <b>fiber-scrap mat</b> or into a labeled fiber-scrap container — never a normal trash can, never the floor.",
    "Never touch your eyes, face, or mouth while working. No food or drink at the bench.",
    "Use tweezers or tape to lift scraps; account for every cleaved end. Wipe the bench with tape when finished.",
    "Do not run fingers along a table to ‘find’ a shard — you will find it with your skin.",
])

section("Ladders, lifts & working at height")
blist([
    "Inspect ladders before use; never use a damaged one. Use the right height — do not stand on the top cap.",
    "Maintain three points of contact; face the ladder; keep your belt buckle between the rails (no overreaching).",
    "Use a fiberglass ladder near any electrical work.",
    "Lifts/scissor lifts: only operate if trained and authorized. Wear the harness where required, use outriggers, watch overhead obstructions and floor loading.",
    "Never carry tools in your hands while climbing — use a tool bag/hoist.",
])

section("PPE & ESD precautions")
ref_table(
    ["Item", "When", "Notes"],
    [
        ["Safety glasses", "Any fiber handling, cleaving, cleaning", "Primary defense against shards and stray light."],
        ["Closed-toe / safety shoes", "On the floor at all times", "Dropped rails, tiles, tools."],
        ["ESD wrist strap / heel straps", "Handling optics, line cards, electronics", "Bond to a grounded point before touching a transceiver's contacts."],
        ["Hearing protection", "Near generators, CRAC/CRAH, gray space", "High-density halls are loud."],
        ["Gloves (cut/nitrile)", "Pulling cable / handling chemicals", "Remove for fine fiber work where dexterity matters."],
    ],
    [1.7*inch, 2.2*inch, 2.9*inch])
callout("note", "ESD is invisible but real",
        ["A discharge too small to feel can degrade or kill an SFP or line card. Store optics in "
         "their <b>anti-static packaging</b>, handle by the body (not the contacts), and bond "
         "yourself to ground before touching sensitive electronics."])

section("Lockout / tagout (LOTO) awareness")
para("As an L2 fiber tech you generally are not the authorized energy-control person, but you "
     "must recognize and respect LOTO. A lock and tag on a breaker, PDU, or panel means an "
     "energy source is being controlled for someone's safety.", body)
blist([
    "Never remove, bypass, or operate a device that is locked or tagged out — for any reason.",
    "Only the person who applied a lock removes it.",
    "If your work requires a circuit that is under LOTO, stop and coordinate with the authorized worker/supervisor.",
])

section("Emergency procedures")
blist([
    "Know the nearest <b>EPO</b> (Emergency Power Off), fire exits, extinguishers, and assembly point <i>before</i> you need them.",
    "Never use an EPO except in a genuine life-safety emergency — it drops the entire room.",
    "Know how to report an incident and where the eyewash / first-aid stations are.",
    "For a suspected fiber-in-eye injury: do not rub; seek medical attention immediately and report it.",
])

# =====================================================================
# CHAPTER 3 — FIBER TYPES
# =====================================================================
chapter("Fiber Types",
        "Single-mode or multimode? Which grade? Match the fiber to the optic, the distance, "
        "and the build record — mismatches are a top cause of high loss and no-light faults.")

section("Single-mode (OS1 / OS2)")
para("Single-mode fiber (SMF) has a very small core (~9 microns) that carries one mode of "
     "light, giving extremely low loss over long distances. It is the default for data center "
     "backbones, inter-building, and long links. The jacket is conventionally <b>yellow</b>.", body)
ref_table(
    ["Grade", "Construction / use", "Typical reach"],
    [
        ["<b>OS1</b>", "Tight-buffered, indoor. Higher attenuation spec (~1.0 dB/km).", "Indoor / campus, shorter SMF runs."],
        ["<b>OS2</b>", "Loose-tube, indoor/outdoor. Lower attenuation (~0.4 dB/km).", "Long backbone, outside plant, DWDM. The modern default."],
    ],
    [0.9*inch, 3.5*inch, 2.2*inch])

section("Multimode (OM1 – OM5)")
para("Multimode fiber (MMF) has a larger core (50 or 62.5 microns) that carries many modes. "
     "It is cheaper to terminate and drives cheaper short-reach optics, but modal dispersion "
     "limits distance. Grades OM3–OM5 are laser-optimized (OM = optical multimode).", body)
ref_table(
    ["Grade", "Core", "Jacket (common)", "Bandwidth / reach highlights"],
    [
        ["OM1", "62.5 &micro;m", "Orange", "Legacy. 1G to ~300 m; very limited at 10G (~33 m)."],
        ["OM2", "50 &micro;m", "Orange", "Legacy. 10G to ~82 m."],
        ["OM3", "50 &micro;m", "Aqua", "Laser-optimized. 10G to 300 m; 40/100G (SR4) to ~100 m."],
        ["OM4", "50 &micro;m", "Aqua / violet", "Laser-optimized. 10G to 400 m; 40/100G to ~150 m."],
        ["OM5", "50 &micro;m", "Lime green", "Wideband (WBMMF) for SWDM; extends short-wave multi-lambda reach."],
    ],
    [0.7*inch, 0.8*inch, 1.3*inch, 3.6*inch])
callout("note", "Never mix core sizes",
        ["Joining 50 &micro;m to 62.5 &micro;m fiber causes large, direction-dependent loss. "
         "Keep OM3/OM4 (aqua) and OM1 (orange) plants separate, and match the optic's specified "
         "fiber type."])

section("Bend-insensitive fiber (BIF)")
para("Bend-insensitive fiber uses a modified cladding (a trench/ring index profile) so it "
     "leaks far less light at tight bends. It is common in data center patch cords and high-"
     "density cassettes where cables route through tight radii. It is still glass — respect "
     "the minimum bend radius; BIF raises the margin, it does not remove the rule.", body)

section("Ribbon fiber")
para("Ribbon cable bonds 12 (or more) fibers side-by-side in a flat ribbon so they can be "
     "<b>mass-fused</b> in a single splice and terminated directly into MPO arrays. It gives "
     "very high fiber counts in a small cable and fast splicing — the backbone of "
     "high-density MPO/MTP trunking.", body)

section("Cable construction: loose tube vs. tight buffer")
ref_table(
    ["Type", "Construction", "Best for"],
    [
        ["<b>Tight-buffered</b>", "Buffer material extruded directly onto the 250 &micro;m fiber (to 900 &micro;m). Flexible, easy to connectorize.", "Indoor patch cords, jumpers, intra-building. Easier direct termination."],
        ["<b>Loose-tube</b>", "Fibers float freely in gel- or dry-filled tubes, isolated from cable stress and temperature.", "Outside plant, long backbone, harsh/temperature-variable environments."],
    ],
    [1.4*inch, 3.4*inch, 2.0*inch])

section("Indoor vs. outdoor cable")
blist([
    "<b>Indoor</b> — rated for flame/smoke (e.g., riser <i>OFNR</i> or plenum <i>OFNP</i>). "
    "Plenum rating is required in air-handling spaces. Not built for moisture/UV.",
    "<b>Outdoor / OSP</b> — water-blocked, UV- and rodent-resistant, wider temperature range. "
    "Often gel-filled loose tube. Not flame-rated for interior runs.",
    "<b>Indoor/outdoor</b> — dual-rated so a single cable can transition into the building "
    "without a mandatory splice at the entrance. Check the local run-length limit for the "
    "outdoor-rated jacket inside the building.",
])
callout("danger", "Plenum rating is a fire-code requirement",
        ["Running non-plenum cable in a plenum air space can violate fire code and endanger "
         "life safety. Match the cable's flame rating to the space — verify before you pull."])

# =====================================================================
# CHAPTER 4 — CONNECTORS
# =====================================================================
chapter("Connectors",
        "The connector is where light crosses a gap — the most failure-prone point in the "
        "link. Know the form factor, the polish, and the orientation cold.")

section("Common connector form factors")
ref_table(
    ["Connector", "Name / latch", "Where you'll see it"],
    [
        ["<b>LC</b>", "Lucent Connector — small (1.25 mm ferrule), push-pull latch", "The data center workhorse. Duplex LC on nearly all SFP/SFP+/SFP28 optics. One leg TX, one RX."],
        ["<b>SC</b>", "Subscriber/Square — larger (2.5 mm), push-pull", "Older backbones, some carrier/ODF hand-offs, GPON."],
        ["<b>FC</b>", "Ferrule Connector — 2.5 mm, screw-on threaded", "Test equipment, high-vibration and legacy telco. Threaded = stable."],
        ["<b>ST</b>", "Straight Tip — 2.5 mm, bayonet twist-lock", "Legacy multimode, older campus/building plant."],
        ["<b>MPO / MTP</b>", "Multi-fiber Push-On — rectangular array (8/12/16/24 fiber)", "High-density trunks, 40/100/400G breakouts, cassettes. See Chapter 7."],
    ],
    [0.9*inch, 2.6*inch, 3.3*inch])
callout("note", "MTP is a brand of MPO",
        ["<b>MTP&reg;</b> is US Conec's high-performance, intermateable implementation of the "
         "generic <b>MPO</b> connector. They mate together; MTP just specifies tighter tolerances, "
         "a floating ferrule, and better pin design. In records the terms are often used "
         "interchangeably — verify pin gender and polarity regardless of the name used."])

section("Polish: APC vs. UPC")
para("The end-face polish controls how much light reflects back at the connection "
     "(<i>reflectance / return loss</i>). This is color-coded and <b>must not be mixed</b>.", body)
ref_table(
    ["Polish", "Boot color", "End-face", "Use / return loss"],
    [
        ["<b>UPC</b>", "Blue (SMF) / Aqua-Beige (MMF)", "Ultra Physical Contact — flat, slight dome", "Digital/data links. Return loss ≥ ~50 dB."],
        ["<b>APC</b>", "Green", "Angled Physical Contact — 8&deg; angle", "RF/analog video, PON, high-sensitivity SMF. Reflections bounce into cladding. Return loss ≥ ~60 dB."],
    ],
    [0.7*inch, 1.9*inch, 2.4*inch, 1.9*inch])
callout("danger", "Never mate APC to UPC",
        ["Green (APC) mates only to green (APC). Forcing an 8&deg; angled ferrule against a flat "
         "UPC ferrule creates a large air gap — huge insertion loss, bad reflectance, and you "
         "can <b>physically damage both end-faces</b>. If a green boot meets a blue boot, stop."])

section("MPO gender & keying")
para("MPO connectors have a mechanical <b>key</b> (a raised tab) on one side of the housing, "
     "and are either pinned or unpinned. Get these wrong and the array will not mate correctly.", body)
blist([
    "<b>Male (pinned)</b> — has two guide pins that align the ferrules. <b>Female "
    "(unpinned)</b> — has the holes the pins seat into.",
    "<b>Rule: opposite genders mate.</b> Male-to-female. Two males will not seat; two females "
    "have nothing to align them. Cassettes are usually pinned, so trunks are usually unpinned "
    "— <i>but verify</i>.",
    "<b>Key-up / key-down</b> describes how the key tab sits relative to the adapter. Key-up to "
    "key-down mating flips the fiber positions and is central to MPO polarity (Chapters 6 & 7).",
    "The <b>white dot / ‘P1’ mark</b> on the connector body identifies fiber position 1 "
    "— use it to confirm orientation.",
])

# =====================================================================
# CHAPTER 5 — OPTICS
# =====================================================================
chapter("Optics (Transceivers)",
        "The optic converts electrical signals to light and back. Pick the right form factor, "
        "speed, and reach — and confirm both ends match.")

section("Pluggable form factors by speed")
ref_table(
    ["Form factor", "Lanes", "Typical speed", "Notes"],
    [
        ["<b>SFP</b>", "1", "1G (also 100M/155M)", "The original small form-factor pluggable. Duplex LC."],
        ["<b>SFP+</b>", "1", "10G", "Same cage as SFP, faster SerDes. Duplex LC."],
        ["<b>SFP28</b>", "1", "25G", "Single 25G lane. Duplex LC. Common leaf-to-server."],
        ["<b>QSFP+</b>", "4", "40G (4&times;10G)", "Quad SFP. MPO-12 (SR4) or duplex (LR4)."],
        ["<b>QSFP28</b>", "4", "100G (4&times;25G)", "Workhorse 100G. MPO (SR4/DR) or duplex (LR4/FR)."],
        ["<b>QSFP-DD</b>", "8", "200G / 400G", "Double-density (8 lanes), backward-compatible cage. MPO-8/12/16."],
        ["<b>OSFP</b>", "8", "400G / 800G", "Octal SFP — slightly larger, integrated heat-sink. High-end spine."],
    ],
    [1.0*inch, 0.6*inch, 1.4*inch, 3.5*inch])

section("Reach & type codes (the letters after the speed)")
para("Optic names encode reach and wavelength scheme. “100G-LR4” = 100 Gig, long "
     "reach, 4 wavelengths. Learn the suffixes:", body)
ref_table(
    ["Code", "Reach class", "Typical distance / medium"],
    [
        ["<b>SR</b>", "Short Reach", "Multimode. ~70–100 m (OM3/OM4). SR4 uses an MPO."],
        ["<b>DR</b>", "500 m Reach", "Single-mode, single lane per fiber. ~500 m."],
        ["<b>FR</b>", "2 km Reach", "Single-mode. ~2 km."],
        ["<b>LR</b>", "Long Reach", "Single-mode. ~10 km. Duplex LC."],
        ["<b>ER</b>", "Extended Reach", "Single-mode. ~30–40 km."],
        ["<b>ZR</b>", "Very long / coherent", "Single-mode. ~80 km+ (coherent ZR for DWDM metro)."],
    ],
    [0.7*inch, 1.5*inch, 4.3*inch])

section("BiDi, CWDM & DWDM — more traffic on fewer fibers")
blist([
    "<b>BiDi (bi-directional)</b> — sends and receives on <i>one</i> fiber using two "
    "different wavelengths and a WDM diplexer. Uses a <b>single simplex LC</b> instead of a "
    "duplex pair. Both ends must be a matched BiDi pair (e.g., Tx1270/Rx1330 on one end, the "
    "reverse on the other).",
    "<b>CWDM (Coarse WDM)</b> — combines several widely-spaced wavelengths (20 nm grid, "
    "typically up to ~18 channels) onto one fiber pair via a passive mux. Uncooled lasers, "
    "lower cost, metro distances.",
    "<b>DWDM (Dense WDM)</b> — packs many tightly-spaced channels (0.8/0.4 nm grid, the "
    "100/50 GHz ITU grid — 40, 80, 96+ channels) onto a fiber pair. Cooled, precise lasers; "
    "often amplified. The backbone of long-haul and high-capacity metro. <b>Can carry hazardous "
    "optical power — see Chapter 2.</b>",
])
callout("tip", "Match the optic to the fiber AND the far end",
        ["Three things must agree: (1) the optic type on both ends is identical, (2) the fiber "
         "plant matches the optic (SMF for LR/DR/FR, correct OM grade for SR), and (3) the "
         "connector/polish matches. A DWDM tunable optic also needs the <b>correct channel/"
         "wavelength</b> provisioned. When in doubt, read the build record."])

# =====================================================================
# CHAPTER 6 — POLARITY
# =====================================================================
chapter("Polarity",
        "Polarity is simply making sure every transmitter (TX) reaches the far-end receiver "
        "(RX). Get it wrong and you get ‘no light’ even though every fiber is perfect.")

section("TX / RX — the whole point")
para("A duplex link needs a crossover: TX on one end must land on RX at the other end, and "
     "vice-versa. In a simple duplex LC jumper this is the familiar ‘A-to-B’ flip. "
     "Across MPO trunks and cassettes, the same crossover must be preserved through every "
     "connection — that is what a <b>polarity method</b> guarantees.", body)

section("The three TIA polarity methods (Type A / B / C)")
ref_table(
    ["Method", "Trunk cable", "How the crossover happens", "Jumpers used"],
    [
        ["<b>Type A</b><br/>(Straight)", "Key-up to key-down; fiber 1&rarr;1, 12&rarr;12 straight through.", "The crossover is done in the <b>patch cords</b> — one straight (A-to-A) and one crossed (A-to-B).", "One A-A and one A-B duplex jumper."],
        ["<b>Type B</b><br/>(Reversed)", "Key-up to key-up; fiber 1&rarr;12, 12&rarr;1 (fully reversed).", "The crossover is built into the <b>trunk</b>. Both patch cords are the same type.", "Two A-to-A duplex jumpers."],
        ["<b>Type C</b><br/>(Pair-flipped)", "Adjacent pairs swapped: 1&harr;2, 3&harr;4 &hellip;", "The crossover is done per-pair inside the trunk.", "Two straight patch cords."],
    ],
    [0.95*inch, 1.9*inch, 2.4*inch, 1.35*inch],
    font=8.0)
callout("note", "One system, end to end",
        ["Pick a polarity method for the channel and keep it consistent from A-side to Z-side. "
         "Mixing methods (or mixing cassette types) inside one channel is the classic cause of a "
         "clean-looking link that carries no traffic. The build record specifies the method — "
         "follow it."])

section("ROLL, PROLL & the field fixes")
blist([
    "<b>ROLL (roll)</b> — physically swapping the duplex pair so TX and RX are exchanged "
    "(rolling the A/B). Done with a crossed (A-B) jumper or by flipping the duplex clip. A "
    "‘ROLL required’ note on a record means: cross this pair.",
    "<b>PROLL (pair roll)</b> — rolling at the pair level within an MPO/array (swapping "
    "pairs rather than a single duplex), used to correct array polarity through cassettes.",
    "<b>Default polarity</b> — the site's standard method (often Type B for MPO). If a "
    "record does not call out a roll, wire the default and verify with a light source.",
])

section("Working vs. Protection, physical vs. logical")
blist([
    "<b>Working vs. Protection</b> — protected circuits carry a primary (<i>working</i>) "
    "path and a backup (<i>protection</i>) path over diverse fibers/routes. Keep them on the "
    "documented diverse strands; never groom both onto the same trunk or you defeat the "
    "protection.",
    "<b>Physical polarity</b> — the actual TX/RX fiber mapping in the glass and connectors.",
    "<b>Logical polarity</b> — how the switch/optic lanes are assigned. On breakout/parallel "
    "optics (SR4, DR4) the <i>lane order</i> matters too; a physically correct MPO can still be "
    "lane-swapped. Verify link at the interface, not just light at the connector.",
])
callout("tip", "‘No light’ but every fiber tests clean? Suspect polarity.",
        ["If a VFL or power meter shows good continuity on each strand but the interface won't "
         "come up, you almost certainly have a polarity/roll issue, not a broken fiber. Re-check "
         "the method against the record before you replace anything."])

# =====================================================================
# CHAPTER 7 — MPO DEEP DIVE
# =====================================================================
chapter("MPO Deep Dive",
        "High-density links live or die on MPO detail: fiber count, pinning, numbering, and how "
        "cassettes fan the array out to duplex LC.")

section("Fiber counts and what drives them")
ref_table(
    ["Count", "Rows", "Drives", "Notes"],
    [
        ["<b>8-fiber</b>", "1", "40G-SR4, 100G-SR4, 400G-DR4 (as 8f)", "4 TX + 4 RX. Efficient for 4-lane optics — no wasted fibers."],
        ["<b>12-fiber</b>", "1", "Legacy 40/100G-SR4 (uses 8 of 12), 12f trunks", "The classic MPO. In SR4 the middle 4 fibers are unused."],
        ["<b>16-fiber</b>", "1", "400G-SR8, 800G", "16 fibers in a single-row MPO16 for 8-lane optics."],
        ["<b>24-fiber</b>", "2", "High-density trunking, 2&times;12 breakouts", "Two stacked rows of 12. Great backbone density; mind row/pin mapping."],
    ],
    [1.0*inch, 0.6*inch, 2.6*inch, 2.3*inch])
callout("note", "8-fiber vs. 12-fiber for SR4",
        ["A 4-lane optic (SR4) needs exactly 8 fibers. On a 12-fiber MPO it uses positions 1–4 "
         "(TX) and 9–12 (RX), leaving 5–8 dark. Native 8-fiber MPO carries the same link "
         "with no wasted strands — which is why 8-fiber is now common. Know which your plant uses."])

section("Pin numbering & fiber numbering")
para("Hold the connector with the <b>key up</b> and look at the end-face. Fiber position 1 (P1) "
     "is on the <b>left</b>, and positions increment to the right (1–12 for a single row). "
     "The white dot on the housing marks the P1 side. Flip the connector (key down) and the "
     "numbering mirrors — which is exactly why key orientation defines polarity.", body)
blist([
    "<b>Guide pins</b> sit outboard of fibers 1 and 12; the pinned (male) connector's pins seat "
    "into the unpinned (female) connector's holes.",
    "On a <b>2-row (24f)</b> MPO, the top row is 1–12 and the bottom row 13–24 (verify "
    "against the vendor's convention — some number by column).",
])

section("Breakout / fan-out cables")
para("A breakout (harness/fan-out) cable has one MPO on one end and several duplex LC (or "
     "multiple MPOs) on the other. It converts a parallel optic (e.g., 100G-SR4 on one QSFP28) "
     "into individual duplex links — e.g., one MPO-8 breaking out to 4&times;10G or 4&times;25G "
     "LC pairs to four separate switches or servers.", body)
ref_table(
    ["Cable", "Purpose"],
    [
        ["MPO &rarr; 4&times; LC duplex", "Break a 40G/100G-SR4 port into 4 independent 10G/25G links."],
        ["MPO &rarr; MPO trunk", "Point-to-point high-density backbone between cassettes/panels."],
        ["MPO conversion (2&times;12 &rarr; 3&times;8)", "Re-map 12-fiber trunks into 8-fiber optic assignments."],
    ],
    [2.3*inch, 4.5*inch])

section("Cassette layouts & pair mapping")
para("An MPO <b>cassette</b> is a small module that takes one or two MPO trunks on the rear and "
     "presents duplex LC ports on the front, doing the array-to-duplex fan-out and enforcing a "
     "polarity method internally. Cassettes come in matched types (often A and B) that must be "
     "paired correctly at each end of the channel.", body)
blist([
    "<b>Rear:</b> MPO (pinned/unpinned per design) carrying 8/12/24 fibers.",
    "<b>Front:</b> duplex LC ports, each mapped to a specific fiber pair in the trunk.",
    "<b>Pair mapping:</b> the cassette defines which trunk fibers become which LC pair and "
    "whether a crossover happens inside — this is how Type A/B/C is realized in practice.",
    "Use <b>matched cassettes end-to-end</b>; mixing an A-end with the wrong far-end module "
    "breaks polarity even when every physical fiber is intact.",
])
callout("tip", "Trace the pair, not just the port",
        ["When patching through cassettes, follow a single duplex pair from the front LC, into "
         "its trunk fibers, through the far cassette, to the far LC. That end-to-end trace is the "
         "fastest way to catch a polarity or pair-mapping mistake before you energize the link."])

# =====================================================================
# CHAPTER 8 — READING BUILD RECORDS
# =====================================================================
chapter("Reading Build Records",
        "The build record (WAN-link record) is your source of truth. Read every field the same "
        "way, every time — A-side first, then Z-side.")

section("The WAN-link line, field by field")
para("A build record describes one circuit as a pair of endpoints (A-side and Z-side) plus "
     "identity, priority, and physical placement fields. Read them in order and confirm each "
     "against the field before you touch anything.", body)
ref_table(
    ["Field", "What it tells you", "How to use it"],
    [
        ["<b>WAN Link</b>", "The logical circuit/service ID for the whole link.", "Your top-level reference on tickets and labels."],
        ["<b>Cable ID</b>", "The identifier of the physical cable/jumper.", "Match to the printed flag label on the cable."],
        ["<b>Cable Serial</b>", "The unique serial of that specific cable asset.", "For inventory/traceability; confirm on the cable jacket."],
        ["<b>Priority</b>", "Service criticality / change-window sensitivity.", "Drives how carefully/when you may touch it."],
        ["<b>Strand Index</b>", "Which fiber(s)/strand(s) within the cable are used.", "Pick the exact strand — wrong strand = no/low light."],
        ["<b>Rack</b>", "Cabinet location of the endpoint.", "Walk to it using room coordinates (Ch. 1)."],
        ["<b>Chassis</b>", "The device/shelf within the rack.", "Identify the specific equipment."],
        ["<b>Port</b>", "The interface/port on that chassis.", "The exact optic/adapter you connect to."],
        ["<b>Adapter</b>", "The bulkhead/coupler position on the panel/ODF.", "Where the jumper lands on the frame."],
        ["<b>Block</b>", "The panel/frame block grouping on the ODF.", "Narrows the adapter down to a physical block."],
        ["<b>Notes</b>", "Free-text: rolls, cautions, exceptions.", "Read every time — this is where ‘ROLL required’ lives."],
    ],
    [1.15*inch, 3.0*inch, 2.65*inch], font=8.2)

section("A-side and Z-side")
para("Every circuit has two ends. Read each end as a full sub-record: <b>Block, Rack, Chassis, "
     "Port, Adapter</b>, label state, ported state, and any polarity instruction. The A-side is "
     "conventionally the source/near end; the Z-side is the destination/far end.", body)

sub("Worked example")
story.append(Table(
    [[Paragraph("<b>WAN Link:</b> WL-DH2-0042 &nbsp; | &nbsp; <b>Cable ID:</b> JMP-1187 &nbsp; | "
                "<b>Serial:</b> C7A93K &nbsp; | &nbsp; <b>Priority:</b> P2", mono)],
     [Paragraph("<b>A-side:</b> DH2 / R07-C12 / Chassis SW-LEAF-07 / Port Et1/14 / "
                "ODF Blk B / Adapter 14 / Strand 14 &nbsp; <b>[LC-UPC]</b>", mono)],
     [Paragraph("<b>Z-side:</b> DH2 / R02-C03 / Chassis SW-SPINE-02 / Port Et3/2 / "
                "ODF Blk A / Adapter 09 / Strand 09 &nbsp; <b>[LC-UPC]</b>", mono)],
     [Paragraph("<b>Notes:</b> Working path. ROLL required at Z-side (A-B jumper). "
                "Clean &amp; scope both ends before mating.", mono)]],
    colWidths=[6.8*inch]))
story[-1].setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f6fa")),
    ("BOX", (0, 0), (-1, -1), 0.8, STEEL),
    ("INNERGRID", (0, 0), (-1, -1), 0.4, GRIDLN),
    ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
]))
spacer(8)
para("<b>Reading it:</b> This is circuit WL-DH2-0042, priority P2 (be careful, coordinate the "
     "window). Cable JMP-1187 runs from a leaf switch port Et1/14 in cabinet R07-C12 (landing on "
     "ODF Block B, adapter/strand 14) to a spine switch port Et3/2 in cabinet R02-C03 (ODF Block "
     "A, adapter/strand 9). Both ends are LC-UPC. The note says roll the pair at the Z-side, so "
     "use a crossed (A-B) jumper there, and scope/clean both ends first.", body)
callout("danger", "If the field doesn't match the record, stop",
        ["A mismatched serial, a missing label, an already-occupied adapter, or a green boot "
         "where the record says UPC — any discrepancy means <b>do not proceed</b>. Photograph "
         "it, escalate, and get the record corrected first."])

# =====================================================================
# CHAPTER 9 — COMMON DATA CENTER TERMS
# =====================================================================
chapter("Common Data Center Terms",
        "The vocabulary of frames, rooms, and pathways. Records and senior techs use these "
        "constantly — speak the language.")

section("Frames, rooms & hand-off points")
ref_table(
    ["Term", "Meaning"],
    [
        ["<b>ODF</b> — Optical Distribution Frame", "The fiber termination/patching frame or cabinet where trunks land and jumpers cross-connect. Your primary work surface."],
        ["<b>CCNR</b>", "A site-specific room/cage/row/network-area identifier used in some build records. <b>Its expansion differs by company</b> — treat it as a location key and verify against the site map / naming standard."],
        ["<b>MDF</b> — Main Distribution Frame", "The primary termination frame for a building/facility — where backbone and external circuits concentrate. Aligns with the MDA."],
        ["<b>IDF</b> — Intermediate Distribution Frame", "A satellite frame that serves a floor/zone and homes back to the MDF. Aligns with HDA/telecom rooms."],
        ["<b>BDF</b> — Building Distribution Frame", "The building-level frame between the MDF and the IDFs in campus designs."],
        ["<b>MMR</b> / Meet-Me Room", "A neutral room where carriers and tenants interconnect. Where cross-connects between different providers are made."],
        ["<b>POP</b> — Point of Presence", "The demarcation/access point where a carrier's network is reachable inside the facility."],
    ],
    [2.4*inch, 4.4*inch], font=8.4)

section("Cross-connect vs. interconnect vs. patch")
blist([
    "<b>Cross-connect</b> — a permanent cabled link between two termination points on "
    "distribution frames (often provider-to-provider in an MMR). Managed as an asset/record.",
    "<b>Interconnect</b> — a direct connection from one party's equipment to another's "
    "demarcation, without an intermediate frame.",
    "<b>Patch (patch cord / jumper)</b> — the flexible cable you plug between panel ports "
    "or from a panel to a device to establish/change a connection.",
    "<b>Patch panel / distribution frame</b> — the passive panel/frame of adapters that "
    "terminates structured cabling and presents ports for patching.",
])

section("Pathways & supports")
ref_table(
    ["Term", "Meaning"],
    [
        ["<b>Raceway</b>", "Any enclosed channel/duct that routes and protects cable."],
        ["<b>Ladder rack</b>", "Open ladder-style overhead tray (rungs) for heavier cable bundles; common for both copper and fiber runs."],
        ["<b>Basket / wire tray</b>", "Open mesh (wire basket) cable tray — lightweight, good airflow, easy drops. Widely used overhead for data cabling."],
        ["<b>Fiber raceway (fiber guide/duct)</b>", "Dedicated yellow duct system (troughs, spillovers, downspouts) protecting fiber jumpers with controlled bend radius across the room."],
    ],
    [2.0*inch, 4.8*inch], font=8.4)

# =====================================================================
# CHAPTER 10 — CABLING STANDARDS
# =====================================================================
chapter("Cabling Standards & Cable Management",
        "Standards keep a build clean, serviceable, and inspectable. Bend radius and slack "
        "discipline protect the light itself.")

section("The standards you'll hear referenced")
ref_table(
    ["Standard", "Scope"],
    [
        ["<b>TIA-568</b>", "Commercial building telecom cabling — the base standard for structured cabling components, performance, and connector color codes."],
        ["<b>TIA-942</b>", "Telecommunications infrastructure standard for <b>data centers</b> — defines the MDA/HDA/EDA/ZDA topology and tier/redundancy concepts."],
        ["<b>ISO/IEC 11801</b>", "The international counterpart to TIA-568 for generic cabling (you may see it on global sites)."],
        ["<b>TIA-606</b>", "Administration/labeling standard — how to identify and record cabling, pathways, and spaces (see Ch. 16–17)."],
    ],
    [1.4*inch, 5.4*inch], font=8.4)

section("Fiber color codes (TIA-598)")
para("Standard 12-fiber sequence — memorize it; it drives strand-index reading and MPO "
     "position 1–12:", body)
ref_table(
    ["Pos", "Color", "Pos", "Color"],
    [
        ["1", "Blue", "7", "Red"],
        ["2", "Orange", "8", "Black"],
        ["3", "Green", "9", "Yellow"],
        ["4", "Brown", "10", "Violet"],
        ["5", "Slate (grey)", "11", "Rose (pink)"],
        ["6", "White", "12", "Aqua"],
    ],
    [0.6*inch, 2.7*inch, 0.6*inch, 2.7*inch], font=8.6)
para("Mnemonic: <i>“Boys Only Get Better Skin Wearing Robes, Yet Very Rare Aqua.”</i> "
     "(Blue, Orange, Green, Brown, Slate, White, Red, Black, Yellow, Violet, Rose, Aqua.) The "
     "second 12 (13–24) repeat the colors with a tracer stripe.", body)

section("Bend radius — protect the light")
callout("danger", "The bend-radius rule",
        ["Exceeding the minimum bend radius causes <b>macrobend loss</b> (light leaks out of the "
         "core) and can permanently damage the glass. Common rules of thumb: <b>10&times; the cable "
         "OD unloaded</b>, and <b>15–20&times; under tension/pull</b>. Bend-insensitive fiber "
         "improves the margin but does not repeal the rule. When routing, no kinks, no zip-tie "
         "crush, no tight corners."])

section("Cable management, slack & ties")
blist([
    "<b>Velcro (hook-and-loop), not zip ties</b>, on fiber and data bundles. Velcro is "
    "re-openable and cannot be over-tightened. A crushed jumper under a zip tie is a classic "
    "hidden loss source.",
    "If zip ties are used anywhere, never cinch them tight on fiber — leave them loose "
    "enough to spin freely, and cut flush.",
    "<b>Slack management</b> — store service loops in the designated slack basket/spool at "
    "the documented radius. Enough slack to re-terminate or move a module, dressed neatly — "
    "not dumped in the bottom of the cabinet.",
    "Dress cables to the vertical/horizontal managers; keep fiber separate from heavy copper and "
    "away from power. Maintain airflow (Ch. 1).",
    "Support the weight — never let a jumper hang by the connector; strain relief lives at "
    "the manager, not the optic.",
])

# =====================================================================
# CHAPTER 11 — CLEANING FIBER
# =====================================================================
chapter("Cleaning Fiber",
        "The number-one cause of link problems is a dirty end-face. ‘Inspect, clean, "
        "inspect again’ — every mate, every time.")

callout("danger", "Inspect before you connect — always",
        ["A single sub-micron particle on a core can cause high loss, back-reflection, or "
         "<b>permanent pit damage</b> when two ferrules are mated and the dirt is ground in. "
         "Scope every end-face <b>before</b> insertion — and never scope a live fiber without "
         "a filtered inspection scope."])

section("The golden rule: Inspect → Clean → Inspect")
numlist([
    "<b>Inspect</b> the end-face with a fiber microscope/scope.",
    "If it fails, <b>clean</b> it (dry first, then wet-dry if needed).",
    "<b>Inspect again.</b> Only mate when it passes. If it still fails after cleaning, suspect "
    "damage — do not force a marginal end-face into service.",
])

section("Tools & methods")
ref_table(
    ["Tool / method", "Use"],
    [
        ["<b>One-click cleaner</b> (e.g., LC/MPO cassette pen)", "Fast dry-clean of a connector or in-adapter bulkhead. The everyday first tool. One push = one fresh cleaning stroke."],
        ["<b>Wet/dry method</b>", "For stubborn contamination (oils, films). A trace of optical-grade solvent on a wipe/stick, immediately followed by a dry pass. Never leave residue."],
        ["<b>Lint-free wipes / cleaning sticks (2.5 mm / 1.25 mm)</b>", "Reach ferrules and recessed bulkheads a one-click can't. Sticks sized to the ferrule."],
        ["<b>Inspection scope</b> (handheld or probe)", "Video/optical microscope with pass/fail zones. The only correct way to ‘look’ at an end-face."],
        ["<b>MPO-specific cleaners/scopes</b>", "Array end-faces need MPO-rated tools — a single-fiber cleaner won't clean all 12/24 positions."],
    ],
    [2.6*inch, 4.2*inch], font=8.4)

section("When to clean")
blist([
    "Before <b>every</b> connection — factory caps and ‘new’ cables are not clean.",
    "Any time a connector has been exposed (cap off, dropped, dragged on the floor).",
    "Whenever you measure high loss or high reflectance, or a link is flapping.",
    "Both the connector <b>and</b> the bulkhead/adapter you plug it into.",
])

section("End-face contamination — what you'll see on the scope")
ref_table(
    ["Pattern", "Likely cause", "Action"],
    [
        ["Round blobs / smears in the core", "Oils, skin, fingerprint", "Wet-dry clean; re-inspect."],
        ["Scattered specks/dust", "Airborne dust, cap debris", "Dry one-click clean; re-inspect."],
        ["Rings/haze around ferrule", "Solvent residue / evaporation", "Re-do wet-dry with a proper dry pass."],
        ["Pits, chips, cracks, scratches through core", "Physical damage / ground-in dirt", "Do not use — replace/re-terminate."],
    ],
    [2.2*inch, 2.4*inch, 2.2*inch], font=8.2)
callout("tip", "Contamination migrates",
        ["Dirt on one mated face transfers to the other. If one side was dirty, clean and "
         "re-inspect <b>both</b> the connector and the bulkhead before re-mating."])

# =====================================================================
# CHAPTER 12 — FIBER TESTING
# =====================================================================
chapter("Fiber Testing",
        "Prove the link before you trust it. Know which tool answers which question — and "
        "what a ‘good’ number looks like.")

section("The instruments")
ref_table(
    ["Tool", "Answers", "How it works"],
    [
        ["<b>VFL</b> — Visual Fault Locator", "“Is it continuous? Where's the break/bend?”", "Red 650 nm laser you shine down the fiber; light escapes at breaks, tight bends, or bad splices (glows). Great for tracing and finding gross faults over short distance."],
        ["<b>Light source + power meter</b> (OLTS)", "“What is the end-to-end insertion loss?”", "Known source at one end, calibrated meter at the other. An <b>OLTS</b> (Optical Loss Test Set) pairs them to measure loss (dB) vs. a reference — the acceptance test for a link."],
        ["<b>OTDR</b> — Optical Time-Domain Reflectometer", "“Where is each event, and how bad?”", "Sends pulses and times the back-scatter/reflections to map every splice, connector, bend, and break by <b>distance and loss</b>. Diagnostic/characterization tool."],
    ],
    [2.0*inch, 2.2*inch, 2.6*inch], font=8.2)
callout("note", "OLTS vs. OTDR — don't confuse them",
        ["<b>OLTS</b> gives the true end-to-end <i>insertion loss</i> a link will actually see — "
         "it is the pass/fail acceptance number. <b>OTDR</b> shows <i>where</i> loss happens along "
         "the fiber (event map) but its numbers are estimates from back-scatter. Certify with "
         "OLTS; troubleshoot location with OTDR."])

section("dB vs. dBm — get this right")
blist([
    "<b>dBm</b> is an <i>absolute</i> power level referenced to 1 mW. A power meter reading of "
    "–13 dBm is a real optical power. Receiver sensitivity and Tx power are in dBm.",
    "<b>dB</b> is a <i>relative</i> difference — a ratio, a loss or gain. Insertion loss of "
    "“2.5 dB” is how much weaker the signal got. (Loss dB = Tx dBm − Rx dBm.)",
    "Rule of thumb: <b>3 dB ≈ half the power</b>; 10 dB = one-tenth the power.",
])

section("Insertion loss & reflectance")
blist([
    "<b>Insertion loss</b> — total signal lost across the link/connector, in dB. Lower is "
    "better. Every connector pair and splice adds some.",
    "<b>Reflectance / return loss</b> — how much light bounces <i>back</i> from a connection. "
    "For return loss, <b>bigger (more negative reflectance) is better</b>; APC beats UPC here. "
    "Bad reflectance destabilizes lasers.",
])

section("Typical acceptance values (verify against your site & the link budget)")
ref_table(
    ["Item", "Common budget figure"],
    [
        ["Mated connector pair (loss)", "≤ 0.5 dB typical max (0.75 dB legacy); high-grade &lt; 0.3 dB."],
        ["Fusion splice", "≤ 0.1–0.3 dB."],
        ["SMF attenuation", "~0.4 dB/km (OS2) at 1310/1550 nm."],
        ["MMF attenuation", "~3.0 dB/km at 850 nm."],
        ["Connector return loss", "UPC ≥ 50 dB; APC ≥ 60 dB."],
        ["Rx power", "Must sit above the optic's Rx sensitivity with margin, below its overload."],
    ],
    [2.6*inch, 4.2*inch], font=8.4)
callout("danger", "The link budget is the authority",
        ["These are typical figures for orientation only. The <b>optic datasheet and the "
         "engineered link budget</b> define pass/fail for a given circuit. Always compare your "
         "measured loss to the budgeted loss for <i>that</i> link."])

# =====================================================================
# CHAPTER 13 — TROUBLESHOOTING
# =====================================================================
chapter("Troubleshooting",
        "Work the problem methodically — cheapest, most-likely, least-invasive first. The "
        "flowchart keeps you from skipping a step under pressure.")

section("The Link-Down decision flowchart")
para("When a link is down or won't come up, follow this yes/no tree top-to-bottom. Do the cheap, "
     "reversible checks first (LEDs, clean, polarity) before you swap hardware or escalate.", body)
story.append(Spacer(1, 4))
story.append(KeepTogether(LinkDownFlowchart()))
story.append(Spacer(1, 6))

section("Fault-to-first-move quick reference")
ref_table(
    ["Symptom", "Most likely", "First moves"],
    [
        ["<b>LOS</b> (Loss of Signal)", "No light reaching Rx — dark fiber, unplugged/disabled far end, dirty/broken connector, wrong strand.", "Confirm far-end port is up & optic seated; scope/clean both ends; verify strand vs. record; measure Rx power."],
        ["<b>LOF</b> (Loss of Frame)", "Light is present but framing is bad — speed/encoding mismatch, marginal signal, wrong optic type.", "Check both ends run the same speed/type; check Rx power margin; look for errors/CRC; clean & re-scope."],
        ["<b>High attenuation</b>", "Dirty end-face, macrobend, bad splice/connector, over-long run.", "Inspect & clean; check for tight bends/kinks/zip-tie crush; OLTS the link; OTDR to locate the event."],
        ["<b>No light at all</b>", "Broken fiber/jumper, wrong strand, disabled/failed optic, TX off.", "VFL to confirm continuity/find break; verify strand; confirm far-end TX enabled; swap suspect jumper."],
        ["<b>Dirty connector</b>", "Contamination on ferrule/bulkhead.", "Inspect → clean → inspect (Ch. 11), both sides."],
        ["<b>Wrong strand</b>", "Patched to the wrong adapter/strand index.", "Re-read A/Z strand index; trace with VFL; re-patch to documented strand."],
        ["<b>Wrong polarity / ROLL</b>", "TX not reaching RX though fibers test clean.", "Check polarity method vs. record; apply ROLL/PROLL; re-verify at the interface (Ch. 6)."],
        ["<b>Bad optic</b>", "Failed/degraded transceiver, wrong type provisioned.", "Check optic type matches far end; read diagnostics (DDM) if available; swap with known-good same type."],
        ["<b>Broken jumper</b>", "Crushed/kinked/over-bent or damaged connector.", "Inspect jacket & end-faces; VFL; replace with a scoped, clean, correct-polish jumper."],
        ["<b>Incorrect documentation</b>", "Field doesn't match record.", "Photograph the discrepancy; do not force a fit; escalate to correct the record before proceeding."],
    ],
    [1.4*inch, 2.6*inch, 2.8*inch], font=7.9)
callout("tip", "Change one thing at a time",
        ["Make a single change, then re-test. Swapping the optic, the jumper, and re-patching all "
         "at once means you'll never know what fixed (or broke) it — and you may introduce a "
         "new fault. Isolate, verify, document."])

# =====================================================================
# CHAPTER 14 — SWITCH BASICS
# =====================================================================
chapter("Switch Basics",
        "You plug fiber into switches all day — enough Layer-2 to read an interface, know a "
        "link light, and speak with the network team.")

section("Interfaces & naming")
blist([
    "<b>Ethernet interfaces</b> are named by speed/slot/port. Conventions vary by vendor but "
    "follow a pattern, e.g., <b>Et1/14</b> (Ethernet, module 1, port 14), <b>Gi0/1</b> "
    "(GigabitEthernet), <b>Te</b>/<b>Twe</b>/<b>Hu</b> for 10/25/100G. Read the record's port "
    "field the way the switch names it.",
    "A <b>breakout</b> port shows sub-interfaces (e.g., Et1/14/1–4) when a 40/100G port is "
    "split into 4 lanes — matches an MPO fan-out (Ch. 7).",
])

section("Speed negotiation & link")
blist([
    "<b>Auto-negotiation</b> lets two ends agree on speed/duplex. Optics/DACs often run at a "
    "fixed rate; a speed mismatch = no link or a flapping link.",
    "<b>Link light / status LED</b> — solid = link up; blinking = traffic; off = no link. "
    "Amber vs. green often distinguishes speed or a fault — check the vendor legend.",
    "A port can be <b>administratively down</b> (disabled in config) even with a perfect fiber. "
    "If LEDs are dark and the fiber is good, the far end may simply be shut.",
])

section("VLANs, trunks & access ports")
ref_table(
    ["Concept", "Meaning"],
    [
        ["<b>VLAN</b>", "A virtual LAN — a logical broadcast domain. Segments traffic without separate physical switches."],
        ["<b>Access port</b>", "Carries a single VLAN to an end device (server/host). Untagged."],
        ["<b>Trunk port</b>", "Carries many VLANs between switches using 802.1Q tags. Uplinks are usually trunks."],
        ["<b>LACP / port-channel</b>", "Bundles multiple physical links into one logical link for more bandwidth and redundancy (802.3ad). Both ends must agree; a mis-cabled member can break the bundle."],
    ],
    [1.7*inch, 5.1*inch], font=8.4)
callout("note", "Where the fiber tech and the network tech meet",
        ["You own Layer 1 (the light and the glass); the network team owns the config (VLANs, "
         "LACP, routing). When a link is physically perfect but won't pass traffic, the handoff "
         "is: <i>‘light levels are in spec and the interface sees light — please check "
         "the port config.’</i>"])

# =====================================================================
# CHAPTER 15 — NETWORKING BASICS
# =====================================================================
chapter("Networking Basics",
        "You work mostly at Layers 1–3, but the whole stack helps you troubleshoot and "
        "communicate. Here's the model and the core protocols.")

section("The OSI 7-layer model")
para("Developed by ISO in 1984, the Open Systems Interconnection model breaks communication into "
     "seven layers, from the physical wire up to the application. A device that works at a given "
     "layer also works at every layer below it (a router works at L3, so also L2 and L1). As a "
     "fiber tech you live at Layer 1 and touch Layers 2–3.", body)
ref_table(
    ["#", "Layer", "PDU", "Your world / examples"],
    [
        ["<b>7</b>", "Application", "Data", "HTTP, FTP, SSH, DNS — end-user services."],
        ["<b>6</b>", "Presentation", "Data", "Encoding/encryption — TLS/SSL, JPEG, MPEG."],
        ["<b>5</b>", "Session", "Data", "Session setup/teardown — SIP, NetBIOS."],
        ["<b>4</b>", "Transport", "Segment", "End-to-end delivery — <b>TCP</b>, <b>UDP</b>."],
        ["<b>3</b>", "Network", "Packet", "Logical addressing/routing — <b>IP</b>, ICMP, OSPF. <i>(You touch this.)</i>"],
        ["<b>2</b>", "Data Link", "Frame", "MAC/switching — Ethernet 802.3, VLANs, ARP. <i>(You touch this.)</i>"],
        ["<b>1</b>", "Physical", "Bits", "<b>Cabling, optics, connectors, voltage/light.</b> <i>(Your home.)</i>"],
    ],
    [0.4*inch, 1.3*inch, 0.9*inch, 4.2*inch], font=8.3)
callout("tip", "The layered-troubleshooting habit",
        ["Start at Layer 1 and work up: is there light and a clean, correct physical path? Then "
         "Layer 2 (does the interface see link/frames?), then Layer 3 (can it route/ping?). "
         "Fixing L1 first resolves the majority of ‘network’ tickets that land on a "
         "cabling tech."])

section("TCP/IP model — the practical stack")
para("The real-world Internet stack collapses OSI into four layers: <b>Application</b> "
     "(L5–7), <b>Transport</b> (TCP/UDP), <b>Internet</b> (IP), and <b>Link/Network Access</b> "
     "(Ethernet + physical). Same ideas, fewer boxes.", body)

section("Core protocols & addressing")
ref_table(
    ["Item", "What it is / does"],
    [
        ["<b>IPv4</b>", "32-bit logical address, dotted decimal (e.g., 172.16.0.1). ~4.3 billion addresses; uses subnets/CIDR."],
        ["<b>IPv6</b>", "128-bit address in hex groups (e.g., 2001:db8::1). Vast space, built-in autoconfig; increasingly standard in the DC."],
        ["<b>MAC address</b>", "48-bit hardware address burned into a NIC (e.g., aaaa.aaaa.aaaa). Layer-2 identity; switches learn these."],
        ["<b>ARP</b>", "Address Resolution Protocol — maps an IP to a MAC on the local segment so frames can be delivered."],
        ["<b>DNS</b>", "Domain Name System — resolves names (host.example.com) to IP addresses."],
        ["<b>DHCP</b>", "Dynamic Host Configuration Protocol — auto-assigns IP/mask/gateway/DNS to hosts."],
        ["<b>ICMP</b>", "Control/diagnostics — the basis of <b>ping</b> and <b>traceroute</b>. Your quick reachability test."],
        ["<b>Routing</b>", "Moving packets between networks (L3). Static routes or protocols like OSPF/BGP pick the path. The <b>default gateway</b> is a host's exit to other networks."],
    ],
    [1.2*inch, 5.6*inch], font=8.4)

# =====================================================================
# CHAPTER 16 — LABELING
# =====================================================================
chapter("Labeling",
        "A cable you can't identify is a cable you can't safely touch. Consistent labels are how "
        "the whole floor stays serviceable.")

section("The Brady M511 workflow (flag labels)")
para("The M511 is a rugged Bluetooth label printer paired to the <b>Brady Express Labels</b> app "
     "on a phone/tablet. Standard flow for a cable flag:", body)
numlist([
    "<b>Prepare the printer</b> — charge it, power on, install a compatible cartridge, close "
    "the cover fully.",
    "<b>Install the app</b> — Brady Express Labels (Android Play / iOS App Store).",
    "<b>Enable connection</b> — turn on Bluetooth and allow nearby-device permissions.",
    "<b>Connect to the M511</b> — select it in the app; match the serial when several appear.",
    "<b>Start a new label</b> — choose the wire/cable <b>Flag</b> design and confirm the "
    "installed supply.",
    "<b>Enter approved identification</b> — use the Cable/Circuit ID from the build record; "
    "add A/Z, port, strand, or priority <i>only when the labeling standard requires it</i>.",
    "<b>Check the preview</b> — confirm both printed halves, text orientation, and that "
    "nothing is clipped.",
    "<b>Print a test</b> — confirm it's complete, dark, centered, not clipped.",
    "<b>Prepare the cable</b> — clean/dry the jacket; don't place the flag over a latch, "
    "boot, or tight bend.",
    "<b>Apply the flag</b> — wrap the narrow center around the cable, align the two printed "
    "halves, press firmly from the cable outward.",
    "<b>Inspect</b> — it must read from the intended direction and match the record. "
    "<b>Reprint</b> anything smeared, clipped, crooked, or lifting.",
])

section("Label types")
ref_table(
    ["Type", "Use"],
    [
        ["<b>Flag label</b>", "Two printed halves wrap into a flag sticking off the cable — readable from both sides. Standard for patch cords/jumpers."],
        ["<b>Wrap (self-laminating) label</b>", "Printed area wraps around the cable, then a clear laminate tail self-covers it for durability. Good on thicker cables."],
        ["<b>Heat-shrink label</b>", "Slides on before termination and shrinks tight — permanent, abrasion-proof; ideal for harsh or high-handling spots."],
    ],
    [2.1*inch, 4.7*inch], font=8.4)

section("Naming conventions, QR & barcodes")
blist([
    "<b>Follow the site naming standard exactly</b> — don't invent formats. Consistency is "
    "what makes labels useful during an outage.",
    "Label <b>both ends</b> of every cable, and both faces where records may be read from either "
    "side.",
    "<b>QR / barcode labels</b> encode the Cable ID/asset so a scan pulls up the record in the "
    "DCIM/asset system — faster and error-free vs. typing. Print them from the approved "
    "template.",
    "Keep labels legible and durable — a smudged or curling label is worse than none because "
    "it invites a wrong assumption.",
])

# =====================================================================
# CHAPTER 17 — DOCUMENTATION
# =====================================================================
chapter("Documentation",
        "The work isn't done until the record is right. Good documentation is what lets the next "
        "tech (or future-you) trust the plant.")

section("Photos: before, during, after")
blist([
    "<b>Before</b> — capture the existing state (port occupancy, labels, cable dressing) "
    "<i>before</i> you change anything. Protects you if something was already wrong.",
    "<b>During</b> — photograph anything unexpected: a discrepancy, damage, an undocumented "
    "cable.",
    "<b>After</b> — the finished, dressed, labeled result showing the connection matches the "
    "record.",
])

section("Tickets, work orders & change control")
ref_table(
    ["Artifact", "Purpose"],
    [
        ["<b>Work order / task</b>", "The authorized instruction to do the work — scope, location, circuit, window."],
        ["<b>Change ticket</b>", "Change-management record authorizing a modification to production, with an approved window and back-out plan. Don't touch production without one when required."],
        ["<b>Closeout / as-built documentation</b>", "The completion package: what was done, test results (OLTS/scope), photos, updated records — submitted to close the task."],
    ],
    [2.2*inch, 4.6*inch], font=8.4)

section("Updating records & cable verification")
blist([
    "Update the <b>DCIM/records system</b> to reflect reality the moment work is complete — "
    "new patches, moved cables, decommissioned strands. A stale record is a future outage.",
    "<b>Cable verification</b> — confirm the physical cable, its label, both endpoints, "
    "strand, and polarity all agree with the record before you close. Trace end-to-end when in "
    "doubt.",
    "Attach test results (loss/scope) to the record where required — they are the evidence "
    "the link meets budget.",
])
callout("tip", "Leave it better than you found it",
        ["If you spot an undocumented cable or a wrong label while doing other work, flag it. "
         "Small corrections compound into a plant everyone can trust — and prevent the 2 a.m. "
         "outage caused by a record no one updated."])

# =====================================================================
# CHAPTER 18 — FIELD CHECKLISTS
# =====================================================================
chapter("Field Checklists",
        "Tear-out, repeatable sequences for the jobs you'll do most. Work top to bottom; don't "
        "skip a box.")

def checklist(title, items):
    sub(title)
    rows = [[Paragraph("☐", ParagraphStyle("cb", fontName="Helvetica", fontSize=11,
                       textColor=STEEL)), Paragraph(it, tbl_cell)] for it in items]
    t = Table(rows, colWidths=[0.3*inch, 6.5*inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#e2e8f0")),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

checklist("New circuit install", [
    "Read the build record fully; confirm WAN Link, Cable ID, priority, A/Z, strands, polish, polarity/ROLL notes.",
    "Confirm change ticket/work order is approved and you're in the window.",
    "Locate both endpoints by room coordinates; confirm rack/chassis/port/adapter match the record.",
    "Take BEFORE photos of both ends.",
    "Select correct jumper (length, fiber type, LC/MPO, UPC/APC, A-A vs A-B per ROLL).",
    "Inspect → clean → inspect both connectors and both bulkheads.",
    "Route with correct bend radius and slack; dress to managers; keep airflow clear.",
    "Mate connectors (respect key/gender on MPO); seat fully (click).",
    "Verify light/loss (OLTS or Rx power) against the link budget; confirm interface comes up.",
    "Apply approved labels (flag) at both ends; verify readable and correct.",
    "Take AFTER photos; update records/DCIM; attach test results; close the ticket.",
])

checklist("Fiber / jumper replacement", [
    "Confirm which strand/circuit and that it's approved to touch (priority/window).",
    "BEFORE photos; note existing polarity/polish and routing.",
    "Stage the correct replacement jumper (matched type/polish/polarity/length), inspected & clean.",
    "Disconnect old jumper; cap the bulkheads immediately.",
    "Inspect/clean bulkheads; inspect/clean new jumper both ends.",
    "Route, mate, verify light/loss and interface up.",
    "Re-label to match record; AFTER photos; update records; dispose old jumper properly.",
])

checklist("Cross-connect", [
    "Verify both termination points (frame/block/adapter) and the demarcation per the order.",
    "Confirm polish/type match end-to-end; stage correct patch cords.",
    "Inspect/clean every end-face and bulkhead in the path.",
    "Patch through, tracing the pair end-to-end; verify polarity.",
    "Test loss end-to-end; label per standard; document the cross-connect record.",
])

checklist("Decommission", [
    "Confirm the circuit is truly dead and approved for removal (ticket + records).",
    "Verify you have the RIGHT strand/cable — trace and double-check before removing.",
    "Photograph before removal.",
    "Remove jumper; cap bulkheads; remove labels.",
    "Update records to release the strand/ports; dispose cable properly; AFTER photo.",
])

checklist("Label audit", [
    "Walk the target rows/racks with the current records in hand.",
    "Confirm every cable is labeled both ends and legible.",
    "Verify each label's ID matches the record and the actual endpoints.",
    "Reprint/replace missing, wrong, smeared, or lifting labels (Brady M511).",
    "Log discrepancies and correct the records.",
])

checklist("Cleaning checklist", [
    "Have scope, one-click cleaner, wipes/sticks, and solvent ready.",
    "Inspect the end-face BEFORE anything.",
    "Dry-clean (one-click); re-inspect.",
    "If still dirty, wet-dry, then dry pass; re-inspect.",
    "Clean the mating bulkhead too; re-inspect both.",
    "Only mate when both pass; cap anything not immediately connected.",
])

checklist("Final verification (before you leave)", [
    "Connections match the build record (endpoints, strand, polarity, polish).",
    "Light/loss within budget; interface up and stable (no flapping/errors).",
    "Labels correct and readable at both ends.",
    "Cable dressed, correct bend radius, slack managed, airflow/containment restored.",
    "Records/DCIM updated; test results and photos attached; ticket closed.",
    "Work area clean — no fiber scraps, caps, or tools left behind.",
])

# =====================================================================
# CHAPTER 19 — ACRONYMS
# =====================================================================
chapter("Common Acronyms",
        "A field glossary. When a record or a senior tech throws an acronym at you, find it here.")

acr = [
    ("A-side", "Source/near end of a circuit record"),
    ("APC", "Angled Physical Contact (8&deg; polish, green)"),
    ("ARP", "Address Resolution Protocol (IP→MAC)"),
    ("AWG", "American Wire Gauge"),
    ("BDF", "Building Distribution Frame"),
    ("BER", "Bit Error Rate"),
    ("BGP", "Border Gateway Protocol"),
    ("BiDi", "Bi-Directional (single-fiber optic)"),
    ("BIF", "Bend-Insensitive Fiber"),
    ("BMS", "Building Management System"),
    ("CapEx", "Capital Expenditure"),
    ("CCNR", "Site-specific room/area location key (verify per site)"),
    ("CIDR", "Classless Inter-Domain Routing"),
    ("CO", "Central Office"),
    ("CRAC", "Computer Room Air Conditioner"),
    ("CRAH", "Computer Room Air Handler"),
    ("CRC", "Cyclic Redundancy Check"),
    ("CWDM", "Coarse Wavelength Division Multiplexing"),
    ("DAC", "Direct Attach Copper (cable)"),
    ("dB", "Decibel (relative power ratio / loss)"),
    ("dBm", "Decibel relative to 1 milliwatt (absolute power)"),
    ("DCIM", "Data Center Infrastructure Management"),
    ("DDM", "Digital Diagnostics Monitoring (optic)"),
    ("DHCP", "Dynamic Host Configuration Protocol"),
    ("DNS", "Domain Name System"),
    ("DOM", "Digital Optical Monitoring"),
    ("DR", "500 m single-mode reach (optic code)"),
    ("DWDM", "Dense Wavelength Division Multiplexing"),
    ("EDA", "Equipment Distribution Area"),
    ("EF", "Entrance Facility"),
    ("EOR", "End of Row (switch)"),
    ("EPO", "Emergency Power Off"),
    ("ER", "Extended Reach (optic code)"),
    ("ESD", "Electrostatic Discharge"),
    ("FC", "Ferrule Connector (threaded)"),
    ("FR", "2 km single-mode reach (optic code)"),
    ("FTP", "File Transfer Protocol"),
    ("Gbps", "Gigabits per second"),
    ("HC", "Horizontal Cross-connect"),
    ("HDA", "Horizontal Distribution Area"),
    ("ICMP", "Internet Control Message Protocol (ping)"),
    ("IDF", "Intermediate Distribution Frame"),
    ("IP", "Internet Protocol"),
    ("IPv4", "Internet Protocol version 4"),
    ("IPv6", "Internet Protocol version 6"),
    ("ISO", "International Organization for Standardization"),
    ("LACP", "Link Aggregation Control Protocol (802.3ad)"),
    ("LC", "Lucent Connector (1.25 mm ferrule)"),
    ("LED", "Light-Emitting Diode (status light)"),
    ("LOF", "Loss of Frame"),
    ("LOS", "Loss of Signal"),
    ("LOTO", "Lockout/Tagout"),
    ("LR", "Long Reach (~10 km, optic code)"),
    ("MAC", "Media Access Control (address)"),
    ("MC", "Main Cross-connect"),
    ("MDA", "Main Distribution Area"),
    ("MDF", "Main Distribution Frame"),
    ("MMF", "Multimode Fiber"),
    ("MMR", "Meet-Me Room"),
    ("MPO", "Multi-fiber Push-On (connector)"),
    ("MTP", "Brand of high-performance MPO (US Conec)"),
    ("NIC", "Network Interface Card"),
    ("nm", "Nanometer (wavelength)"),
    ("NOC", "Network Operations Center"),
    ("ODF", "Optical Distribution Frame"),
    ("OFNP", "Optical Fiber Nonconductive Plenum (rating)"),
    ("OFNR", "Optical Fiber Nonconductive Riser (rating)"),
    ("OLTS", "Optical Loss Test Set"),
    ("OM1–OM5", "Multimode fiber grades"),
    ("OpEx", "Operational Expenditure"),
    ("OS1/OS2", "Single-mode fiber grades"),
    ("OSFP", "Octal Small Form-factor Pluggable"),
    ("OSI", "Open Systems Interconnection (model)"),
    ("OSP", "Outside Plant"),
    ("OSPF", "Open Shortest Path First (routing)"),
    ("OTDR", "Optical Time-Domain Reflectometer"),
    ("PDU", "Power Distribution Unit"),
    ("POP", "Point of Presence"),
    ("PPE", "Personal Protective Equipment"),
    ("PROLL", "Pair Roll (array pair swap)"),
    ("QSFP", "Quad Small Form-factor Pluggable"),
    ("QSFP-DD", "QSFP Double Density (8 lanes)"),
    ("RJ45", "8-pin modular copper connector"),
    ("ROLL", "Rolled duplex pair (TX/RX swap)"),
    ("RL", "Return Loss"),
    ("RX / Rx", "Receive"),
    ("SC", "Subscriber/Square Connector (2.5 mm)"),
    ("SFP", "Small Form-factor Pluggable"),
    ("SFP+", "Enhanced SFP (10G)"),
    ("SFP28", "SFP for 25G"),
    ("SMF", "Single-Mode Fiber"),
    ("SR", "Short Reach (multimode, optic code)"),
    ("SSH", "Secure Shell"),
    ("ST", "Straight Tip Connector (bayonet)"),
    ("TCP", "Transmission Control Protocol"),
    ("TIA", "Telecommunications Industry Association"),
    ("TLS/SSL", "Transport Layer Security / Secure Sockets Layer"),
    ("TOR", "Top of Rack (switch)"),
    ("TX / Tx", "Transmit"),
    ("U / RU", "Rack Unit (1.75 in)"),
    ("UDP", "User Datagram Protocol"),
    ("UPC", "Ultra Physical Contact (flat polish, blue)"),
    ("UPS", "Uninterruptible Power Supply"),
    ("VFL", "Visual Fault Locator"),
    ("VLAN", "Virtual Local Area Network"),
    ("WAN", "Wide Area Network"),
    ("WBMMF", "Wideband Multimode Fiber (OM5)"),
    ("WDM", "Wavelength Division Multiplexing"),
    ("ZDA", "Zone Distribution Area"),
    ("ZR", "~80 km / coherent DWDM reach (optic code)"),
]
# render as two-column glossary tables
def acronym_columns(entries):
    half = (len(entries) + 1) // 2
    left = entries[:half]
    right = entries[half:]
    rows = []
    for i in range(half):
        l = left[i]
        lcell_k = Paragraph("<b>%s</b>" % l[0], ParagraphStyle("ak", parent=tbl_cell, fontSize=8.1))
        lcell_v = Paragraph(l[1], ParagraphStyle("av", parent=tbl_cell, fontSize=8.1))
        if i < len(right):
            r = right[i]
            rcell_k = Paragraph("<b>%s</b>" % r[0], ParagraphStyle("ak", parent=tbl_cell, fontSize=8.1))
            rcell_v = Paragraph(r[1], ParagraphStyle("av", parent=tbl_cell, fontSize=8.1))
        else:
            rcell_k = Paragraph("", tbl_cell); rcell_v = Paragraph("", tbl_cell)
        rows.append([lcell_k, lcell_v, rcell_k, rcell_v])
    t = Table(rows, colWidths=[0.95*inch, 2.45*inch, 0.95*inch, 2.45*inch], repeatRows=0)
    sty = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("LINEAFTER", (1, 0), (1, -1), 0.6, GRIDLN),
    ]
    for i in range(len(rows)):
        if i % 2:
            sty.append(("BACKGROUND", (0, i), (-1, i), LIGHT2))
    t.setStyle(TableStyle(sty))
    story.append(t)

acronym_columns(acr)

# =====================================================================
# CHAPTER 20 — PRACTICE LABS
# =====================================================================
chapter("Practice Labs",
        "Realistic exercises to build fluency. Work them with the earlier chapters open; answers "
        "follow each lab.")

def lab(n, title, scenario, task, answer):
    keep = []
    keep.append(Paragraph("Lab %d &mdash; %s" % (n, title), h3))
    keep.append(Paragraph("<b>Scenario.</b> %s" % scenario, body))
    keep.append(Paragraph("<b>Your task.</b> %s" % task, body))
    box = Table([[Paragraph("<b>Answer key.</b> %s" % answer,
                  ParagraphStyle("ans", parent=callout_body, fontSize=8.8))]],
                colWidths=[6.6*inch])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TIPBG),
        ("BOX", (0, 0), (-1, -1), 0.6, TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    keep.append(Spacer(1, 2))
    keep.append(box)
    keep.append(Spacer(1, 10))
    story.append(KeepTogether(keep))

lab(1, "Find the correct rack from a WAN-link record",
    "A record reads: <font face='Courier'>A-side: DH2 / R07-C12 / SW-LEAF-07 / Et1/14 / "
    "ODF Blk B / Adapter 14</font>.",
    "Describe exactly where you walk and what you confirm on arrival.",
    "Go to Data Hall 2, Row 07, Cabinet 12 (use the floor-grid tile labels to navigate). "
    "Confirm the chassis labeled SW-LEAF-07, locate port Et1/14, and confirm the ODF Block B, "
    "adapter 14 termination. Verify the cabinet/label match the record before touching anything.")

lab(2, "Determine which MPO fibers are used",
    "A 100G-SR4 optic (QSFP28) is installed on a <b>12-fiber</b> MPO trunk.",
    "Which fiber positions carry traffic, and which are dark?",
    "SR4 uses 4 TX + 4 RX = 8 fibers. On a 12-fiber MPO it uses positions <b>1–4 (TX)</b> "
    "and <b>9–12 (RX)</b>; positions <b>5–8 are unused</b>. (On a native 8-fiber MPO no "
    "positions are wasted.)")

lab(3, "Identify whether a ROLL is required",
    "You've patched a duplex LC link exactly per the strand indices. Every strand tests continuous "
    "on the VFL and power is good, but the switch interface stays down. The record's Notes field "
    "says nothing about polarity.",
    "What's the likely issue and what do you do?",
    "This is the classic polarity signature: good continuity per strand but no link = TX isn't "
    "reaching the far RX. A <b>ROLL</b> (crossed A-B jumper) is required on one end. Apply the "
    "roll, re-verify at the interface, and flag the record so the ROLL is documented.")

lab(4, "Choose the correct optic",
    "You must light a 2 km single-mode link between two switches. Available in the crib: 100G-SR4, "
    "100G-DR, 100G-FR, 100G-LR4.",
    "Which optic do you pull, and why not the others?",
    "Pick <b>100G-FR</b> — single-mode, ~2 km reach. SR4 is multimode/short-reach (won't "
    "reach and needs the wrong fiber). DR is only ~500 m. LR4 (~10 km) would work but is more "
    "optic than needed — use the engineered/specified optic; FR matches the 2 km requirement.")

lab(5, "Calculate expected insertion loss",
    "A single-mode link is 3 km of OS2 (0.4 dB/km) with 4 mated connector pairs (0.5 dB each) and "
    "2 fusion splices (0.15 dB each).",
    "What total insertion loss should you expect, and how do you judge pass/fail?",
    "Fiber: 3 &times; 0.4 = 1.2 dB. Connectors: 4 &times; 0.5 = 2.0 dB. Splices: 2 &times; 0.15 = "
    "0.3 dB. <b>Total ≈ 3.5 dB.</b> Pass/fail: compare your OLTS measurement to this budget "
    "AND to the optic's allowed link loss — measured should be at or below budget with margin.")

lab(6, "Trace a circuit from A-side to Z-side",
    "A protected circuit runs A-side (leaf, ODF Blk B adapter 14) to Z-side (spine, ODF Blk A "
    "adapter 9) with a ROLL at Z and a diverse protection path.",
    "List the trace steps to verify it end-to-end.",
    "1) At A, confirm chassis/port/ODF block/adapter/strand vs. record. 2) Follow the jumper into "
    "ODF Blk B adapter 14 and the trunk strand. 3) Trace the strand to the Z ODF Blk A adapter 9. "
    "4) Confirm the ROLL (A-B jumper) at Z. 5) Verify the protection path is on the documented "
    "<b>diverse</b> strands (not the same trunk). 6) OLTS/light-level both paths; confirm the "
    "interface is up.")

lab(7, "Label the cable correctly with a Brady M511",
    "You've completed the install in Lab 1 and need to flag both ends. The site standard says: "
    "Cable ID only on the flag.",
    "Outline the correct M511 steps and what you print.",
    "Print <b>JMP-1187</b> (the Cable ID) only — not the extra fields, since the standard "
    "says ID-only. In the app: connect to the M511 (match serial), choose the <b>Flag</b> design, "
    "enter the Cable ID, preview both halves, print a test (dark/centered/not clipped), clean/dry "
    "the jacket, wrap the flag clear of latch/boot/bend, press from the cable outward, and confirm "
    "it reads correctly at <b>both ends</b>.")

# =====================================================================
# Closing page
# =====================================================================
story.append(PageBreak())
h("Field Quick-Reference Card", h_chapter)
story.append(HR(1, 2, ACCENT, pad=2))
spacer(8)
sub("Before every mate")
para("<b>Inspect → Clean → Inspect.</b> Scope the end-face and the bulkhead; only mate "
     "when both pass.", body)
sub("Match four things")
para("Optic type (both ends) &nbsp;•&nbsp; fiber (SMF/OM grade) &nbsp;•&nbsp; connector "
     "&amp; polish (never APC↔UPC) &nbsp;•&nbsp; polarity/strand per record.", body)
sub("Link down? Work the tree")
para("LEDs › clean › polarity/strand › labels › light levels › escalate. "
     "Change one thing at a time; re-test after each.", body)
sub("The numbers")
para("3 dB ≈ half power &nbsp;•&nbsp; connector pair ≤ 0.5 dB &nbsp;•&nbsp; "
     "splice ≤ 0.1–0.3 dB &nbsp;•&nbsp; OS2 ≈ 0.4 dB/km &nbsp;•&nbsp; UPC "
     "RL ≥ 50 dB, APC ≥ 60 dB.", body)
sub("Always")
para("Follow the approved record and site standard. Respect bend radius. Label both ends. Update "
     "the record. Leave no fiber scraps. When in doubt, stop and ask.", body)
spacer(16)
story.append(HR(1, 1, GRIDLN))
spacer(6)
para("<i>This manual is a vendor-neutral training and reference aid. Site-specific procedures, "
     "safety rules, naming standards, and engineered link budgets always take precedence over the "
     "general guidance printed here.</i>", ParagraphStyle("fine", parent=body, fontSize=8.4,
     textColor=GREY))

# ----------------------------------------------------------------------------
# Build (two-pass for TOC)
# ----------------------------------------------------------------------------
doc = ManualDoc(OUT, pagesize=letter,
                title="L2 Fiber Technician Field Manual",
                author="Data Center Operations",
                subject="Field manual for L2 fiber technicians in the data center")
doc.multiBuild(story)
print("WROTE", OUT)
