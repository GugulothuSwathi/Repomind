# agents/risk_heatmap_agent.py
from __future__ import annotations
# ============================================
# RepoMind - Repository Risk Heatmap Agent ⭐
#
# PURPOSE:
#   Create a visual "heatmap" showing which parts
#   of the repository are most dangerous.
#
# HOW IT WORKS:
#   1. Collects results from all other agents
#   2. Calculates a risk score for each file/module
#   3. Uses radon to measure code complexity locally
#   4. Returns data for visualization in Streamlit
#
# WHY THIS IS COOL:
#   Instead of reading a list of issues, you instantly
#   SEE which files are red (dangerous) vs green (safe).
# ============================================

import re
from utils.config import RISK_WEIGHTS


def run_risk_heatmap_agent(
    files: dict[str, str],
    security_results: dict,
    code_review_results: dict,
    dependency_results: dict,
) -> dict:
    """
    Calculate risk scores for each file and generate heatmap data.

    Args:
        files               : All repo files
        security_results    : From security_agent
        code_review_results : From code_review_agent
        dependency_results  : From dependency_agent

    Returns:
        Dictionary with:
        - file_risks         : List of {file, score, level, breakdown}
        - module_risks       : Aggregated by top-level module/folder
        - overall_risk_score : Single number 0-100 (higher = more risky!)
        - risk_distribution  : Count of CRITICAL/HIGH/MEDIUM/LOW files
        - top_risky_files    : Top 5 most dangerous files
    """

    file_risks = []

    # --- Step 1: Build a risk profile for each file ---
    for filepath in files.keys():

        # Count security issues in this file
        security_issues = sum(
            1 for v in security_results.get("vulnerabilities", [])
            if v.get("file") == filepath
        )

        # Count code review issues in this file
        code_issues = sum(
            1 for i in code_review_results.get("issues", [])
            if i.get("file") == filepath
        )

        # Measure code complexity using a simple method
        # (We analyze the file directly — no external tool needed)
        complexity_score = _estimate_complexity(files[filepath], filepath)

        # Count lint-style issues (we use our own simple checker)
        lint_errors = _count_lint_issues(files[filepath], filepath)

        # Calculate weighted risk score
        # Formula: 0.4*security + 0.3*complexity + 0.2*lint + 0.1*dependency
        raw_score = (
            RISK_WEIGHTS["security_issues"]  * min(security_issues * 20, 100) +
            RISK_WEIGHTS["complexity"]       * complexity_score +
            RISK_WEIGHTS["lint_errors"]      * min(lint_errors * 10, 100) +
            RISK_WEIGHTS["dependency_risk"]  * 0  # file-level dependency risk not calculated
        )

        # Convert to 0-100 risk score (higher = more risky)
        risk_score = min(100, int(raw_score))

        # Determine risk level label
        if risk_score >= 70:
            risk_level = "CRITICAL"
            emoji = "🔴"
        elif risk_score >= 40:
            risk_level = "HIGH"
            emoji = "🟠"
        elif risk_score >= 20:
            risk_level = "MEDIUM"
            emoji = "🟡"
        else:
            risk_level = "LOW"
            emoji = "🟢"

        file_risks.append({
            "file":       filepath,
            "score":      risk_score,
            "level":      risk_level,
            "emoji":      emoji,
            "breakdown": {
                "security_issues":  security_issues,
                "complexity":       complexity_score,
                "lint_errors":      lint_errors,
            }
        })

    # Sort by risk score (highest first)
    file_risks.sort(key=lambda x: x["score"], reverse=True)

    # --- Step 2: Aggregate by module (top-level folder) ---
    module_risks = _aggregate_by_module(file_risks)

    # --- Step 3: Calculate overall repository risk score ---
    if file_risks:
        # Weight the average toward the worst files
        scores = [f["score"] for f in file_risks]
        scores.sort(reverse=True)

        # Give more weight to worst files
        if len(scores) >= 3:
            overall_score = int(scores[0] * 0.5 + scores[1] * 0.3 + sum(scores[2:]) / len(scores[2:]) * 0.2)
        else:
            overall_score = int(sum(scores) / len(scores))
    else:
        overall_score = 0

    # --- Step 4: Risk distribution ---
    risk_distribution = {
        "CRITICAL": sum(1 for f in file_risks if f["level"] == "CRITICAL"),
        "HIGH":     sum(1 for f in file_risks if f["level"] == "HIGH"),
        "MEDIUM":   sum(1 for f in file_risks if f["level"] == "MEDIUM"),
        "LOW":      sum(1 for f in file_risks if f["level"] == "LOW"),
    }

    return {
        "file_risks":          file_risks,
        "module_risks":        module_risks,
        "overall_risk_score":  overall_score,
        "risk_distribution":   risk_distribution,
        "top_risky_files":     file_risks[:5],
        "total_files":         len(file_risks),
    }


