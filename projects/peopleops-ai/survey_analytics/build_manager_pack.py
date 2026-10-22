"""Build the hiring-manager guide, guided diagram and two editable Word documents.

Run this authoring utility with the bundled document Python runtime, not the app image.
"""

import html
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from survey_analytics.manager_pack_content import (
    BR,
    BUSINESS_PROBLEM,
    DATE,
    GAPS,
    REQUIREMENTS,
    STEPS,
    SUMMARY,
    WALKTHROUGH,
)

ROOT = Path(__file__).parent
OUT = ROOT / "docs/manager-pack"
E = html.escape


def diagram():
    """Draw the same readable six-stage architecture as PNG and vector SVG."""
    image = Image.new("RGB", (1200, 760), "#ffffff")
    draw = ImageDraw.Draw(image)
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    fonts = {size: ImageFont.truetype(font_path, size) for size in (20, 23, 28, 30)}
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760" role="img" aria-labelledby="title desc"><title id="title">Local n8n survey architecture</title><desc id="desc">n8n orchestrates collection, Bronze, Silver, Gold, visualization and dashboard; errors go to a local inbox.</desc><rect width="1200" height="760" fill="white"/>'
    ]

    def box(x, y, w, h, fill, border="#d6dfd9"):
        draw.rounded_rectangle(
            (x, y, x + w, y + h), radius=12, fill=fill, outline=border, width=2
        )
        svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{border}" stroke-width="2"/>'
        )

    def text(x, y, value, size=23, color="#243f35"):
        draw.text((x, y), value, font=fonts[size], fill=color)
        svg.append(
            f'<text x="{x}" y="{y + size}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}">{E(value)}</text>'
        )

    def arrow(points):
        draw.line(points, fill="#759587", width=4)
        a, b = points[-2], points[-1]
        if b[0] > a[0]:
            tri = [b, (b[0] - 10, b[1] - 7), (b[0] - 10, b[1] + 7)]
        elif b[0] < a[0]:
            tri = [b, (b[0] + 10, b[1] - 7), (b[0] + 10, b[1] + 7)]
        else:
            tri = [b, (b[0] - 7, b[1] - 10), (b[0] + 7, b[1] - 10)]
        draw.polygon(tri, fill="#759587")
        svg.append(
            '<polyline points="'
            + " ".join(f"{x},{y}" for x, y in points)
            + '" fill="none" stroke="#759587" stroke-width="4"/>'
        )
        svg.append(
            '<polygon points="'
            + " ".join(f"{x},{y}" for x, y in tri)
            + '" fill="#759587"/>'
        )

    box(25, 20, 1150, 112, "#173f35")
    text(48, 37, "n8n orchestrates the sequence", 30, "#ffffff")
    text(
        48,
        80,
        "Start in n8n or the dashboard. FastAPI performs the data work; SQLite stores it.",
        23,
        "#d5e5dc",
    )
    blocks = [
        (
            25,
            185,
            "01  Mock Qualtrics",
            ["Public fake token", "5,000 unique responses"],
        ),
        (425, 185, "02  Bronze", ["Preserve the raw export", "5,000 raw versions"]),
        (
            825,
            185,
            "03  Silver",
            ["Validate and deduplicate", "5,000 accepted responses"],
        ),
        (
            825,
            420,
            "04  Gold",
            ["Calculate explicit metrics", "10 department aggregates"],
        ),
        (
            425,
            420,
            "05  Visualization",
            ["Build reports from Gold", "HTML and CSV exports"],
        ),
        (
            25,
            420,
            "06  Dashboard",
            ["Filter and compare scores", "Show each sample size"],
        ),
    ]
    for x, y, title, lines in blocks:
        box(x, y, 350, 166, "#f0f5ef")
        text(x + 20, y + 22, title, 28)
        for offset, line in enumerate(lines):
            text(x + 20, y + 75 + offset * 33, line, 23)
    arrow([(375, 267), (421, 267)])
    arrow([(775, 267), (821, 267)])
    arrow([(1000, 351), (1000, 416)])
    arrow([(825, 503), (779, 503)])
    arrow([(425, 503), (379, 503)])
    text(
        25,
        611,
        "Bronze, Silver and Gold persist in local SQLite under the same source batch hash.",
        23,
    )
    box(25, 660, 1150, 75, "#fff5e9", "#e6cdae")
    text(
        45,
        683,
        "If a stage fails: stop that run > published error workflow > local notification inbox",
        23,
        "#785232",
    )
    svg.append("</svg>")
    image.save(OUT / "architecture.png")
    (OUT / "architecture.svg").write_text("".join(svg))


