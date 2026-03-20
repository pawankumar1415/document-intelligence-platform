from __future__ import annotations

from pathlib import Path

from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches, Emu
from pptx.dml.color import RGBColor as PptxRGBColor
from pptx.util import Inches as PptxInches, Pt as PptxPt, Emu as PptxEmu


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGO_PATH = PROJECT_ROOT / "frontend" / "public" / "bsbi-logo.jpeg"
PPT_TEMPLATE_PATH = PROJECT_ROOT / "backend" / "data" / "NDA AI Narrative - Show&Tell.pptx"

# ── BSBI Brand Colour Palette ──────────────────────────────────────────────
BSBI_RED = RGBColor(177, 18, 35)
BSBI_DARK_GREY = RGBColor(51, 51, 51)
BSBI_MID_GREY = RGBColor(120, 120, 120)
BSBI_LIGHT_GREY = RGBColor(230, 230, 230)
BSBI_WHITE = RGBColor(255, 255, 255)
BSBI_ACCENT_DARK = RGBColor(40, 40, 40)

# PPT-specific colours (python-pptx uses its own RGBColor class)
PPT_RED = PptxRGBColor(177, 18, 35)
PPT_DARK_GREY = PptxRGBColor(51, 51, 51)
PPT_MID_GREY = PptxRGBColor(120, 120, 120)
PPT_LIGHT_GREY = PptxRGBColor(230, 230, 230)
PPT_WHITE = PptxRGBColor(255, 255, 255)
PPT_ACCENT_DARK = PptxRGBColor(40, 40, 40)
PPT_BODY_TEXT = PptxRGBColor(50, 50, 50)

# ── Font defaults ──────────────────────────────────────────────────────────
FONT_FAMILY = "Calibri"


def logo_exists() -> bool:
    return LOGO_PATH.exists() and LOGO_PATH.is_file()


def ppt_template_exists() -> bool:
    return PPT_TEMPLATE_PATH.exists() and PPT_TEMPLATE_PATH.is_file()


# ── DOCX helpers ───────────────────────────────────────────────────────────

def apply_docx_styles(document) -> None:
    """Configure all shared styles on a python-docx Document."""
    from docx.enum.text import WD_LINE_SPACING

    # Normal
    normal = document.styles["Normal"]
    normal.font.name = FONT_FAMILY
    normal.font.size = Pt(11)
    normal.font.color.rgb = BSBI_DARK_GREY
    pf = normal.paragraph_format
    pf.space_after = Pt(6)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.15

    # Heading 1
    h1 = document.styles["Heading 1"]
    h1.font.name = FONT_FAMILY
    h1.font.size = Pt(16)
    h1.font.bold = True
    h1.font.color.rgb = BSBI_RED
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(6)

    # Heading 2
    h2 = document.styles["Heading 2"]
    h2.font.name = FONT_FAMILY
    h2.font.size = Pt(13)
    h2.font.bold = True
    h2.font.color.rgb = BSBI_DARK_GREY
    h2.paragraph_format.space_before = Pt(12)
    h2.paragraph_format.space_after = Pt(4)

    # List Bullet
    try:
        lb = document.styles["List Bullet"]
        lb.font.name = FONT_FAMILY
        lb.font.size = Pt(11)
        lb.font.color.rgb = BSBI_DARK_GREY
        lb.paragraph_format.space_after = Pt(3)
    except KeyError:
        pass

    # Set margins to 1 inch all sides
    for section in document.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)


def add_styled_table(document, headers: list[str], rows: list[list[str]]) -> None:
    """Add a branded table with BSBI red header row and alternating row shading."""
    table = document.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.autofit = True

    # Header row
    header_cells = table.rows[0].cells
    for idx, text in enumerate(headers):
        cell = header_cells[idx]
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(10)
        run.font.name = FONT_FAMILY
        run.font.color.rgb = BSBI_WHITE
        _shade_cell(cell, "B11223")

    # Data rows
    for row_idx, row_data in enumerate(rows):
        row_cells = table.rows[row_idx + 1].cells
        shade = "F5F5F5" if row_idx % 2 == 0 else "FFFFFF"
        for col_idx, text in enumerate(row_data):
            if col_idx >= len(row_cells):
                break
            cell = row_cells[col_idx]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(text)
            run.font.size = Pt(10)
            run.font.name = FONT_FAMILY
            run.font.color.rgb = BSBI_DARK_GREY
            _shade_cell(cell, shade)

    # Space after table
    document.add_paragraph("")


