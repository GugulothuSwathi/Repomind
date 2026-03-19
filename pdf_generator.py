# pdf_generator.py
# ============================================
# Generates a PDF report for RepoMind analysis
# Uses reportlab (pip install reportlab)
# ============================================

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ── colour palette ───────────────────────────────────────────────────────────
PRIMARY   = colors.HexColor("#6C63FF")
DARK      = colors.HexColor("#1a1a2e")
ACCENT    = colors.HexColor("#0f3460")
SUCCESS   = colors.HexColor("#28a745")
WARNING   = colors.HexColor("#ffc107")
DANGER    = colors.HexColor("#dc3545")
INFO      = colors.HexColor("#17a2b8")
LIGHT_BG  = colors.HexColor("#f8f9fa")
MID_GREY  = colors.HexColor("#6c757d")
WHITE     = colors.white


# ── helpers ───────────────────────────────────────────────────────────────────

def _severity_colour(severity: str) -> colors.Color:
    s = str(severity).upper()
    if s in ("CRITICAL", "HIGH"):
        return DANGER
    if s == "MEDIUM":
        return WARNING
    if s == "LOW":
        return SUCCESS
    return INFO


def _score_colour(score: float) -> colors.Color:
    if score >= 75:
        return SUCCESS
    if score >= 50:
        return WARNING
    return DANGER


def _clamp(val, lo=0, hi=100):
    try:
        return max(lo, min(hi, float(val)))
    except (TypeError, ValueError):
        return lo


def _safe_str(val, default="N/A") -> str:
    if val is None:
        return default
    return str(val).strip() or default


def _truncate(text: str, max_len: int = 300) -> str:
    text = str(text)
    return text if len(text) <= max_len else text[:max_len] + "…"


# ── style sheet ───────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "title",
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName="Helvetica",
            fontSize=11,
            textColor=colors.HexColor("#ddddff"),
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "section": ParagraphStyle(
            "section",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=PRIMARY,
            spaceBefore=14,
            spaceAfter=6,
            borderPad=2,
        ),
        "subsection": ParagraphStyle(
            "subsection",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=ACCENT,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK,
            spaceAfter=4,
            leading=13,
        ),
        "body_small": ParagraphStyle(
            "body_small",
            fontName="Helvetica",
            fontSize=8,
            textColor=MID_GREY,
            spaceAfter=3,
            leading=11,
        ),
        "code": ParagraphStyle(
            "code",
            fontName="Courier",
            fontSize=8,
            textColor=DARK,
            backColor=LIGHT_BG,
            spaceAfter=3,
            leading=11,
            leftIndent=8,
        ),
        "badge_high": ParagraphStyle(
            "badge_high",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=WHITE,
        ),
        "meta": ParagraphStyle(
            "meta",
            fontName="Helvetica",
            fontSize=8,
            textColor=MID_GREY,
            alignment=TA_RIGHT,
        ),
        "toc_item": ParagraphStyle(
            "toc_item",
            fontName="Helvetica",
            fontSize=10,
            textColor=ACCENT,
            spaceAfter=3,
            leftIndent=12,
        ),
    }
    return styles


# ── section builders ─────────────────────────────────────────────────────────

def _header_table(repo_info: dict, styles: dict):
    """Returns the dark banner at the top of the first page."""
    name = _safe_str(repo_info.get("name"), "Repository")
    url  = _safe_str(repo_info.get("url"), "")
    desc = _safe_str(repo_info.get("description"), "")
    lang = _safe_str(repo_info.get("language"), "")
    stars = _safe_str(repo_info.get("stars"), "0")
    forks = _safe_str(repo_info.get("forks"), "0")
    date  = datetime.now().strftime("%d %B %Y, %H:%M")

    title_p    = Paragraph(f"🧠 RepoMind Analysis Report", styles["title"])
    repo_p     = Paragraph(f"<b>{name}</b>", ParagraphStyle("rn", fontName="Helvetica-Bold",
                           fontSize=14, textColor=WHITE, alignment=TA_CENTER))
    url_p      = Paragraph(url, styles["subtitle"])
    desc_p     = Paragraph(_truncate(desc, 150), styles["subtitle"])
    meta_line  = f"⭐ {stars} stars  •  🍴 {forks} forks  •  🔤 {lang}  •  📅 {date}"
    meta_p     = Paragraph(meta_line, styles["subtitle"])

    data = [[title_p], [repo_p], [url_p], [desc_p], [meta_p]]
    t = Table(data, colWidths=[17 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), DARK),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [6]),
    ]))
    return t