def base_document(title, subtitle):
    """Apply a restrained, readable Letter portrait style for an executive review."""
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = Inches(0.65)
    section.left_margin = section.right_margin = Inches(0.75)
    for name in ("Normal", "Title", "Subtitle", "Heading 1", "Heading 2"):
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.color.rgb = RGBColor(0, 0, 0)
    normal = doc.styles["Normal"]
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.08
    for name, size in (
        ("Title", 24),
        ("Subtitle", 11),
        ("Heading 1", 16),
        ("Heading 2", 11.5),
    ):
        doc.styles[name].font.size = Pt(size)
        doc.styles[name].paragraph_format.space_before = Pt(
            10 if name.startswith("Heading") else 0
        )
        doc.styles[name].paragraph_format.space_after = Pt(6)
    doc.core_properties.author = "PeopleOps AI demonstration project"
    doc.core_properties.title = title
    doc.core_properties.subject = (
        "Fictional local n8n survey workflow for hiring-manager review"
    )
    doc.add_paragraph(title, "Title")
    doc.add_paragraph(subtitle, "Subtitle")
    doc.add_paragraph(
        f"Version 1.0   |   {DATE}   |   Audience Hiring manager and technical reviewer"
    )
    return doc


def table(doc, headers, rows, widths):
    """Add a compact comparison table with explicit borders and repeating headers."""
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    for col, width in zip(t.columns, widths, strict=True):
        col.width = Inches(width)
    for i, h in enumerate(headers):
        t.rows[0].cells[i].text = h
    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = str(value)
    for ri, row in enumerate(t.rows):
        for ci, cell in enumerate(row.cells):
            cell.width = Inches(widths[ci])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            props = cell._tc.get_or_add_tcPr()
            borders = OxmlElement("w:tcBorders")
            for edge in ("top", "left", "bottom", "right"):
                line = OxmlElement("w:" + edge)
                line.set(qn("w:val"), "single")
                line.set(qn("w:sz"), "4")
                line.set(qn("w:color"), "D9D9D9")
                borders.append(line)
            props.append(borders)
            margins = OxmlElement("w:tcMar")
            for edge in ("top", "left", "bottom", "right"):
                m = OxmlElement("w:" + edge)
                m.set(qn("w:w"), "85")
                m.set(qn("w:type"), "dxa")
                margins.append(m)
            props.append(margins)
            shading = OxmlElement("w:shd")
            shading.set(
                qn("w:fill"), "244B64" if ri == 0 else "F1F5F7" if ri % 2 else "FFFFFF"
            )
            props.append(shading)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.04
                for run in p.runs:
                    run.font.size = Pt(10)
                    run.font.bold = ri == 0
                    run.font.color.rgb = (
                        RGBColor(255, 255, 255) if ri == 0 else RGBColor(0, 0, 0)
                    )
        cant = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(cant)
    repeat = OxmlElement("w:tblHeader")
    t.rows[0]._tr.get_or_add_trPr().append(repeat)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return t


