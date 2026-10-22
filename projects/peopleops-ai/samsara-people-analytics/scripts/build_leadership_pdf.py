"""Render a leadership PDF from an observed, verified n8n execution.

Run with the bundled Python runtime. All flowchart marks and charts are vectors.
"""
import json
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/samsara-n8n-leadership-workflow.pdf"
REPORT = json.loads((ROOT / "evidence/pdf-leadership-run.json").read_text())
WORKFLOW = json.loads((ROOT / "n8n/qualtrics-survey-demo.json").read_text())
assert REPORT["validation"]["status"] == "PASS"
assert all(c["pass"] for c in REPORT["validation"]["comparisons"])
assert REPORT["report"] and len(REPORT["plan"]["departments"]) == 5

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
pdfmetrics.registerFont(TTFont("ArialDemo", str(FONT_DIR / "Arial.ttf")))
pdfmetrics.registerFont(TTFont("ArialDemoBold", str(FONT_DIR / "Arial Bold.ttf")))
REG, BOLD = "ArialDemo", "ArialDemoBold"
W, H = landscape(A4)
M = 36
CW = W - M * 2
INK = colors.HexColor("#19343C")
MUTED = colors.HexColor("#596C74")
TEAL = colors.HexColor("#087F8C")
LINE = colors.HexColor("#DCE5E8")
SOFT = colors.HexColor("#F4F8F9")
TEAL_SOFT = colors.HexColor("#EAF5F3")
ORANGE = colors.HexColor("#BE623B")
ORANGE_SOFT = colors.HexColor("#FCF4EE")
RED = colors.HexColor("#9E4E43")

OUT.parent.mkdir(parents=True, exist_ok=True)
c = canvas.Canvas(str(OUT), pagesize=(W, H), pageCompression=1)
c.setTitle("Samsara People Analytics Demo | n8n Leadership Workflow")
c.setAuthor("People Analytics Demo")
c.setSubject("Synthetic employee-survey orchestration, independent validation and leadership readout")
layout_log = []


def rect(x, top, width, height, fill, stroke=None, radius=6):
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    c.setLineWidth(.7)
    c.roundRect(x, H - top - height, width, height, radius, fill=1, stroke=bool(stroke))


def line(x1, top1, x2, top2, color=LINE, width=.8):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, H - top1, x2, H - top2)


def text(value, x, top, size=10, bold=False, color=INK, align="left"):
    value = str(value)
    assert "\u2011" not in value and "\u2014" not in value and "\u2013" not in value
    font = BOLD if bold else REG
    width = pdfmetrics.stringWidth(value, font, size)
    left = x - width if align == "right" else x - width / 2 if align == "center" else x
    assert left >= M - 1 and left + width <= W - M + 1, (value, left, width)
    c.setFont(font, size)
    c.setFillColor(color)
    if align == "right":
        c.drawRightString(x, H - top - size, value)
    elif align == "center":
        c.drawCentredString(x, H - top - size, value)
    else:
        c.drawString(x, H - top - size, value)


def paragraph(value, x, top, width, max_height, size=10, leading=13, bold=False, color=MUTED):
    style = ParagraphStyle("p", fontName=BOLD if bold else REG, fontSize=size,
                           leading=leading, textColor=color, alignment=TA_LEFT)
    p = Paragraph(escape(value), style)
    actual_width, actual_height = p.wrap(width, max_height)
    assert actual_height <= max_height, (value, actual_height, max_height)
    assert x >= M - 1 and x + actual_width <= W - M + 1
    assert top + actual_height < H - 32
    p.drawOn(c, x, H - top - actual_height)
    layout_log.append({"text": value, "top": top, "height": actual_height, "width": width})
    return actual_height


def arrow(x1, top1, x2, top2):
    line(x1, top1, x2, top2, TEAL, 1.2)
    path = c.beginPath()
    if top1 == top2:
        sign = 1 if x2 > x1 else -1
        path.moveTo(x2, H - top2)
        path.lineTo(x2 - sign * 4, H - top2 + 2.5)
        path.lineTo(x2 - sign * 4, H - top2 - 2.5)
    else:
        sign = 1 if top2 > top1 else -1
        path.moveTo(x2, H - top2)
        path.lineTo(x2 - 2.5, H - top2 + sign * 4)
        path.lineTo(x2 + 2.5, H - top2 + sign * 4)
    path.close()
    c.setFillColor(TEAL)
    c.drawPath(path, fill=1, stroke=0)