def _scores_table(results: dict, styles: dict):
    """Summary score table for all agents."""
    tm_data = results.get("time_machine", {}) or {}
    tm_commits = tm_data.get("commits", []) if isinstance(tm_data, dict) else []
    tm_score = tm_data.get("score", 70 if tm_commits else 0) if isinstance(tm_data, dict) else 0

    score_map = {
        "Code Review":    results.get("code_review",    {}).get("score",         0),
        "Security":       results.get("security",       {}).get("score",         0),
        "Documentation":  results.get("documentation",  {}).get("score",         0),
        "Dependencies":   results.get("dependency",     {}).get("score",         0),
        "Bug Fix":        results.get("bug_fix",        {}).get("score",         0),
        "Risk Heatmap":   100 - _clamp(results.get("risk_heatmap", {}).get("overall_risk_score", 50)),
        "Architecture":   results.get("architecture",   {}).get("score",         70),
        "Time Machine":   tm_score,
    }

    header = [
        Paragraph("<b>Agent</b>",  styles["body"]),
        Paragraph("<b>Score</b>",  styles["body"]),
        Paragraph("<b>Status</b>", styles["body"]),
    ]
    rows = [header]
    for agent, raw_score in score_map.items():
        score  = _clamp(raw_score)
        status = "✅ Good" if score >= 75 else ("⚠️ Fair" if score >= 50 else "❌ Needs Work")
        colour = _score_colour(score)
        rows.append([
            Paragraph(agent, styles["body"]),
            Paragraph(f"<b>{score:.0f} / 100</b>",
                      ParagraphStyle("sc", fontName="Helvetica-Bold", fontSize=9,
                                     textColor=colour)),
            Paragraph(status, styles["body"]),
        ])

    t = Table(rows, colWidths=[7 * cm, 4 * cm, 6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#dee2e6")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def _code_review_section(cr: dict, styles: dict):
    elems = []
    elems.append(Paragraph("🔍 Code Review", styles["section"]))
    elems.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))

    # metrics
    metrics = [
        ("Files Detected",  cr.get("files_detected", "N/A")),
        ("Files Reviewed",  cr.get("files_reviewed", "N/A")),
        ("Total Findings",  cr.get("total_findings", 0)),
        ("Score",           f"{_clamp(cr.get('score', 0)):.0f} / 100"),
    ]
    row = [Paragraph(f"<b>{k}</b><br/>{v}", styles["body"]) for k, v in metrics]
    t = Table([row], colWidths=[4.25 * cm] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT_BG),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 6))

    # top issues (up to 10)
    issues = cr.get("issues", [])
    if issues:
        elems.append(Paragraph("<b>Top Findings</b>", styles["subsection"]))
        for i, issue in enumerate(issues[:10], 1):
            sev   = _safe_str(issue.get("severity", "INFO"))
            fname = _safe_str(issue.get("file", ""), "unknown file")
            title = _safe_str(issue.get("issue", ""), "Finding")
            desc  = _truncate(_safe_str(issue.get("description", ""), ""), 200)
            suggestion = _truncate(_safe_str(issue.get("suggestion", ""), ""), 200)

            badge_colour = _severity_colour(sev)
            elems.append(KeepTogether([
                Paragraph(
                    f'<font color="#{badge_colour.hexval()[2:]}"><b>[{sev}]</b></font> '
                    f'<b>{_truncate(title, 80)}</b> — <i>{_truncate(fname, 60)}</i>',
                    styles["body"],
                ),
                Paragraph(desc,       styles["body_small"]),
                Paragraph(f"💡 {suggestion}", styles["body_small"]),
                Spacer(1, 3),
            ]))
    return elems