def metric_summary(doc):
    table(
        doc,
        ["Metric", "Definition", "Observed value"],
        [
            (
                "Experience",
                "Mean engagement on 1 to 5 scale multiplied by 20; attainable range 20 to 100",
                "75.99 / 100; 4,865 answers",
            ),
            (
                "CSAT",
                "100 times satisfaction scores 4 or 5 divided by answered satisfaction questions",
                "68.56%; 4,828 answers",
            ),
            (
                "eNPS",
                "100 times promoters scoring 9 or 10 minus detractors scoring 0 to 6, divided by answered recommendation questions",
                "+5.60; 4,879 answers",
            ),
        ],
        [1.0, 4.2, 1.8],
    )


def build_brd():
    """Create a three-page business case with scope, architecture and review criteria."""
    doc = base_document(
        "Business requirements document", "Synthetic employee survey analytics with n8n"
    )
    doc.add_paragraph(SUMMARY)
    doc.add_heading("Business problem", 1)
    doc.add_paragraph(BUSINESS_PROBLEM)
    doc.add_heading("Business requirements", 1)
    table(
        doc,
        ["ID", "Outcome", "Business acceptance"],
        [(i, name, desc) for i, name, desc, _ in BR],
        [0.55, 1.8, 4.65],
    )
    doc.add_heading("Scope and value", 1)
    doc.add_paragraph(
        "In scope: a fixed synthetic cohort, local mock API, executable n8n orchestration, durable data layers, department scores and manager reports. The expected value is easier review of data engineering decisions; time or cost savings have not been measured."
    )
    doc.add_paragraph(
        "Out of scope: real Qualtrics or Samsara access, individual employee assessment, live HR records, production deployment and actual organizational findings."
    )
    doc.add_page_break()
    doc.add_heading("Guided architecture", 1)
    doc.add_paragraph(
        "Read the numbered flow left to right across the first row, then right to left across the second. Arrows show data handoffs. n8n coordinates the HTTP calls; the Python service performs transformations and calculations."
    )
    doc.add_picture(str(OUT / "architecture.png"), width=Inches(7.0))
    doc.add_heading("Why the layers exist", 1)
    doc.add_paragraph(
        "Bronze is the preserved source evidence. Silver is the validated record set. Gold is the committed metric result used by every chart and export. The source batch hash links them, so a reviewer can follow a displayed score back to its snapshot."
    )
    doc.add_heading("What to say in the interview", 1)
    doc.add_paragraph(
        "The dashboard does not invent the scores. n8n collects the fixed export, the API validates and stores it, and Gold calculates company and department metrics. Rerunning the same input reuses the same batch instead of creating duplicate survey rows. The final stage creates portable reports from those committed aggregates."
    )
    doc.add_page_break()
    doc.add_heading("Review roles and acceptance", 1)
    table(
        doc,
        ["Review role", "Responsibility"],
        [
            (
                "Hiring manager",
                "Assess whether the business need, outcomes and demonstration are understandable.",
            ),
            (
                "Technical reviewer",
                "Inspect execution, data grain, arithmetic, replay behavior and evidence.",
            ),
            (
                "Project owner",
                "Run the local demonstration, explain assumptions and maintain its requirements.",
            ),
            (
                "Future business and security owners",
                "Approve real data access, metric definitions and production controls before any enterprise use.",
            ),
        ],
        [1.8, 5.2],
    )
    doc.add_heading("Observed business outputs", 1)
    metric_summary(doc)
    doc.add_paragraph(
        "All 5,000 synthetic invitations have completed responses across ten illustrative departments. Question-level skips explain the smaller score denominators. These values describe the fictional fixture, not Samsara employees."
    )
    doc.add_heading("Conditions before enterprise use", 1)
    for text in GAPS:
        doc.add_paragraph(text, style="List Bullet")
    doc.add_paragraph(
        "Acceptance status: local demonstration evidence is available. This document is not stakeholder signoff, a production certification or an assertion of completed employee research."
    )
    save_document(doc, OUT / "BusinessRequirements.docx")


