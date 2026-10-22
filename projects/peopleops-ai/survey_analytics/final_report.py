"""Present committed Gold metrics as a portable, aggregate-only executive report."""

from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

ASSETS = Path(__file__).parent / "report"


def render_final_report(gold, snapshot=False):
    """Turn one published Gold snapshot into a readable report without recomputing scores."""
    template = (ASSETS / "index.html").read_text()
    style = (ASSETS / "style.css").read_text()
    if gold is None:
        return (
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>Final report · Awaiting results</title>"
            f'<style>{style}</style><main class="empty"><p class="eyebrow">FINAL REPORT</p>'
            "<h1>Your report is waiting for results.</h1>"
            "<p>Run the synthetic 5,000-employee workflow to publish its Gold snapshot.</p>"
            '<a class="button primary" href="/guide">Open the workflow guide →</a></main></html>'
        )
    metrics = gold["metrics"]
    departments = sorted(
        gold["department_breakdown"],
        key=lambda row: row["metrics"]["experience_score"]["value"],
        reverse=True,
    )
    highest, lowest = departments[0], departments[-1]
    experience = metrics["experience_score"]["value"]
    spread = (
        highest["metrics"]["experience_score"]["value"]
        - lowest["metrics"]["experience_score"]["value"]
    )
    negative = sum(row["metrics"]["enps"]["value"] < 0 for row in departments)
    csat_leader = max(
        departments, key=lambda row: row["metrics"]["csat_top_two_box"]["value"]
    )
    chart, table = [], []
    for row in departments:
        name, m = escape(row["department"]), row["metrics"]
        score = m["experience_score"]["value"]
        difference = score - experience
        color = "teal" if difference >= 0 else "clay"
        chart.append(
            f'<div class="bar-row"><div class="bar-label">{name}<small>'
            f"{row['counts']['completed']:,} responses</small></div>"
            f'<div class="bar-track"><span class="bar {color}" style="width:{score}%"></span>'
            f'<span class="reference" style="left:{experience}%"></span></div>'
            f'<strong>{score:.2f}</strong><span class="delta {color}">{difference:+.2f}</span></div>'
        )
        enps = m["enps"]["value"]
        table.append(
            f'<tr><th scope="row">{name}</th><td>{row["counts"]["completed"]:,}</td>'
            f"<td><b>{score:.2f}</b><small>n = {m['experience_score']['denominator']:,}</small></td>"
            f"<td>{m['csat_top_two_box']['value']:.2f}%<small>n = {m['csat_top_two_box']['denominator']:,}</small></td>"
            f'<td><span class="pill {"teal" if enps >= 0 else "clay"}">{enps:+.2f}</span>'
            f"<small>n = {m['enps']['denominator']:,}</small></td></tr>"
        )
    coverage = []
    completed = gold["counts"]["completed"]
    for label, key in [
        ("Engagement", "experience_score"),
        ("Satisfaction", "csat_top_two_box"),
        ("Recommendation", "enps"),
    ]:
        answered = metrics[key]["denominator"]
        coverage.append(
            f'<div class="coverage-row"><span>{label}</span><div class="coverage-track">'
            f'<i style="width:{answered / completed * 100}%"></i></div>'
            f"<b>{answered:,} / {completed:,}</b><small>{completed - answered:,} skipped</small></div>"
        )
    enps = metrics["enps"]
    segments = []
    for label, count, color in [
        ("Promoters", enps["promoters"], "teal"),
        (
            "Passives",
            enps["denominator"] - enps["promoters"] - enps["detractors"],
            "sand",
        ),
        ("Detractors", enps["detractors"], "clay"),
    ]:
        percent = count / enps["denominator"] * 100
        segments.append(
            f'<span class="{color}" style="width:{percent}%" title="{label}: {count:,}">{percent:.1f}%</span>'
        )
    batch = gold["batch_id"]
    published = datetime.fromisoformat(gold["published_at"]).astimezone(
        ZoneInfo("Asia/Seoul")
    )
    download = (
        ""
        if snapshot
        else (
            f'<a class="button" href="/analytics/export/{batch}/html" download>↓ Download report</a>'
            f'<a class="text-link" href="/analytics/export/{batch}/csv">Download department CSV ↗</a>'
        )
    )
    replacements = {
        "STYLE": style,
        "DOWNLOAD": download,
        "EXPERIENCE": f"{experience:.2f}",
        "ENGAGEMENT_N": f"{metrics['experience_score']['denominator']:,}",
        "CSAT": f"{metrics['csat_top_two_box']['value']:.2f}",
        "CSAT_N": f"{metrics['csat_top_two_box']['denominator']:,}",
        "ENPS": f"{enps['value']:+.2f}",
        "ENPS_N": f"{enps['denominator']:,}",
        "COMPLETED": f"{completed:,}",
        "INVITED": f"{gold['counts']['invited']:,}",
        "PARTICIPATION": f"{metrics['completion_rate']['value']:.0f}",
        "DEPARTMENTS": str(len(departments)),
        "HIGHEST": escape(highest["department"]),
        "LOWEST": escape(lowest["department"]),
        "HIGH_SCORE": f"{highest['metrics']['experience_score']['value']:.2f}",
        "LOW_SCORE": f"{lowest['metrics']['experience_score']['value']:.2f}",
        "SPREAD": f"{spread:.2f}",
        "NEGATIVE": str(negative),
        "CSAT_LEADER": escape(csat_leader["department"]),
        "CSAT_HIGH": f"{csat_leader['metrics']['csat_top_two_box']['value']:.2f}",
        "CHART": "".join(chart),
        "TABLE": "".join(table),
        "COVERAGE": "".join(coverage),
        "SEGMENTS": "".join(segments),
        "BATCH": escape(batch),
        "VERSION": escape(gold["metric_version"]),
        "PUBLISHED": published.strftime("%d %B %Y · %H:%M KST"),
        # Preserve an unformatted denominator for machine-readable provenance.
        "SAMPLE": str(metrics["experience_score"]["denominator"]),
    }
    for key, value in replacements.items():
        template = template.replace(f"__{key}__", value)
    return template
