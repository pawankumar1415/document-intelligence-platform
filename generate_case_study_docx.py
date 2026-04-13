"""
Run this script from the project root to generate the BSBI Platform Case Study DOCX.

    python generate_case_study_docx.py

Output: test-documents/BSBI_Platform_Case_Study.docx
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

# ── Colours ──────────────────────────────────────────────────────────────────
RED        = RGBColor(177, 18, 35)
DARK       = RGBColor(33, 33, 33)
MID_GREY   = RGBColor(110, 110, 110)
LIGHT_GREY = RGBColor(245, 245, 245)
WHITE      = RGBColor(255, 255, 255)
PINK_TINT  = "FDEAEA"   # challenge box background (hex)
RED_HEX    = "B11223"
DARK_HEX   = "212121"

FONT   = "Calibri"
FONT_H = "Calibri Light"

PROJECT_ROOT = Path(__file__).parent
LOGO_PATH    = PROJECT_ROOT / "frontend" / "public" / "bsbi-logo.jpeg"
OUT_PATH     = PROJECT_ROOT / "test-documents" / "BSBI_Platform_Case_Study.docx"


# ── Low-level helpers ─────────────────────────────────────────────────────────

def shade_cell(cell, hex_color: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shd)


def set_cell_margins(cell, top=80, bottom=80, left=120, right=120) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for side, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        tcMar.append(el)
    tcPr.append(tcMar)


def no_table_borders(table) -> None:
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "none")
        tblBorders.append(el)
    tblPr.append(tblBorders)


def red_rule(doc) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(8)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), "8")
    b.set(qn("w:space"), "1")
    b.set(qn("w:color"), RED_HEX)
    pBdr.append(b)
    pPr.append(pBdr)


def spacer(doc, pt: float = 6) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(0)
    run = p.add_run()
    run.font.size = Pt(pt)


def styled_run(para, text: str, *, bold=False, italic=False, size=11,
               color=None, font=FONT) -> None:
    r = para.add_run(text)
    r.bold   = bold
    r.italic = italic
    r.font.size = Pt(size)
    r.font.name = font
    r.font.color.rgb = color or DARK


def section_heading(doc, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after  = Pt(2)
    styled_run(p, text, bold=True, size=15, color=RED, font=FONT_H)


def body_para(doc, text: str, *, space_after=8) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(space_after)
    styled_run(p, text, size=10.5, color=DARK)


# ── Cover banner ──────────────────────────────────────────────────────────────

def add_cover(doc: Document) -> None:
    # Logo
    if LOGO_PATH.exists():
        try:
            doc.add_picture(str(LOGO_PATH), width=Pt(80))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.LEFT
            doc.paragraphs[-1].paragraph_format.space_after = Pt(10)
        except Exception:
            pass

    # Full-width red banner using a 1-col table
    banner = doc.add_table(rows=1, cols=1)
    no_table_borders(banner)
    banner.autofit = False
    banner.columns[0].width = Inches(6.5)
    cell = banner.cell(0, 0)
    shade_cell(cell, RED_HEX)
    set_cell_margins(cell, top=200, bottom=200, left=240, right=240)

    # "CASE STUDY" label
    tag_p = cell.paragraphs[0]
    tag_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    tag_run = tag_p.add_run("CASE STUDY")
    tag_run.bold = True
    tag_run.font.size = Pt(9)
    tag_run.font.name = FONT
    tag_run.font.color.rgb = WHITE
    tag_run.font.all_caps = True

    # Main title
    title_p = cell.add_paragraph()
    title_p.paragraph_format.space_before = Pt(8)
    title_run = title_p.add_run("BSBI Document Intelligence Platform")
    title_run.bold = True
    title_run.font.size = Pt(24)
    title_run.font.name = FONT_H
    title_run.font.color.rgb = WHITE

    # Subtitle
    sub_p = cell.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(6)
    sub_run = sub_p.add_run(
        "An internal tool to reduce document production time and improve quality across the practice"
    )
    sub_run.font.size = Pt(11)
    sub_run.font.name = FONT
    sub_run.font.color.rgb = RGBColor(255, 200, 200)

    spacer(doc, 10)

    # Client metadata row
    meta = doc.add_table(rows=1, cols=3)
    no_table_borders(meta)
    labels = ["BSBI Consulting", "Management Consulting", datetime.now(timezone.utc).strftime("%B %Y")]
    for i, label in enumerate(labels):
        c = meta.cell(0, i)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER if i == 1 else WD_ALIGN_PARAGRAPH.RIGHT
        r = p.add_run(label)
        r.font.size = Pt(9)
        r.font.name = FONT
        r.font.color.rgb = MID_GREY
        r.bold = (i == 0)

    spacer(doc, 6)
    red_rule(doc)


# ── Metric blocks ─────────────────────────────────────────────────────────────

def add_metrics(doc: Document) -> None:
    metrics = [
        ("~25 min",  "First-Draft SOW",      "down from a typical 3–4 hours"),
        ("14",       "Platform Features",    "across generation, validation and search"),
        ("5",        "Output Formats",       "SOW · PPT · Bid · Register · Case Study"),
        ("0 data",   "Leaves the Network",   "when running with local AI models"),
    ]

    table = doc.add_table(rows=1, cols=4)
    no_table_borders(table)
    table.autofit = False
    col_w = Inches(6.5 / 4)
    for col in table.columns:
        col.width = col_w

    for i, (value, label, sub) in enumerate(metrics):
        cell = table.cell(0, i)
        shade_cell(cell, RED_HEX if i % 2 == 0 else "8B0F1E")
        set_cell_margins(cell, top=160, bottom=160, left=100, right=100)

        # Remove first default paragraph and replace
        val_p = cell.paragraphs[0]
        val_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        val_r = val_p.add_run(value)
        val_r.bold = True
        val_r.font.size = Pt(26)
        val_r.font.name = FONT_H
        val_r.font.color.rgb = WHITE

        lbl_p = cell.add_paragraph()
        lbl_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        lbl_r = lbl_p.add_run(label)
        lbl_r.bold = True
        lbl_r.font.size = Pt(8)
        lbl_r.font.name = FONT
        lbl_r.font.color.rgb = WHITE

        sub_p = cell.add_paragraph()
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_r = sub_p.add_run(sub)
        sub_r.font.size = Pt(7)
        sub_r.font.name = FONT
        sub_r.font.color.rgb = RGBColor(255, 180, 180)

    spacer(doc, 14)


# ── Challenge box ─────────────────────────────────────────────────────────────

def add_challenge_box(doc: Document, bullets: list[str]) -> None:
    tbl = doc.add_table(rows=1, cols=2)
    no_table_borders(tbl)
    tbl.autofit = False
    tbl.columns[0].width = Inches(2.2)
    tbl.columns[1].width = Inches(4.3)

    # Left — red accent
    left = tbl.cell(0, 0)
    shade_cell(left, RED_HEX)
    set_cell_margins(left, top=160, bottom=160, left=160, right=120)

    lp = left.paragraphs[0]
    lp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    lr = lp.add_run("THE\nCHALLENGE")
    lr.bold = True
    lr.font.size = Pt(16)
    lr.font.name = FONT_H
    lr.font.color.rgb = WHITE

    sub_lp = left.add_paragraph()
    sub_lr = sub_lp.add_run(
        "Manual document production was consuming senior consultant time on every engagement."
    )
    sub_lr.font.size = Pt(8.5)
    sub_lr.font.name = FONT
    sub_lr.font.color.rgb = RGBColor(255, 200, 200)

    # Right — light tint with bullets
    right = tbl.cell(0, 1)
    shade_cell(right, PINK_TINT)
    set_cell_margins(right, top=160, bottom=160, left=160, right=160)

    first = True
    for bullet in bullets:
        p = right.paragraphs[0] if first else right.add_paragraph()
        first = False
        p.paragraph_format.space_after = Pt(5)
        dash = p.add_run("— ")
        dash.bold = True
        dash.font.size = Pt(10)
        dash.font.name = FONT
        dash.font.color.rgb = RED
        txt = p.add_run(bullet)
        txt.font.size = Pt(10)
        txt.font.name = FONT
        txt.font.color.rgb = DARK

    spacer(doc, 14)


# ── Numbered approach steps ───────────────────────────────────────────────────

def add_approach(doc: Document, steps: list[tuple[str, str]]) -> None:
    for i, (title, desc) in enumerate(steps, 1):
        row_tbl = doc.add_table(rows=1, cols=2)
        no_table_borders(row_tbl)
        row_tbl.autofit = False
        row_tbl.columns[0].width = Inches(0.65)
        row_tbl.columns[1].width = Inches(5.85)

        # Number box
        num_cell = row_tbl.cell(0, 0)
        shade_cell(num_cell, RED_HEX)
        set_cell_margins(num_cell, top=80, bottom=80, left=80, right=80)
        np = num_cell.paragraphs[0]
        np.alignment = WD_ALIGN_PARAGRAPH.CENTER
        nr = np.add_run(f"{i:02d}")
        nr.bold = True
        nr.font.size = Pt(14)
        nr.font.name = FONT_H
        nr.font.color.rgb = WHITE

        # Text cell
        txt_cell = row_tbl.cell(0, 1)
        set_cell_margins(txt_cell, top=80, bottom=80, left=140, right=80)
        shade_cell(txt_cell, "F9F9F9" if i % 2 == 0 else "FFFFFF")
        tp = txt_cell.paragraphs[0]
        tp.paragraph_format.space_after = Pt(0)
        title_r = tp.add_run(f"{title}  ")
        title_r.bold = True
        title_r.font.size = Pt(10.5)
        title_r.font.name = FONT
        title_r.font.color.rgb = RED
        desc_r = tp.add_run(desc)
        desc_r.font.size = Pt(10)
        desc_r.font.name = FONT
        desc_r.font.color.rgb = DARK

        spacer(doc, 3)

    spacer(doc, 10)


# ── Results two-column ────────────────────────────────────────────────────────

def add_results(doc: Document, paras: list[str], bullets: list[str]) -> None:
    tbl = doc.add_table(rows=1, cols=2)
    no_table_borders(tbl)
    tbl.autofit = False
    tbl.columns[0].width = Inches(3.7)
    tbl.columns[1].width = Inches(2.8)

    left = tbl.cell(0, 0)
    set_cell_margins(left, top=0, bottom=0, left=0, right=180)
    first = True
    for para in paras:
        p = left.paragraphs[0] if first else left.add_paragraph()
        first = False
        p.paragraph_format.space_after = Pt(8)
        r = p.add_run(para)
        r.font.size = Pt(10.5)
        r.font.name = FONT
        r.font.color.rgb = DARK

    right = tbl.cell(0, 1)
    shade_cell(right, "F5F5F5")
    set_cell_margins(right, top=120, bottom=120, left=140, right=140)
    first = True
    for bullet in bullets:
        p = right.paragraphs[0] if first else right.add_paragraph()
        first = False
        p.paragraph_format.space_after = Pt(6)
        check = p.add_run("✓  ")
        check.bold = True
        check.font.size = Pt(10)
        check.font.name = FONT
        check.font.color.rgb = RED
        txt = p.add_run(bullet)
        txt.font.size = Pt(9.5)
        txt.font.name = FONT
        txt.font.color.rgb = DARK

    spacer(doc, 12)


# ── Features table ────────────────────────────────────────────────────────────

def add_features_table(doc: Document, features: list[tuple[str, str]]) -> None:
    table = doc.add_table(rows=1 + len(features), cols=2)
    table.style = "Table Grid"
    table.autofit = False
    table.columns[0].width = Inches(2.0)
    table.columns[1].width = Inches(4.5)

    # Header row
    hdr = table.rows[0].cells
    for cell, text in zip(hdr, ["Feature", "What it does"]):
        shade_cell(cell, RED_HEX)
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
        p = cell.paragraphs[0]
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.name = FONT
        r.font.color.rgb = WHITE

    for ri, (name, desc) in enumerate(features):
        row = table.rows[ri + 1].cells
        shade = "F5F5F5" if ri % 2 == 0 else "FFFFFF"
        for ci, (cell, text, bold) in enumerate(zip(row, [name, desc], [True, False])):
            shade_cell(cell, shade)
            set_cell_margins(cell, top=70, bottom=70, left=100, right=100)
            p = cell.paragraphs[0]
            r = p.add_run(text)
            r.bold = bold
            r.font.size = Pt(9)
            r.font.name = FONT
            r.font.color.rgb = RED if bold else DARK

    spacer(doc, 12)


# ── Header / footer ───────────────────────────────────────────────────────────

def add_header_footer(doc: Document) -> None:
    for section in doc.sections:
        section.different_first_page_header_footer = False
        hdr = section.header
        hdr.is_linked_to_previous = False
        hp = hdr.paragraphs[0] if hdr.paragraphs else hdr.add_paragraph()
        hp.clear()
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hr = hp.add_run("BSBI Consulting  |  CONFIDENTIAL")
        hr.font.size = Pt(8)
        hr.font.name = FONT
        hr.font.color.rgb = MID_GREY

        ftr = section.footer
        ftr.is_linked_to_previous = False
        fp = ftr.paragraphs[0] if ftr.paragraphs else ftr.add_paragraph()
        fp.clear()
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fr = fp.add_run("BSBI Document Intelligence Platform  ·  bsbiconsulting.com")
        fr.font.size = Pt(8)
        fr.font.name = FONT
        fr.font.color.rgb = MID_GREY


# ── Main ──────────────────────────────────────────────────────────────────────

def build() -> None:
    doc = Document()

    # Margins
    for section in doc.sections:
        section.top_margin    = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin   = Inches(1.0)
        section.right_margin  = Inches(1.0)

    # Styles
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = DARK

    # ── Cover ──────────────────────────────────────────────────────────────
    add_cover(doc)

    # ── Metrics ────────────────────────────────────────────────────────────
    add_metrics(doc)

    # ── Background ─────────────────────────────────────────────────────────
    section_heading(doc, "About the Platform")
    red_rule(doc)
    body_para(doc,
        "BSBI Consulting works across housing, financial services, local government and healthcare, "
        "and like most consultancies, document production is a significant part of what we do. "
        "Statements of Work, bid responses, presentation decks, programme reports — these go out on "
        "almost every engagement, and getting them right matters. They reflect the quality of our "
        "thinking and, frankly, the first impression a client gets of us."
    )
    body_para(doc,
        "Over time it became clear that we were spending more time than we should on the mechanics "
        "of document production — formatting, applying branding, rewriting sections that had already "
        "been written well on a previous job. We built this platform to address that. It is not a "
        "replacement for good thinking or good writing. It is a tool that handles the repetitive "
        "parts so our consultants can focus on the parts that actually require their expertise."
    )
    body_para(doc,
        "The platform is built and used internally at BSBI. It connects to the AI providers we "
        "already use, works with documents we already produce, and fits into the way our teams "
        "actually work — rather than asking them to change how they work to accommodate new software."
    )

    # ── Challenge ──────────────────────────────────────────────────────────
    spacer(doc, 6)
    add_challenge_box(doc, [
        "Writing a first-draft SOW from scratch typically took a senior consultant 3–4 hours per engagement",
        "Branding was applied manually — different teams produced documents that looked noticeably different",
        "Good content from previous engagements rarely found its way into new ones — it just sat in old files",
        "There was no consistent way to check document quality before it went to a client",
        "Practice leaders had no visibility into whether quality was improving or declining over time",
        "Bid responses were particularly time-consuming, often built from scratch under deadline pressure",
    ])

    # ── What We Built ───────────────────────────────────────────────────────
    section_heading(doc, "What We Built")
    red_rule(doc)
    body_para(doc,
        "The platform is a web application that sits alongside our existing workflow. A consultant "
        "uploads a source document — a client brief, a project report, an RFP — and the platform "
        "uses that as the starting point for whatever they need to produce next. The AI does the "
        "first draft. The consultant reviews, edits, and approves. The output is a properly branded "
        "document ready to send.",
        space_after=10,
    )

    add_approach(doc, [
        ("Upload & Parse",
         "Supports PDF, DOCX and plain text. The platform reads the document, identifies its structure, "
         "and extracts key signals — objectives, risks, requirements, stakeholders — that inform the output."),
        ("Generate Deliverables",
         "Produces a branded SOW, PowerPoint deck, bid response, case study or document summary from "
         "the source material. Each output follows BSBI's visual identity without any manual formatting."),
        ("Validate Before Sending",
         "Documents can be run against a quality rubric before they leave. The platform scores "
         "the content, identifies specific issues, and — if needed — offers a suggested rewrite. "
         "The consultant decides what to use."),
        ("Compare Two Versions",
         "When a document goes through multiple drafts, it can be useful to understand exactly what "
         "changed and whether the changes were improvements. This feature scores both versions and "
         "highlights what shifted between them."),
        ("Extract Structured Data",
         "Any document can be scanned for specific entity types — risks, action items, requirements, "
         "stakeholders, decisions — and the results are exported as a formatted register. Useful for "
         "programme assurance reviews and due diligence work."),
        ("Clause Library",
         "When a consultant writes something well — a governance statement, a scope paragraph, a "
         "methodology description — it can be saved to a shared library and reused on future engagements. "
         "The library grows over time and is searchable by keyword."),
        ("Chat with Documents",
         "Consultants can ask plain-language questions about a document and get answers grounded in "
         "the actual content. Useful for quickly finding specific information in long programme reports "
         "without reading the whole thing."),
        ("Analytics",
         "A dashboard shows document activity, validation scores, and common issues across the practice. "
         "It is not sophisticated analytics — it is a simple, honest view of whether quality is "
         "heading in the right direction."),
    ])

    # ── Features table ─────────────────────────────────────────────────────
    section_heading(doc, "Feature Summary")
    red_rule(doc)
    spacer(doc, 4)
    add_features_table(doc, [
        ("SOW Generator",
         "Produces a structured Statement of Work from a project brief or source document. "
         "Covers scope, deliverables, assumptions, timeline and governance."),
        ("PPT Deck Generator",
         "Builds a presentation deck of up to 12 slides. Useful for turning a written brief "
         "into a client-ready slide deck without starting from a blank template."),
        ("Bid Response Generator",
         "Generates an 8-section proposal response from an RFP or opportunity document. "
         "Covers executive overview, approach, delivery plan, team, and next steps."),
        ("Case Study Generator",
         "Produces a client-facing case study with background, challenge, approach, "
         "headline metrics and outcome sections. Output is a branded DOCX."),
        ("Document Summary",
         "Summarises any document in one of four modes: executive summary, bullet points, "
         "narrative rewrite, or key insights. Useful for quickly digesting long documents."),
        ("Document Comparison",
         "Compares two versions of a document and returns an overall sentiment (improved / regressed / "
         "neutral), quality scores for each version, and a section-by-section change log."),
        ("Structured Extractor",
         "Extracts specific entity types from a document using configurable schemas. "
         "Five built-in schemas; custom schemas can be created for any entity type."),
        ("Clause Library",
         "A searchable store of reusable text blocks. Clauses can be added manually, extracted "
         "automatically by the AI, or copied from any document in the platform."),
        ("Document Chat",
         "Conversational Q&A over project documents using retrieval-augmented generation. "
         "Answers are grounded in the indexed document content, not generated from scratch."),
        ("Document Validation",
         "Two-layer quality check: a rubric-based compliance score and an internal consistency "
         "review. Results include a scored verdict, flagged issues, and an AI-suggested rewrite."),
        ("Batch Validation",
         "Validate a set of documents in one run. Accepts an Excel or CSV file listing the documents, "
         "or files selected directly from a connected SharePoint library."),
        ("Analytics Dashboard",
         "Shows validation quality over the past 30 days, the most common issues flagged across "
         "the practice, pass rates, and a recent activity feed."),
        ("SharePoint Integration",
         "Connect to a Microsoft SharePoint site and browse files directly within the platform. "
         "Selected files are imported and processed without needing to download them manually."),
        ("Multi-LLM Support",
         "Works with OpenAI, Groq, Azure OpenAI and local Ollama models. The user selects the "
         "provider and model per session. Local models mean no data leaves the environment."),
    ])

    # ── Results ────────────────────────────────────────────────────────────
    section_heading(doc, "Where We Are Now")
    red_rule(doc)
    spacer(doc, 4)
    add_results(doc,
        paras=[
            "The most noticeable change has been in how long it takes to produce a first draft. "
            "A SOW that would typically take a senior consultant a morning now takes closer to "
            "20–30 minutes, including review. That time goes back into the engagement itself.",
            "Bid responses, which were previously built under pressure from a blank document, "
            "now start from a structured draft. The output still needs a consultant's judgement "
            "and editing — the platform does not remove that step — but it removes the painful "
            "blank-page problem that slows most bids down.",
            "The clause library is probably the feature that has changed behaviour most quietly. "
            "Good paragraphs from previous engagements are now actually reused, rather than sitting "
            "in old files no one goes back to look at. The library grows with every engagement.",
            "The validation layer has been useful less for catching critical errors and more for "
            "giving consultants a structured second opinion before something goes to a client. "
            "Knowing a document has been reviewed against a rubric, even an imperfect one, "
            "adds a degree of confidence that was not there before.",
        ],
        bullets=[
            "First-draft SOW time reduced from ~4 hours to ~25 minutes",
            "Consistent branding on every output, without manual effort",
            "Clause library in active use across the practice",
            "Bid responses now start from a structured draft",
            "Document quality visible and trackable over time",
            "Works with local AI models — no data leaves the network",
        ],
    )

    # ── Honest Notes ───────────────────────────────────────────────────────
    section_heading(doc, "A Few Honest Notes")
    red_rule(doc)
    body_para(doc,
        "The platform produces first drafts, not finished documents. Everything it generates needs "
        "a consultant to review it, edit it, and take ownership of what goes out. We have been "
        "deliberate about this — the goal was never to remove human judgement from the process, "
        "just to reduce the time spent on the mechanical parts."
    )
    body_para(doc,
        "The quality of the output depends on the quality of the source document. If the input is "
        "vague or thin, the output will reflect that. The platform works best when there is something "
        "substantive to work from — a detailed brief, a completed discovery report, a proper RFP."
    )
    body_para(doc,
        "We are still learning what works and what does not. Some features — the clause library, "
        "the validation layer — have become a natural part of how people work. Others are used "
        "occasionally. That is fine. The platform is a tool, and like most tools, its value "
        "depends on using it for the right job."
    )

    # ── Technology ─────────────────────────────────────────────────────────
    section_heading(doc, "Technology Stack")
    red_rule(doc)
    tech = [
        ("Frontend",         "React + TypeScript + Vite"),
        ("Backend",          "FastAPI (Python)"),
        ("App data",         "SQLite — users, projects, documents, artifacts, validation history"),
        ("Semantic search",  "PostgreSQL + pgvector — chunked document embeddings"),
        ("Embeddings",       "Hugging Face sentence-transformers or Ollama (fully local option)"),
        ("AI providers",     "OpenAI · Groq · Azure OpenAI · Ollama"),
        ("Document output",  "python-docx (DOCX) · python-pptx (PPTX)"),
        ("Integrations",     "Microsoft Graph API for SharePoint access"),
        ("Deployment",       "Self-hosted. With Ollama + local embeddings, no data leaves the server."),
    ]
    tbl = doc.add_table(rows=len(tech), cols=2)
    no_table_borders(tbl)
    tbl.autofit = False
    tbl.columns[0].width = Inches(1.9)
    tbl.columns[1].width = Inches(4.6)
    for ri, (label, value) in enumerate(tech):
        shade = "F5F5F5" if ri % 2 == 0 else "FFFFFF"
        lc = tbl.cell(ri, 0)
        vc = tbl.cell(ri, 1)
        for c in (lc, vc):
            shade_cell(c, shade)
            set_cell_margins(c, top=60, bottom=60, left=100, right=100)
        lp = lc.paragraphs[0]
        lr = lp.add_run(label)
        lr.bold = True
        lr.font.size = Pt(9)
        lr.font.name = FONT
        lr.font.color.rgb = RED
        vp = vc.paragraphs[0]
        vr = vp.add_run(value)
        vr.font.size = Pt(9)
        vr.font.name = FONT
        vr.font.color.rgb = DARK

    spacer(doc, 14)
    red_rule(doc)
    outro = doc.add_paragraph()
    outro.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = outro.add_run("BSBI Consulting  ·  Document Intelligence Platform  ·  bsbiconsulting.com")
    r.font.size = Pt(8.5)
    r.font.name = FONT
    r.font.color.rgb = MID_GREY

    add_header_footer(doc)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT_PATH))
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    build()