def _security_section(sec: dict, styles: dict):
    elems = []
    elems.append(Paragraph("🔒 Security Analysis", styles["section"]))
    elems.append(HRFlowable(width="100%", thickness=1, color=DANGER))

    vulns = sec.get("vulnerabilities", [])
    score = _clamp(sec.get("score", 0))
    elems.append(Paragraph(
        f"Security Score: <b>{score:.0f}/100</b> — "
        f"<b>{len(vulns)}</b> vulnerabilit{'y' if len(vulns)==1 else 'ies'} found.",
        styles["body"],
    ))
    elems.append(Spacer(1, 4))

    for vuln in vulns[:12]:
        sev   = _safe_str(vuln.get("severity", "INFO"))
        vtype = _safe_str(vuln.get("type", "Unknown"))
        fname = _safe_str(vuln.get("file", ""))
        line  = vuln.get("line", "")
        desc  = _truncate(_safe_str(vuln.get("description", ""), ""), 200)
        rec   = _truncate(_safe_str(vuln.get("recommendation", ""), ""), 200)

        badge_colour = _severity_colour(sev)
        line_str = f" (line {line})" if line else ""
        elems.append(KeepTogether([
            Paragraph(
                f'<font color="#{badge_colour.hexval()[2:]}"><b>[{sev}]</b></font> '
                f'<b>{vtype}</b> — <i>{_truncate(fname, 55)}{line_str}</i>',
                styles["body"],
            ),
            Paragraph(desc,         styles["body_small"]),
            Paragraph(f"🛡️ {rec}",   styles["body_small"]),
            Spacer(1, 3),
        ]))
    return elems


def _documentation_section(doc: dict, styles: dict):
    elems = []
    elems.append(Paragraph("📚 Documentation Analysis", styles["section"]))
    elems.append(HRFlowable(width="100%", thickness=1, color=INFO))

    score    = _clamp(doc.get("score", 0))
    coverage = _clamp(doc.get("doc_coverage", 0))
    has_readme = doc.get("has_readme", False)
    readme_score = _clamp(doc.get("readme_score", 0))

    metrics = [
        ("Overall Score",    f"{score:.0f}/100"),
        ("Doc Coverage",     f"{coverage:.0f}%"),
        ("README",           "✅ Present" if has_readme else "❌ Missing"),
        ("README Quality",   f"{readme_score:.0f}/100"),
    ]
    row = [Paragraph(f"<b>{k}</b><br/>{v}", styles["body"]) for k, v in metrics]
    t = Table([row], colWidths=[4.25 * cm] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT_BG),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
    ]))
    elems.append(t)

    issues = doc.get("issues", [])
    if issues:
        elems.append(Spacer(1, 4))
        elems.append(Paragraph("<b>Documentation Issues</b>", styles["subsection"]))
        for iss in issues[:8]:
            elems.append(Paragraph(f"• {_truncate(str(iss), 200)}", styles["body_small"]))
    return elems


def _dependency_section(dep: dict, styles: dict):
    elems = []
    elems.append(Paragraph("📦 Dependency Analysis", styles["section"]))
    elems.append(HRFlowable(width="100%", thickness=1, color=WARNING))

    score      = _clamp(dep.get("score", 0))
    total_deps = dep.get("total_dependencies", 0)
    outdated   = dep.get("outdated_count", 0)
    vulnerable = dep.get("vulnerable_count", 0)

    metrics = [
        ("Score",        f"{score:.0f}/100"),
        ("Total Deps",   str(total_deps)),
        ("Outdated",     str(outdated)),
        ("Vulnerable",   str(vulnerable)),
    ]
    row = [Paragraph(f"<b>{k}</b><br/>{v}", styles["body"]) for k, v in metrics]
    t = Table([row], colWidths=[4.25 * cm] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT_BG),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
    ]))
    elems.append(t)

    deps_list = dep.get("dependencies", [])
    if deps_list:
        elems.append(Spacer(1, 4))
        elems.append(Paragraph("<b>Dependencies</b>", styles["subsection"]))
        header = [
            Paragraph("<b>Package</b>",       styles["body"]),
            Paragraph("<b>Current</b>",        styles["body"]),
            Paragraph("<b>Status</b>",         styles["body"]),
            Paragraph("<b>Risk</b>",           styles["body"]),
        ]
        rows = [header]
        for d in deps_list[:20]:
            status = _safe_str(d.get("status", ""), "unknown")
            risk   = _safe_str(d.get("risk", ""), "")
            rows.append([
                Paragraph(_truncate(_safe_str(d.get("name", ""), "?"), 30), styles["body_small"]),
                Paragraph(_safe_str(d.get("version", ""), "?"),           styles["body_small"]),
                Paragraph(status,                                          styles["body_small"]),
                Paragraph(risk,                                            styles["body_small"]),
            ])
        t2 = Table(rows, colWidths=[5 * cm, 3 * cm, 5 * cm, 4 * cm])
        t2.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        elems.append(t2)
    return elems