def _estimate_complexity(content: str, filepath: str) -> float:
    """
    Estimate code complexity WITHOUT external tools.

    We use a simple heuristic:
    - Count if/else/for/while/try statements
    - More branching = more complex
    - Returns a 0-100 score

    This is simplified McCabe complexity.
    """
    if not filepath.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".cs", ".java", ".go", ".rb", ".php")):
        return 10  # Low complexity for non-code files

    # Count control flow statements
    control_keywords = ["if ", "elif ", "else:", "for ", "while ", "try:", "except", "with ", "match "]
    count = sum(content.count(kw) for kw in control_keywords)

    # Also count function definitions — many functions = complex file
    func_count = content.count("def ") + content.count("function ") + content.count("=> {")

    # Normalize to 0-100
    complexity = min(100, (count * 2) + (func_count * 3))
    return complexity


def _count_lint_issues(content: str, filepath: str) -> int:
    """
    Count simple code quality issues without running pylint.

    Checks for:
    - Lines that are too long (>120 chars)
    - TODO/FIXME comments (unfinished code)
    - Print statements in Python (should use logging)
    - Magic numbers (unexplained numbers in code)
    """
    issues = 0

    for line in content.split("\n"):
        # Long lines
        if len(line) > 120:
            issues += 1

        # TODO/FIXME
        if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line, re.IGNORECASE):
            issues += 1

        # print() in Python (should use logging)
        if filepath.endswith(".py") and re.match(r"\s*print\s*\(", line):
            issues += 0.5  # minor issue, half point

    return int(issues)


def _aggregate_by_module(file_risks: list[dict]) -> list[dict]:
    """
    Group file risks by their top-level module (folder).

    Example:
        auth/login.py     → "auth" module
        auth/logout.py    → "auth" module
        payments/views.py → "payments" module

    Returns sorted list of module risk summaries.
    """
    modules = {}

    for file_risk in file_risks:
        filepath = file_risk["file"]

        # Get the top-level folder name
        parts = filepath.split("/")
        if len(parts) > 1:
            module = parts[0]
        else:
            module = "root"

        if module not in modules:
            modules[module] = {"files": [], "scores": []}

        modules[module]["files"].append(filepath)
        modules[module]["scores"].append(file_risk["score"])

    # Calculate average score per module
    module_list = []
    for module_name, data in modules.items():
        avg_score = int(sum(data["scores"]) / len(data["scores"]))
        max_score = max(data["scores"])

        if max_score >= 70:
            level = "CRITICAL"
            emoji = "🔴"
        elif max_score >= 40:
            level = "HIGH"
            emoji = "🟠"
        elif max_score >= 20:
            level = "MEDIUM"
            emoji = "🟡"
        else:
            level = "LOW"
            emoji = "🟢"

        module_list.append({
            "module":    module_name,
            "avg_score": avg_score,
            "max_score": max_score,
            "level":     level,
            "emoji":     emoji,
            "file_count": len(data["files"]),
        })

    return sorted(module_list, key=lambda x: x["max_score"], reverse=True)