def requirement_block(doc, item):
    doc.add_heading(item["id"] + " " + item["name"], 2)
    doc.add_paragraph(item["shall"])
    p = doc.add_paragraph()
    p.add_run("Acceptance  ").bold = True
    p.add_run(item["acceptance"])
    p.paragraph_format.space_after = Pt(5)


def build_requirements():
    """Create a readable baseline linking functional requirements to concrete checks."""
    doc = base_document(
        "Workflow requirements document",
        "Synthetic employee survey collection and department reporting",
    )
    doc.styles["Normal"].paragraph_format.space_after = Pt(5)
    doc.styles["Normal"].paragraph_format.line_spacing = 1.04
    doc.styles["Heading 2"].paragraph_format.space_before = Pt(8)
    doc.styles["Heading 2"].paragraph_format.space_after = Pt(4)
    doc.add_paragraph(
        "This baseline defines what the local workflow must do and how a reviewer can check it. All requirements apply to the fixed synthetic demonstration. Business requirement identifiers refer to the companion BRD; no enterprise acceptance is implied."
    )
    doc.add_heading("Collection and processing requirements", 1)
    for item in REQUIREMENTS[:6]:
        requirement_block(doc, item)
    doc.add_page_break()
    doc.add_heading("Publication and review requirements", 1)
    for item in REQUIREMENTS[6:]:
        requirement_block(doc, item)
    doc.add_page_break()
    doc.add_heading("Data and metric contract", 1)
    doc.add_paragraph(
        "Input grain: one current response per fictional employee. Each row includes synthetic employee and response IDs, a UTC timestamp, department, completion, engagement and CSAT from 1 to 5, recommendation from 0 to 10, and duration. Scores may be null; only the server owned fixture is accepted."
    )
    metric_summary(doc)
    doc.add_heading("Operating requirements", 1)
    table(
        doc,
        ["ID", "Required local behavior", "Evidence boundary"],
        [
            (
                "NFR01",
                "Use a deterministic fixture and atomic stage commits; identical reruns retain row counts.",
                "Unit and real replay checks; not a distributed exactly once guarantee.",
            ),
            (
                "NFR02",
                "HTTP nodes use a 10 second timeout, at most 3 tries and 1 second between retries; workflow timeout is 120 seconds.",
                "Configuration inspection; not a measured availability target.",
            ),
            (
                "NFR03",
                "Publish department slices only when all completed and per-question department samples meet the minimum of 5; exports omit individual identifiers.",
                "Small-fixture suppression and aggregate export tests; not a privacy certification.",
            ),
            (
                "NFR04",
                "Publish ports to loopback, keep the source token fake, and show synthetic labels in manager outputs.",
                "Compose and content inspection; not enterprise authentication.",
            ),
        ],
        [0.7, 3.65, 2.65],
    )
    doc.add_heading("Requirement traceability", 1)
    doc.add_paragraph(
        "The companion requirements.csv and interactive guide list each FR, its parent BR, acceptance condition, evidence type and exact test/source reference. FR08 and parts of FR03/FR11 require browser evidence; unit tests alone do not prove them."
    )
    doc.add_heading("How to execute the demonstration", 1)
    doc.add_paragraph("Open samsaraSurvey5000 in n8n, choose Run synthetic survey and click Execute. Inspect the layer outputs; one n8n item can contain all 5,000 responses. Filter Engineering to confirm 1,200 respondents, then rerun and confirm unchanged row counts.")
    doc.add_paragraph(
        "Local guide http://127.0.0.1:8812/guide links to n8n and the dashboard on the demo Mac. Share the Word documents and diagram with remote reviewers."
    )
    save_document(doc, OUT / "WorkflowRequirements.docx")


def save_document(doc, destination):
    """Remove inherited paragraph rules and save the document without title borders."""
    for root in (doc.styles.element, doc.element):
        for border in list(root.iter(qn("w:pBdr"))):
            border.getparent().remove(border)
    doc.save(destination)