def _bug_fix_section(bf: dict, styles: dict):
    elems = []
    elems.append(Paragraph("🐛 Bug Fix Analysis", styles["section"]))
    elems.append(HRFlowable(width="100%", thickness=1, color=WARNING))

    patches = bf.get("patches", [])
    stats   = bf.get("stats", {})
    score   = _clamp(bf.get("score", 0))

    elems.append(Paragraph(
        f"Score: <b>{score:.0f}/100</b> — "
        f"<b>{stats.get('total_patches', len(patches))}</b> patches generated.",
        styles["body"],
    ))
    elems.append(Spacer(1, 4))

    for patch in patches[:8]:
        fname = _safe_str(patch.get("file", ""))
        issue = _truncate(_safe_str(patch.get("issue", ""), "Bug"), 100)
        fix   = _truncate(_safe_str(patch.get("fix", patch.get("suggestion", "")), ""), 200)
        elems.append(KeepTogether([
            Paragraph(f"<b>📄 {_truncate(fname, 60)}</b>", styles["body"]),
            Paragraph(f"Issue: {issue}",  styles["body_small"]),
            Paragraph(f"Fix: {fix}",     styles["body_small"]),
            Spacer(1, 3),
        ]))
    return elems


def _risk_section(rh: dict, styles: dict):
    elems = []
    elems.append(Paragraph("🗺️ Risk Heatmap", styles["section"]))
    elems.append(HRFlowable(width="100%", thickness=1, color=DANGER))

    overall = _clamp(rh.get("overall_risk_score", 50))
    colour  = _score_colour(100 - overall)
    elems.append(Paragraph(
        f'Overall Risk Score: <font color="#{colour.hexval()[2:]}"><b>{overall:.0f} / 100</b></font>',
        styles["body"],
    ))
    elems.append(Spacer(1, 4))

    hotspots = rh.get("hotspots", [])
    if hotspots:
        elems.append(Paragraph("<b>High-Risk Files</b>", styles["subsection"]))
        header = [
            Paragraph("<b>File</b>",  styles["body"]),
            Paragraph("<b>Risk</b>",  styles["body"]),
            Paragraph("<b>Reason</b>", styles["body"]),
        ]
        rows = [header]
        for hs in hotspots[:15]:
            risk   = _clamp(hs.get("risk_score", hs.get("risk", 0)))
            reason = _truncate(_safe_str(hs.get("reason", hs.get("factors", "")), ""), 100)
            rows.append([
                Paragraph(_truncate(_safe_str(hs.get("file", ""), "?"), 45), styles["body_small"]),
                Paragraph(f"{risk:.0f}",          styles["body_small"]),
                Paragraph(reason,                  styles["body_small"]),
            ])
        t = Table(rows, colWidths=[8 * cm, 2 * cm, 7 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), DANGER),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        elems.append(t)
    return elems


def _architecture_section(arch: dict, styles: dict):
    elems = []
    elems.append(Paragraph("🏗️ Architecture Analysis", styles["section"]))
    elems.append(HRFlowable(width="100%", thickness=1, color=INFO))

    pattern     = _safe_str(arch.get("pattern", arch.get("architecture_type", "")), "Unknown")
    components  = arch.get("components", [])
    score       = _clamp(arch.get("score", 70))

    elems.append(Paragraph(
        f"Architectural Pattern: <b>{pattern}</b> — Score: <b>{score:.0f}/100</b>",
        styles["body"],
    ))
    elems.append(Spacer(1, 4))

    if components:
        elems.append(Paragraph("<b>Detected Components</b>", styles["subsection"]))
        for comp in components[:12]:
            if isinstance(comp, dict):
                name = _safe_str(comp.get("name", comp.get("component", "")), "Component")
                desc = _truncate(_safe_str(comp.get("description", comp.get("role", "")), ""), 120)
                elems.append(Paragraph(f"• <b>{name}</b>: {desc}", styles["body_small"]))
            else:
                elems.append(Paragraph(f"• {_truncate(str(comp), 120)}", styles["body_small"]))
    return elems