verified_time = datetime.fromisoformat(REPORT["validation"]["timestamp"].replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Seoul"))
run_id = REPORT["orchestration"]["executionId"]
checksum = REPORT["validation"]["sourceChecksum"]


def header(page, title, subtitle):
    text("SAMSARA PEOPLE ANALYTICS / DEMO", M, 23, 8, True, TEAL)
    rect(W - M - 112, 19, 112, 21, ORANGE_SOFT)
    text("SYNTHETIC DATA", W - M - 56, 24, 8, True, ORANGE, "center")
    text(title, M, 62, 24, True)
    text(subtitle, M, 100, 10.6, False, MUTED)
    line(M, H - 33, W - M, H - 33)
    text("Fictional demonstration. Not actual Samsara employee results.", M, H - 24, 7.6, False, MUTED)
    text(f"22 OCT 2026  |  {page} / 2", W - M, H - 24, 7.6, False, MUTED, "right")


header(1, "From question to verified people insight",
       "An executive view of the actual n8n workflow, from HR request to a consistent report.")
rect(M, 126, CW, 49, SOFT)
text("THE BUSINESS QUESTION", M + 13, 135, 7.8, True, TEAL)
text('"What was everyone\'s company survey score over the last three years?"', M + 13, 150, 12)
text("FOLLOW STEPS 1-4 ACROSS, THEN 5-8 BACK TO THE REPORT", M, 191, 8, True, MUTED)

gap = 19
card_w = (CW - gap * 3) / 4
card_h = 112
xs = [M + i * (card_w + gap) for i in range(4)]
top_row, bottom_row = 207, 365
stages = [
    ("Webhook", "Receive question", "The app sends an HR question to the n8n webhook."),
    ("Parse Request", "Choose the scope", "Select 2024-2026 and the requested departments."),
    ("Valid Request", "Check the request", "Allow supported aggregate requests; reject unknown inputs."),
    ("Mock Qualtrics", "Retrieve survey data", "Read the synthetic survey export and eligible headcounts."),
    ("Metrics Engine", "Calculate + verify", "Calculate scores, then compare with saved Python reference results."),
    ("RAG Retrieval", "Retrieve methodology", "Retrieve approved definitions and data-quality guidance."),
    ("Build Grounded Answer", "Build the answer", "Combine verified values with cited methodology."),
    ("Respond to Webhook", "Return the report", "Send one verified dataset to the chat and dashboard."),
]
native_names = {node["name"] for node in WORKFLOW["nodes"]}
for i, (native, title, body) in enumerate(stages):
    assert native in native_names
    index = i if i < 4 else 7 - i
    x, top = xs[index], top_row if i < 4 else bottom_row
    rect(x, top, card_w, card_h, TEAL_SOFT if i == 4 else colors.white, TEAL if i == 4 else LINE)
    rect(x + 11, top + 11, 22, 20, TEAL if i == 4 else SOFT, radius=5)
    text(f"{i + 1:02d}", x + 22, top + 15, 8.1, True, colors.white if i == 4 else TEAL, "center")
    text(native.upper(), x + 39, top + 17, 7.2, True, MUTED)
    text(title, x + 12, top + 39, 12.7, True)
    paragraph(body, x + 12, top + 61, card_w - 24, 43, 9.6, 12.3)
for i in range(3):
    arrow(xs[i] + card_w + 2, top_row + card_h / 2, xs[i + 1] - 3, top_row + card_h / 2)
arrow(xs[3] + card_w / 2, top_row + card_h + 2, xs[3] + card_w / 2, bottom_row - 3)
for i in range(3, 0, -1):
    arrow(xs[i] - 2, bottom_row + card_h / 2, xs[i - 1] + card_w + 3, bottom_row + card_h / 2)
text("CONTINUE", xs[3] + card_w / 2 + 10, 337, 7.4, False, MUTED)

rect(M, 495, CW, 50, ORANGE_SOFT)
text("IF A CHECK FAILS", M + 13, 504, 8.2, True, RED)
paragraph("Invalid inputs, unavailable services or failed verification return a clear error. Unverified numerical reports are withheld.",
          M + 13, 520, CW - 26, 19, 10, 12.5, color=INK)
c.showPage()

header(2, "A leadership readout with an audit trail",
       "5,000 fictional eligible employees per year across five departments; every result comes from the same verified source.")
report, validation = REPORT["report"], REPORT["validation"]
stats = [
    ("SYNTHETIC SUBMISSIONS", f"{report['quality']['retrievedRecords']:,}", "Raw records retrieved from the mock export"),
    ("VALID SURVEY RESPONSES", f"{report['overall']['validRespondents']:,}", "Pooled across the three reporting periods"),
    ("INDEPENDENT VERIFICATION", validation["status"], f"{len(validation['comparisons'])} comparisons passed in this report"),
]
sw = (CW - 24) / 3
for i, (label, value, detail) in enumerate(stats):
    x = M + i * (sw + 12)
    rect(x, 126, sw, 67, TEAL_SOFT if i == 2 else SOFT)
    text(label, x + 12, 136, 7.7, True, MUTED)
    text(value, x + 12, 152, 22, True, TEAL if i == 2 else INK)
    text(detail, x + 12, 181, 8, False, MUTED)
text(f"Data quality: {report['quality']['duplicatesRemoved']:,} duplicate records removed; {report['quality']['invalidExcluded']:,} invalid unique responses excluded.",
     M, 202, 8.4, False, MUTED)

left_w = 456
right_x, right_w = M + left_w + 22, CW - left_w - 22
text("THE THREE-YEAR VIEW", M, 229, 9.4, True, TEAL)
rect(M, 247, left_w, 22, SOFT, radius=3)
col = [M + 11, M + 164, M + 258, M + 348, M + left_w - 11]
for title, x, align in zip(["Period", "Score /100", "Valid responses", "Eligible", "Response rate"], col, ["left", "right", "right", "right", "right"]):
    text(title, x, 253, 8.2, True, MUTED, align)
for i, row in enumerate(report["annual"]):
    top = 273 + i * 25
    vals = [str(row["year"]) + (" YTD" if row["year"] == 2026 else ""), f"{row['score']:.2f}",
            f"{row['validRespondents']:,}", f"{row['eligibleEmployees']:,}", f"{row['responseRate']:.2f}%"]
    for j, (value, x) in enumerate(zip(vals, col)):
        text(value, x, top, 10, j in (0, 1), TEAL if j == 1 else INK, "left" if j == 0 else "right")
    line(M, top + 20, M + left_w, top + 20)
paragraph("2026 is year-to-date through October 21. No statistical significance or causal claim is implied.", M, 350, left_w, 25, 8.8, 11.5)
text("Metric: Demo Company Engagement Score; equal weight per valid respondent.", M, 370, 8.4, False, MUTED)

text("THE FICTIONAL ELIGIBLE POPULATION", M, 391, 9.4, True, TEAL)
text("5,000 total each year", M + left_w, 391, 8.4, False, MUTED, "right")
latest_year = report["annual"][-1]["year"]
departments = [r for r in report["departments"] if r["year"] == latest_year]
assert sum(r["eligibleEmployees"] for r in departments) == 5000
max_eligible = max(r["eligibleEmployees"] for r in departments)
for i, row in enumerate(departments):
    top = 417 + i * 23
    text(row["department"], M + 1, top, 9.3)
    rect(M + 200, top + 3, 171 * row["eligibleEmployees"] / max_eligible, 7, TEAL, radius=2)
    text(f"{row['eligibleEmployees']:,}", M + left_w, top - .2, 10, True, INK, "right")
text("Illustrative staffing allocation, not actual Samsara headcount.", M, 538, 8, False, MUTED)

rect(right_x, 229, right_w, 318, SOFT)
text("Why the report is traceable", right_x + 15, 243, 13, True)
controls = [
    (277, "01 / Controlled requests", "Only approved years, departments and aggregate survey questions are accepted."),
    (341, "02 / Independent verification", "TypeScript results match a separately generated Python reference. Counts and source checksums are exact; scores agree within 0.01."),
    (437, "03 / Consistent presentation", "Chat, charts and CSV use the same verified report. RAG supplies definitions, not measured survey scores."),
]
for top, label, detail in controls:
    text(label, right_x + 15, top, 9.6, True, TEAL)
    paragraph(detail, right_x + 15, top + 19, right_w - 30, 66, 9.6, 12.5)
text(f"Verified run #{run_id} | {verified_time.strftime('%d %b %Y, %H:%M')} KST", right_x + 15, 522, 8, True, MUTED)

c.showPage()
c.save()
manifest = {"output": str(OUT), "pages": 2, "executionId": run_id, "validation": validation["status"],
            "sourceChecksum": checksum, "verifiedAt": validation["timestamp"],
            "workflow": WORKFLOW["id"], "layoutChecks": len(layout_log)}
(ROOT / "evidence/pdf-leadership-build.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
