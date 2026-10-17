"""Builds the newspaper-style PDF for one edition (reportlab Platypus)."""
import io
from concurrent.futures import ThreadPoolExecutor
from xml.sax.saxutils import escape

import requests
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, FrameBreak, Image, KeepTogether, NextPageTemplate,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

from config import HEADERS

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm
GAP = 0.6 * cm
COL_W = (PAGE_W - 2 * MARGIN - GAP) / 2
FULL_W = PAGE_W - 2 * MARGIN
INK = colors.HexColor("#1A1A1A")
RED = colors.HexColor("#8B1A1A")

S = {
    "lead_title": ParagraphStyle("lt", fontName="Times-Bold", fontSize=22, leading=25, spaceAfter=4),
    "title": ParagraphStyle("t", fontName="Times-Bold", fontSize=12.5, leading=14, spaceAfter=2),
    "meta": ParagraphStyle("m", fontName="Helvetica-Oblique", fontSize=7.5, textColor=colors.gray, spaceAfter=3),
    "body": ParagraphStyle("b", fontName="Times-Roman", fontSize=9.5, leading=11.5, alignment=TA_JUSTIFY, spaceAfter=3),
    "link": ParagraphStyle("l", fontName="Helvetica", fontSize=7.5, spaceAfter=8),
    "section": ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=10, textColor=RED, spaceBefore=6, spaceAfter=4),
    "box": ParagraphStyle("bx", fontName="Times-Roman", fontSize=10, leading=13, spaceAfter=3),
    "box_title": ParagraphStyle("bt", fontName="Helvetica-Bold", fontSize=10, textColor=RED, spaceAfter=4),
}


def clean(text) -> str:
    """Keep only characters the built-in PDF fonts can draw, then escape XML."""
    text = (text or "").replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.encode("cp1252", "replace").decode("cp1252")
    return escape(text)


def fetch_image(url: str):
    """Download one image and return JPEG bytes with its size, or None on any failure."""
    if not url:
        return None
    try:
        response = requests.get(url, headers=HEADERS, timeout=6)
        response.raise_for_status()
        image = PILImage.open(io.BytesIO(response.content)).convert("RGB")
        image.thumbnail((900, 900))
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=80)
        buffer.seek(0)
        return buffer, image.size
    except Exception:
        return None


def load_images(articles: list) -> dict:
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda a: fetch_image(a.get("image_url")), articles))
    return {a["id"]: r for a, r in zip(articles, results) if r}


def picture(images: dict, article: dict, width: float, max_height: float):
    found = images.get(article["id"])
    if not found:
        return None
    buffer, (w, h) = found
    height = width * h / w
    if height > max_height:
        width, height = width * max_height / height, max_height
    return Image(buffer, width=width, height=height)


def story(article: dict, images: dict, lead: bool = False) -> list:
    width = FULL_W if lead else COL_W
    parts = []
    pic = picture(images, article, width, 7 * cm if lead else 4 * cm)
    if pic:
        parts.append(pic)
        parts.append(Spacer(1, 3))
    parts.append(Paragraph(clean(article["title"]), S["lead_title" if lead else "title"]))
    parts.append(Paragraph(clean(f"{article['source']} | {article['topic']}"), S["meta"]))
    summary = article.get("summary") or ""
    if summary and not summary.startswith("http"):
        parts.append(Paragraph(clean(summary), S["body"]))
    link = escape(article["link"], {'"': "&quot;"})
    parts.append(Paragraph(f'<a href="{link}" color="#1a4f8b">Read the full story online</a>', S["link"]))
    return [KeepTogether(parts)]


def boxed(title: str, lines: list) -> Table:
    inner = [Paragraph(clean(title), S["box_title"])] + [Paragraph(clean(x), S["box"]) for x in lines]
    table = Table([[inner]], colWidths=[FULL_W])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, INK),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3EDE0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def build_pdf(user_name: str, date_label: str, articles: list,
              takeaways: list = None, editor_note: str = None) -> bytes:
    images = load_images(articles)
    buffer = io.BytesIO()

    def first_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(INK)
        canvas.setFont("Times-Bold", 30)
        canvas.drawCentredString(PAGE_W / 2, PAGE_H - 2.3 * cm, f"The {clean(user_name)} Morning Paper")
        canvas.setLineWidth(2)
        canvas.line(MARGIN, PAGE_H - 2.7 * cm, PAGE_W - MARGIN, PAGE_H - 2.7 * cm)
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(MARGIN, PAGE_H - 3.2 * cm, clean(date_label))
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 3.2 * cm, "Personalised for you")
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, PAGE_H - 3.5 * cm, PAGE_W - MARGIN, PAGE_H - 3.5 * cm)
        footer(canvas, doc)
        canvas.restoreState()

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.gray)
        canvas.drawCentredString(PAGE_W / 2, 0.9 * cm, f"Page {doc.page}  |  Made fresh for {clean(user_name)}")

    def later_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Times-Italic", 9)
        canvas.drawString(MARGIN, PAGE_H - 1.1 * cm, f"The {clean(user_name)} Morning Paper | {clean(date_label)}")
        canvas.line(MARGIN, PAGE_H - 1.25 * cm, PAGE_W - MARGIN, PAGE_H - 1.25 * cm)
        footer(canvas, doc)
        canvas.restoreState()

    top = PAGE_H - 3.8 * cm
    lead_h = 11.5 * cm
    bottom = 1.5 * cm
    first_frames = [
        Frame(MARGIN, top - lead_h, FULL_W, lead_h, id="lead", leftPadding=0, rightPadding=0),
        Frame(MARGIN, bottom, COL_W, top - lead_h - bottom, id="c1", leftPadding=0, rightPadding=0),
        Frame(MARGIN + COL_W + GAP, bottom, COL_W, top - lead_h - bottom, id="c2", leftPadding=0, rightPadding=0),
    ]
    body_top = PAGE_H - 1.6 * cm
    later_frames = [
        Frame(MARGIN, bottom, COL_W, body_top - bottom, id="l1", leftPadding=0, rightPadding=0),
        Frame(MARGIN + COL_W + GAP, bottom, COL_W, body_top - bottom, id="l2", leftPadding=0, rightPadding=0),
    ]
    doc = BaseDocTemplate(buffer, pagesize=A4, title=f"The {user_name} Morning Paper", author="Personal Morning Paper")
    doc.addPageTemplates([
        PageTemplate(id="first", frames=first_frames, onPage=first_page),
        PageTemplate(id="later", frames=later_frames, onPage=later_page),
    ])

    lead, rest = articles[0], articles[1:]
    wild = [a for a in rest if a.get("wildcard")]
    regular = [a for a in rest if not a.get("wildcard")]

    flow = [NextPageTemplate("later")]
    flow += story(lead, images, lead=True)
    if takeaways:
        flow.append(Spacer(1, 4))
        flow.append(boxed("TODAY'S 3 TAKEAWAYS", [f"{i}. {t}" for i, t in enumerate(takeaways, 1)]))
    flow.append(FrameBreak())

    flow.append(Paragraph("TOP STORIES", S["section"]))
    for article in regular[:4]:
        flow += story(article, images)

    by_topic = {}
    for article in regular[4:]:
        by_topic.setdefault(article["topic"], []).append(article)
    for topic, items in by_topic.items():
        flow.append(Paragraph(clean(topic.upper()), S["section"]))
        for article in items:
            flow += story(article, images)

    if wild:
        flow.append(Paragraph("WILDCARDS: OUTSIDE YOUR USUAL TOPICS", S["section"]))
        for article in wild:
            flow += story(article, images)

    doc.build(flow)
    return buffer.getvalue()