def _time_machine_section(tm: dict, styles: dict):
    elems = []
    elems.append(Paragraph("⏳ Time Machine Analysis", styles["section"]))
    elems.append(HRFlowable(width="100%", thickness=1, color=INFO))

    commits = tm.get("commits", []) if isinstance(tm, dict) else []
    summary = _truncate(_safe_str(tm.get("summary", tm.get("insight", "")), ""), 220) if isinstance(tm, dict) else ""

    elems.append(Paragraph(
        f"Commits analyzed: <b>{len(commits)}</b>",
        styles["body"],
    ))

    if summary:
        elems.append(Spacer(1, 3))
        elems.append(Paragraph(summary, styles["body_small"]))

    if commits:
        elems.append(Spacer(1, 4))
        elems.append(Paragraph("<b>Recent Commit Highlights</b>", styles["subsection"]))
        for c in commits[:10]:
            if isinstance(c, dict):
                sha = _safe_str(c.get("sha", c.get("id", "")), "")[:10]
                msg = _truncate(_safe_str(c.get("message", c.get("title", "")), "Commit"), 110)
                author = _safe_str(c.get("author", ""), "")
                line = f"• <b>{sha}</b> {msg}" if sha else f"• {msg}"
                if author:
                    line += f" <font color=\"#6c757d\">({author})</font>"
                elems.append(Paragraph(line, styles["body_small"]))
            else:
                elems.append(Paragraph(f"• {_truncate(str(c), 120)}", styles["body_small"]))
    return elems


def _footer_note(styles: dict):
    return [
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=0.5, color=MID_GREY),
        Paragraph(
            f"Generated by <b>RepoMind</b> on {datetime.now().strftime('%d %B %Y at %H:%M')}. "
            "This report is auto-generated and intended as a starting point for human review.",
            ParagraphStyle("footer", fontName="Helvetica", fontSize=7.5,
                           textColor=MID_GREY, alignment=TA_CENTER),
        ),
    ]


# ── public API ────────────────────────────────────────────────────────────────

def generate_repomind_report(results: dict, repo_info: dict) -> bytes:
    """
    Generate a PDF report from RepoMind analysis results.

    Parameters
    ----------
    results   : dict returned by the orchestration step in app.py
    repo_info : dict returned by get_repo_info()

    Returns
    -------
    bytes : raw PDF bytes ready for st.download_button
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        title=f"RepoMind Report – {repo_info.get('name', 'Repository')}",
        author="RepoMind",
    )

    styles = _build_styles()
    story  = []

    # ── cover / header ────────────────────────────────────────────────────────
    story.append(_header_table(repo_info, styles))
    story.append(Spacer(1, 14))

    # ── summary scores ────────────────────────────────────────────────────────
    story.append(Paragraph("📊 Summary Scores", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
    story.append(Spacer(1, 4))
    story.append(_scores_table(results, styles))
    story.append(Spacer(1, 10))

    # ── individual sections ───────────────────────────────────────────────────
    if "code_review" in results:
        story.extend(_code_review_section(results["code_review"], styles))
        story.append(Spacer(1, 8))

    if "security" in results:
        story.extend(_security_section(results["security"], styles))
        story.append(Spacer(1, 8))

    if "documentation" in results:
        story.extend(_documentation_section(results["documentation"], styles))
        story.append(Spacer(1, 8))

    if "dependency" in results:
        story.extend(_dependency_section(results["dependency"], styles))
        story.append(Spacer(1, 8))

    if "bug_fix" in results:
        story.extend(_bug_fix_section(results["bug_fix"], styles))
        story.append(Spacer(1, 8))

    if "risk_heatmap" in results:
        story.extend(_risk_section(results["risk_heatmap"], styles))
        story.append(Spacer(1, 8))

    if "architecture" in results:
        story.extend(_architecture_section(results["architecture"], styles))
        story.append(Spacer(1, 8))

    if "time_machine" in results:
        story.extend(_time_machine_section(results["time_machine"], styles))
        story.append(Spacer(1, 8))

    # ── footer ────────────────────────────────────────────────────────────────
    story.extend(_footer_note(styles))

    doc.build(story)
    return buffer.getvalue()