def build_guide():
    """Build a self-contained guided architecture and requirement review page."""
    steps = json.dumps(STEPS).replace("<", "\\u003c")
    nav = "".join(
        f'<button class="stage" data-stage="{i}" aria-pressed="{str(i == 0).lower()}"><b>{i + 1:02}</b>{E(s["name"])}</button>'
        for i, s in enumerate(STEPS)
    )
    br = "".join(
        f"<tr><td>{i}</td><td><strong>{E(name)}</strong><br>{E(desc)}</td><td>{E(ref)}</td></tr>"
        for i, name, desc, ref in BR
    )
    req = "".join(
        f"<details><summary><span>{r['id']}</span> {E(r['name'])}</summary><p>{E(r['shall'])}</p><p><b>Acceptance:</b> {E(r['acceptance'])}</p><p><b>Business need:</b> {r['br']} · <b>Evidence:</b> {r['type']}</p><code>{E(r['evidence'])}</code></details>"
        for r in REQUIREMENTS
    )
    walk = "".join(
        f"<li><strong>{E(action)}</strong> <span>{E(time_)}</span><p>{E(detail)}</p></li>"
        for time_, action, detail in WALKTHROUGH
    )
    gaps = "".join(f"<li>{E(g)}</li>" for g in GAPS)
    svg = (OUT / "architecture.svg").read_text()
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hiring manager guide · Survey workflow</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f4f6f2;color:#21392f;font:15px/1.65 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:26px}nav{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;margin-bottom:30px}a{color:#27674e}h1{font-size:38px;line-height:1.15;letter-spacing:-1.2px;margin:15px 0}h2{font-size:25px;line-height:1.3;margin:0 0 15px}h3{margin:0 0 10px;font-size:18px}.eyebrow{font-size:11px;letter-spacing:1.8px;color:#64816d;font-weight:650}.intro{max-width:850px;font-size:17px;color:#65776a}.badge{font-size:10px;letter-spacing:1px;background:#e3ecd8;border-radius:20px;padding:7px 12px;display:inline-block}.actions{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}.actions a,button{border:1px solid #ccd9cc;border-radius:6px;background:#fff;padding:10px 14px;cursor:pointer;text-decoration:none;font:inherit;font-size:13px;color:#234b36}button.primary{background:#204c39;color:white;border-color:#204c39}button:disabled{opacity:.45;cursor:default}.panel{background:white;border:1px solid #dce5d9;border-radius:10px;padding:28px;margin-top:24px}.arch svg{width:100%;height:auto;display:block}.stage-nav{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:15px 0}.stage{text-align:left;display:flex;align-items:center;gap:8px;font-size:12px}.stage b{color:#739063}.stage[aria-pressed=true]{background:#e6efdf;border-color:#71956c}.explain{border-top:1px solid #e0e7dc;padding-top:22px;margin-top:20px}.explain p{margin:10px 0}.controls{display:flex;justify-content:space-between;gap:12px;margin-top:20px}#progress{font-size:12px;color:#78906d}#run-result{padding:14px 0;color:#456b3f;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;border-bottom:1px solid #e0e8dd;padding:13px 10px;vertical-align:top}th{font-size:11px;color:#748b6a}td:first-child{white-space:nowrap;font-weight:600}details{border-bottom:1px solid #e1e8dc;padding:13px 0}summary{cursor:pointer;font-size:14px;font-weight:600}summary span{color:#658256;margin-right:8px}details p{font-size:13px}code{display:block;font:11px/1.8 ui-monospace,monospace;overflow-wrap:anywhere;color:#6c7f63}.walk{padding-left:22px}.walk li{padding:10px 0}.walk span{font-size:11px;color:#7f9273;margin-left:8px}.walk p{margin:6px 0;font-size:14px}.limits li{margin:12px 0;font-size:13px}.table-wrap{overflow-x:auto}.metrics{display:flex;gap:35px;flex-wrap:wrap;margin:20px 0}.metrics strong{display:block;font-size:27px}.metrics span{font-size:12px;color:#6d8260}footer{font-size:12px;color:#7c8d72;padding:28px 0}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #90b47c;outline-offset:3px}@media(max-width:650px){main{padding:18px}.panel{padding:18px}h1{font-size:30px}.intro{font-size:15px}.stage-nav{grid-template-columns:repeat(2,1fr)}.stage{font-size:11px}.metrics{gap:20px}.metrics strong{font-size:24px}}
    </style></head><body><main><nav><a href="http://127.0.0.1:8812/dashboard">← Dashboard</a><a href="#architecture">Architecture</a><a href="#business">Business case</a><a href="#requirements">Requirements</a><a href="#demo">Demo script</a></nav><span class="badge">HIRING MANAGER REVIEW · 100% FICTIONAL DATA</span><p class="eyebrow">LOCAL N8N WORKFLOW · 21 OCTOBER 2026</p><h1>How the survey workflow works</h1><p class="intro">__SUMMARY__</p><div class="actions"><a href="/report" style="background:#204c39;color:white;border-color:#204c39">View final report ↗</a><a href="http://127.0.0.1:5680/workflow/samsaraSurvey5000">Open n8n Execute ↗</a><a href="/guide/download/BusinessRequirements.docx">Download BRD</a><a href="/guide/download/WorkflowRequirements.docx">Download requirements</a><a href="/guide/download/architecture.svg">Download diagram</a></div><div class="metrics"><div><strong>5,000</strong><span>unique fictional employees</span></div><div><strong>10</strong><span>illustrative departments</span></div><div><strong>3</strong><span>explicit sentiment metrics</span></div></div>
    <section id="architecture" class="panel"><p class="eyebrow">FOLLOW THE DATA</p><h2>Guided architecture</h2><p>n8n decides the order. FastAPI performs the data work. SQLite preserves each layer. Choose a stage below to see its purpose, input, output and review check.</p><div class="arch">__SVG__</div><div class="stage-nav">__NAV__</div><div class="explain" aria-live="polite"><p id="progress"></p><h3 id="step-title"></h3><p id="step-why"></p><p><b>Receives:</b> <span id="step-input"></span></p><p><b>Produces:</b> <span id="step-output"></span></p><p><b>Verify:</b> <span id="step-check"></span></p><code id="step-node"></code></div><div class="controls"><button id="previous">← Previous stage</button><button id="next">Next stage →</button></div></section>
    <section class="panel"><p class="eyebrow">TRY THE WORKING PRODUCT</p><h2>Execute the local n8n workflow</h2><p>This button calls the same published n8n webhook used by the dashboard. It recollects the fixed fixture and reuses its committed batch. It does not run the Python test suite or contact a live vendor.</p><button class="primary" id="execute">Execute n8n workflow</button><div id="run-result" role="status" aria-live="polite">Ready to run on the demonstration Mac.</div></section>
    <section id="business" class="panel"><p class="eyebrow">BRD SUMMARY</p><h2>The business case</h2><p>__PROBLEM__</p><div class="table-wrap"><table><thead><tr><th>ID</th><th>Business requirement</th><th>Related workflow requirements</th></tr></thead><tbody>__BR__</tbody></table></div><h3>Scope and expected value</h3><p>The intended benefit is an easier, evidence-based review of data engineering decisions. The scope is one synthetic snapshot, local execution and department reporting. No measured labor saving, approved business funding or stakeholder signoff is claimed.</p></section>
    <section id="requirements" class="panel"><p class="eyebrow">REQUIREMENTS BASELINE</p><h2>What must work and how to check it</h2><p>Expand a requirement for its acceptance condition and evidence source. Browser, unit and live checks are separate forms of evidence.</p>__REQ__<div class="actions"><a href="/guide/download/requirements.csv">Download traceability CSV</a></div></section>
    <section id="demo" class="panel"><p class="eyebrow">FIVE MINUTE INTERVIEW WALKTHROUGH</p><h2>Show the outcome and the reasoning</h2><ol class="walk">__WALK__</ol><p><b>Expected local result:</b> 5,000 accepted responses, zero quarantined cohort rows and ten department groups. Experience 75.99/100; CSAT 68.56%; eNPS +5.60. The question counts are 4,865, 4,828 and 4,879 respectively.</p><p><b>Important distinction:</b> The earlier 500-request load test repeatedly downloaded a small fixture. This workflow collects 5,000 different fictional employees. One n8n item can hold all 5,000 responses.</p></section>
    <section class="panel"><p class="eyebrow">PRODUCTION BOUNDARY</p><h2>What still needs approval and engineering</h2><ul class="limits">__GAPS__</ul><p><b>Source of truth:</b> executable Python functions and the imported n8n JSON. This pack describes the working local baseline; it is not a production readiness signoff.</p></section><footer>PeopleOps AI demonstration project · Local links work on the demonstration Mac. Share the Word documents and diagram files with remote reviewers. The company name, employee population and results are illustrative.</footer></main><script>
    const steps=__STEPS__;let current=0;const $=id=>document.getElementById(id);function show(i){current=Math.max(0,Math.min(steps.length-1,i));const s=steps[current];$('progress').textContent=`STAGE ${current+1} OF ${steps.length}`;$('step-title').textContent=s.name;$('step-why').textContent=s.why;for(const k of ['input','output','check','node'])$('step-'+k).textContent=s[k];document.querySelectorAll('[data-stage]').forEach((b,j)=>b.setAttribute('aria-pressed',String(j===current)));$('previous').disabled=current===0;$('next').disabled=current===steps.length-1;}document.querySelectorAll('[data-stage]').forEach(b=>b.onclick=()=>show(Number(b.dataset.stage)));$('previous').onclick=()=>show(current-1);$('next').onclick=()=>show(current+1);show(0);$('execute').onclick=async()=>{const b=$('execute');b.disabled=true;$('run-result').textContent='Running source → Bronze → Silver → Gold → visualization…';try{const r=await fetch('/analytics/run',{method:'POST'});if(!r.ok)throw Error('Workflow did not complete. Inspect n8n executions and the local error inbox.');const run=await r.json();if(run.status!=='ready')throw Error('Workflow returned a result that is not ready.');const a=await fetch('/analytics');if(!a.ok)throw Error('Gold snapshot is unavailable.');const g=await a.json();$('run-result').textContent=`Completed: ${g.counts.completed.toLocaleString()} synthetic responses; ${g.department_breakdown.length} departments; batch ${g.batch_id.slice(0,16)}… Open the dashboard to inspect the scores.`;}catch(e){$('run-result').textContent=e.message;}finally{b.disabled=false;}};if(location.protocol==='file:'){$('execute').disabled=true;$('run-result').textContent='Saved guide. Open the localhost dashboard on the demonstration Mac to execute n8n.';}
    </script></body></html>"""
    for key, value in {
        "SUMMARY": E(SUMMARY),
        "PROBLEM": E(BUSINESS_PROBLEM),
        "SVG": svg,
        "NAV": nav,
        "BR": br,
        "REQ": req,
        "WALK": walk,
        "GAPS": gaps,
        "STEPS": steps,
    }.items():
        page = page.replace("__" + key + "__", value)
    (OUT / "hiring-manager-guide.html").write_text(page)


def main():
    """Generate the review pack without changing runtime data or execution settings."""
    import csv

    OUT.mkdir(parents=True, exist_ok=True)
    diagram()
    build_brd()
    build_requirements()
    build_guide()
    with (OUT / "requirements.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(REQUIREMENTS[0]))
        writer.writeheader()
        writer.writerows(REQUIREMENTS)
    print(
        json.dumps(
            {
                "directory": str(OUT),
                "word_documents": 2,
                "requirements": len(REQUIREMENTS),
                "guided_stages": len(STEPS),
            }
        )
    )


if __name__ == "__main__":
    main()