def _shade_cell(cell, hex_colour: str) -> None:
    """Apply background shading to a table cell."""
    from docx.oxml import OxmlElement
    shading_elm = OxmlElement("w:shd")
    shading_elm.set(qn("w:fill"), hex_colour)
    shading_elm.set(qn("w:val"), "clear")
    cell._tc.get_or_add_tcPr().append(shading_elm)


def add_horizontal_rule(document) -> None:
    """Add a thin BSBI-red horizontal rule paragraph."""
    from docx.oxml import OxmlElement
    p = document.add_paragraph()
    p_pr = p._p.get_or_add_pPr()
    bottom_border = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), "6")
    b.set(qn("w:space"), "1")
    b.set(qn("w:color"), "B11223")
    bottom_border.append(b)
    p_pr.append(bottom_border)


def add_header_footer(document) -> None:
    """Add branded headers and footers to all sections of the document."""
    from docx.oxml import OxmlElement
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    for section in document.sections:
        section.different_first_page_header_footer = True

        # Header (non-first pages): BSBI logo left, "Confidential" right
        header = section.header
        header.is_linked_to_previous = False
        hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        hp.clear()
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = hp.add_run("BSBI Consulting  |  Confidential")
        run.font.size = Pt(8)
        run.font.color.rgb = BSBI_MID_GREY
        run.font.name = FONT_FAMILY

        # Footer: Page number centre
        footer = section.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        fp.clear()
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = fp.add_run()
        run.font.size = Pt(8)
        run.font.color.rgb = BSBI_MID_GREY
        run.font.name = FONT_FAMILY
        # Insert PAGE field
        fld_char_begin = OxmlElement("w:fldChar")
        fld_char_begin.set(qn("w:fldCharType"), "begin")
        run._r.append(fld_char_begin)
        instr_text = OxmlElement("w:instrText")
        instr_text.set(qn("xml:space"), "preserve")
        instr_text.text = " PAGE "
        run._r.append(instr_text)
        fld_char_end = OxmlElement("w:fldChar")
        fld_char_end.set(qn("w:fldCharType"), "end")
        run._r.append(fld_char_end)


# ── PPT helpers ────────────────────────────────────────────────────────────

def add_ppt_accent_bar(slide, presentation) -> None:
    """Add a thin BSBI-red bar at the bottom of a slide."""
    from pptx.util import Inches as I, Emu as E
    slide_width = presentation.slide_width or E(12192000)  # 13.333 inches default
    slide_height = presentation.slide_height or E(6858000)  # 7.5 inches default
    bar_height = I(0.3)
    left = E(0)
    top = slide_height - bar_height
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE.RECTANGLE
        left,
        top,
        slide_width,
        bar_height,
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = PPT_RED
    shape.line.fill.background()


def add_ppt_slide_number(slide, presentation) -> None:
    """Add a slide number text box in the bottom-right corner."""
    from pptx.util import Inches as I, Emu as E
    slide_height = presentation.slide_height or E(6858000)
    tb = slide.shapes.add_textbox(
        I(11.5),
        slide_height - I(0.45),
        I(1.0),
        I(0.3),
    )
    tf = tb.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    from pptx.enum.text import PP_ALIGN
    p.alignment = PP_ALIGN.RIGHT
    # Insert slide number field via XML
    from pptx.oxml.ns import qn as pptx_qn
    from lxml import etree
    fld = etree.SubElement(p._p, pptx_qn("a:fld"))
    import uuid
    fld.set("id", f"{{{uuid.uuid4()}}}")
    fld.set("type", "slidenum")
    rpr = etree.SubElement(fld, pptx_qn("a:rPr"))
    rpr.set("lang", "en-GB")
    rpr.set("sz", "900")
    solid = etree.SubElement(rpr, pptx_qn("a:solidFill"))
    srgb = etree.SubElement(solid, pptx_qn("a:srgbClr"))
    srgb.set("val", "787878")
    t = etree.SubElement(fld, pptx_qn("a:t"))
    t.text = "‹#›"
