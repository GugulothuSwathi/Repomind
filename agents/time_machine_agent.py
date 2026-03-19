# agents/time_machine_agent.py
# ============================================
# RepoMind - Repository Time Machine Agent
#
# Analyzes how a repository evolved over time:
# - Historical commit timeline
# - Architecture evolution per commit
# - Risk timeline (security/complexity over time)
# - Predictive future risk
# ============================================

import os
import json
import tempfile
import shutil
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from utils.llm import get_gemini_response, get_gemini_response_json
from utils.config import GITHUB_TOKEN


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def run_time_machine_agent(
    github_url: str,
    max_commits: int = 15,
    branch: str = "main",
) -> dict:
    """
    Full Time Machine analysis for a repository.

    Returns a dict with:
      - commits          : list of commit metadata
      - file_evolution   : files added/removed per commit
      - risk_timeline    : risk score per commit
      - arch_snapshots   : architecture graph per commit
      - predictions      : predicted risky files
      - summary          : AI summary of evolution
    """
    result = {
        "commits": [],
        "file_evolution": [],
        "risk_timeline": [],
        "arch_snapshots": [],
        "predictions": [],
        "summary": "",
        "error": None,
    }

    # ── 1. Clone the repo into a temp directory ──────────────────────────
    tmpdir = tempfile.mkdtemp(prefix="repomind_tm_")
    try:
        clone_url = _build_clone_url(github_url)
        ret = subprocess.run(
            ["git", "clone", "--depth", str(max_commits * 2), clone_url, tmpdir],
            capture_output=True, text=True, timeout=120,
        )
        if ret.returncode != 0:
            # Try without auth token
            ret2 = subprocess.run(
                ["git", "clone", "--depth", str(max_commits * 2), github_url, tmpdir],
                capture_output=True, text=True, timeout=120,
            )
            if ret2.returncode != 0:
                result["error"] = f"Clone failed: {ret2.stderr[:300]}"
                return result

        # ── 2. Fetch commit history ───────────────────────────────────────
        commits = _get_commit_history(tmpdir, max_commits)
        result["commits"] = commits

        if not commits:
            result["error"] = "No commits found in repository."
            return result

        # ── 3. Per-commit analysis ────────────────────────────────────────
        prev_files: set[str] = set()
        churn_map: dict[str, int] = defaultdict(int)   # file → total lines changed
        bug_density: dict[str, int] = defaultdict(int) # file → bug-related commits

        for commit in commits:
            sha = commit["hash"]

            # File changes at this commit
            file_changes = _get_file_changes(tmpdir, sha)
            commit["files_changed"] = file_changes

            added   = [f for f in file_changes if file_changes[f]["status"] == "A"]
            removed = [f for f in file_changes if file_changes[f]["status"] == "D"]
            modified = [f for f in file_changes if file_changes[f]["status"] == "M"]

            # Track churn
            for fpath, info in file_changes.items():
                churn_map[fpath] += info.get("lines_changed", 0)
                if _is_bug_commit(commit.get("message", "")):
                    bug_density[fpath] += 1

            # File evolution snapshot
            current_files = (prev_files | set(added)) - set(removed)
            result["file_evolution"].append({
                "hash":          sha,
                "date":          commit["date"],
                "message":       commit["message"],
                "author":        commit["author"],
                "files_added":   added,
                "files_removed": removed,
                "files_modified": modified,
                "total_files":   len(current_files),
            })
            prev_files = current_files

            # Risk score for this commit (lightweight — no full checkout)
            risk = _estimate_commit_risk(commit, file_changes)
            result["risk_timeline"].append({
                "hash":    sha,
                "date":    commit["date"],
                "message": commit["message"][:60],
                "risk_score": risk["score"],
                "risk_level": risk["level"],
                "dominant_risk": risk["dominant"],
                "security_score": risk["security"],
                "complexity_score": risk["complexity"],
                "dependency_score": risk["dependency"],
            })

            # Architecture snapshot (import-level, from diff)
            arch = _extract_arch_snapshot(tmpdir, sha, file_changes)
            result["arch_snapshots"].append({
                "hash":       sha,
                "date":       commit["date"],
                "message":    commit["message"][:60],
                "nodes":      arch["nodes"],
                "edges":      arch["edges"],
                "mermaid":    arch["mermaid"],
            })

        # ── 4. Predictive Risk ────────────────────────────────────────────
        result["predictions"] = _predict_future_risk(churn_map, bug_density, result["risk_timeline"])

        # ── 5. AI Summary ─────────────────────────────────────────────────
        result["summary"] = _generate_evolution_summary(result)

    except Exception as exc:
        result["error"] = str(exc)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return result


# ─────────────────────────────────────────────
# GIT HELPERS
# ─────────────────────────────────────────────

def _build_clone_url(github_url: str) -> str:
    """Embed GITHUB_TOKEN into the clone URL for private/rate-limited repos."""
    token = GITHUB_TOKEN
    if token and "github.com" in github_url:
        url = github_url.replace("https://", f"https://{token}@")
        return url
    return github_url


def _get_commit_history(repo_dir: str, max_commits: int) -> list[dict]:
    """Return list of commit metadata dicts."""
    fmt = "%H|%ad|%an|%ae|%s"
    ret = subprocess.run(
        ["git", "log", f"--pretty=format:{fmt}", "--date=short", f"-{max_commits}"],
        cwd=repo_dir, capture_output=True, text=True, timeout=30,
    )
    commits = []
    for line in ret.stdout.strip().splitlines():
        parts = line.split("|", 4)
        if len(parts) == 5:
            commits.append({
                "hash":    parts[0],
                "date":    parts[1],
                "author":  parts[2],
                "email":   parts[3],
                "message": parts[4],
            })
    return commits


def _get_file_changes(repo_dir: str, sha: str) -> dict[str, dict]:
    """
    Return {filepath: {status, lines_added, lines_removed, lines_changed}}
    for a specific commit using git diff-tree.
    """
    # name-status
    ns_ret = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--name-status", sha],
        cwd=repo_dir, capture_output=True, text=True, timeout=15,
    )
    # numstat
    num_ret = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--numstat", sha],
        cwd=repo_dir, capture_output=True, text=True, timeout=15,
    )

    changes: dict[str, dict] = {}

    for line in ns_ret.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            status = parts[0][0]  # A / M / D / R
            fpath  = parts[-1]
            changes[fpath] = {"status": status, "lines_added": 0, "lines_removed": 0, "lines_changed": 0}

    for line in num_ret.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            added   = int(parts[0]) if parts[0].isdigit() else 0
            removed = int(parts[1]) if parts[1].isdigit() else 0
            fpath   = parts[2]
            if fpath in changes:
                changes[fpath]["lines_added"]   = added
                changes[fpath]["lines_removed"]  = removed
                changes[fpath]["lines_changed"]  = added + removed

    return changes


def _is_bug_commit(message: str) -> bool:
    keywords = ["fix", "bug", "error", "patch", "hotfix", "issue", "crash", "broken", "revert"]
    msg_lower = message.lower()
    return any(k in msg_lower for k in keywords)


# ─────────────────────────────────────────────
# RISK ESTIMATION (no full checkout needed)
# ─────────────────────────────────────────────

RISKY_PATTERNS = [
    "password", "secret", "token", "api_key", "hardcoded",
    "eval(", "exec(", "subprocess", "os.system", "shell=True",
    "sql", "inject", "TODO", "FIXME", "HACK", "XXX",
]

def _estimate_commit_risk(commit: dict, file_changes: dict) -> dict:
    """Estimate risk of a commit from metadata + file list (no checkout)."""
    security_score   = 0
    complexity_score = 0
    dependency_score = 0

    msg = commit.get("message", "").lower()

    # Security signals from commit message
    sec_keywords = ["security", "vuln", "cve", "inject", "xss", "auth", "passwd", "secret", "token"]
    security_score += sum(5 for k in sec_keywords if k in msg)

    # Bug commit raises complexity risk
    if _is_bug_commit(msg):
        complexity_score += 15

    # File-level signals
    py_files = [f for f in file_changes if f.endswith(".py")]
    req_files = [f for f in file_changes if "requirements" in f.lower() or f.endswith((".toml", ".json"))]

    complexity_score += min(len(py_files) * 3, 30)
    dependency_score += min(len(req_files) * 10, 40)

    # High churn = more risk
    total_lines = sum(v.get("lines_changed", 0) for v in file_changes.values())
    complexity_score += min(total_lines // 20, 25)

    # Weighted total
    score = int(
        0.40 * min(security_score,   100) +
        0.35 * min(complexity_score, 100) +
        0.25 * min(dependency_score, 100)
    )
    score = max(0, min(score, 100))

    if score >= 70:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    dominant = max(
        [("security", security_score), ("complexity", complexity_score), ("dependency", dependency_score)],
        key=lambda x: x[1]
    )[0]

    return {
        "score":      score,
        "level":      level,
        "dominant":   dominant,
        "security":   min(security_score,   100),
        "complexity": min(complexity_score, 100),
        "dependency": min(dependency_score, 100),
    }


# ─────────────────────────────────────────────
# ARCHITECTURE SNAPSHOT
# ─────────────────────────────────────────────

def _extract_arch_snapshot(repo_dir: str, sha: str, file_changes: dict) -> dict:
    """
    Build a lightweight architecture graph from the files changed in this commit.
    Returns nodes, edges, and a Mermaid diagram string.
    """
    # Collect Python files that were added or modified
    py_files = [f for f, info in file_changes.items()
                if f.endswith(".py") and info["status"] in ("A", "M")]

    nodes: list[str] = []
    edges: list[tuple[str, str]] = []

    for fpath in py_files[:20]:  # limit for performance
        module = fpath.replace("/", ".").replace(".py", "")
        short  = fpath.split("/")[-1].replace(".py", "")
        nodes.append(short)

        # Try to read the file at this commit
        try:
            content_ret = subprocess.run(
                ["git", "show", f"{sha}:{fpath}"],
                cwd=repo_dir, capture_output=True, text=True, timeout=5,
            )
            if content_ret.returncode == 0:
                for line in content_ret.stdout.splitlines()[:50]:
                    line = line.strip()
                    if line.startswith("from ") or line.startswith("import "):
                        imported = _parse_import(line)
                        if imported and imported != short:
                            edges.append((short, imported))
        except Exception:
            pass

    # De-duplicate edges
    edges = list(set(edges))[:30]

    # Build Mermaid
    mermaid = _build_mermaid(nodes, edges)

    return {"nodes": nodes, "edges": [{"from": e[0], "to": e[1]} for e in edges], "mermaid": mermaid}


def _parse_import(line: str) -> Optional[str]:
    """Extract module name from an import line."""
    try:
        if line.startswith("from "):
            parts = line.split()
            return parts[1].split(".")[0] if len(parts) > 1 else None
        elif line.startswith("import "):
            return line.split()[1].split(".")[0]
    except Exception:
        pass
    return None


def _build_mermaid(nodes: list[str], edges: list[tuple]) -> str:
    if not nodes:
        return "graph LR\n    A[No Python files changed]"
    lines = ["graph LR"]
    for node in nodes[:15]:
        safe = node.replace("-", "_").replace(".", "_")
        lines.append(f"    {safe}[{node}]")
    for src, dst in edges[:20]:
        safe_src = src.replace("-", "_").replace(".", "_")
        safe_dst = dst.replace("-", "_").replace(".", "_")
        lines.append(f"    {safe_src} --> {safe_dst}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# PREDICTIVE RISK
# ─────────────────────────────────────────────

def _predict_future_risk(
    churn_map: dict[str, int],
    bug_density: dict[str, int],
    risk_timeline: list[dict],
) -> list[dict]:
    """
    Simple weighted scoring to predict which files are most likely to cause issues.
    No external ML library needed — pure Python scoring.
    """
    all_files = set(churn_map.keys()) | set(bug_density.keys())
    if not all_files:
        return []

    max_churn = max(churn_map.values(), default=1) or 1
    max_bugs  = max(bug_density.values(), default=1) or 1

    # Average recent risk trend
    recent = risk_timeline[-5:] if len(risk_timeline) >= 5 else risk_timeline
    avg_recent_risk = sum(r["risk_score"] for r in recent) / len(recent) if recent else 30

    predictions = []
    for fpath in all_files:
        if not fpath.endswith((".py", ".js", ".ts", ".java", ".go")):
            continue

        churn_norm = churn_map.get(fpath, 0) / max_churn
        bugs_norm  = bug_density.get(fpath, 0) / max_bugs

        predicted_score = int(
            0.45 * churn_norm * 100 +
            0.40 * bugs_norm  * 100 +
            0.15 * avg_recent_risk
        )
        predicted_score = min(predicted_score, 100)

        if predicted_score >= 20:
            predictions.append({
                "file":            fpath,
                "predicted_score": predicted_score,
                "churn_lines":     churn_map.get(fpath, 0),
                "bug_commits":     bug_density.get(fpath, 0),
                "risk_level":      "HIGH" if predicted_score >= 60 else "MEDIUM" if predicted_score >= 35 else "LOW",
                "reason":          _prediction_reason(churn_norm, bugs_norm),
            })

    predictions.sort(key=lambda x: x["predicted_score"], reverse=True)
    return predictions[:10]


def _prediction_reason(churn: float, bugs: float) -> str:
    if bugs > 0.5:
        return "Frequent bug-fix commits suggest ongoing instability"
    if churn > 0.7:
        return "Very high churn — file changes frequently across commits"
    if churn > 0.4:
        return "Moderate churn combined with past issues"
    return "Historical change patterns indicate risk"


# ─────────────────────────────────────────────
# AI SUMMARY
# ─────────────────────────────────────────────

def _generate_evolution_summary(result: dict) -> str:
    """Ask Gemini to summarize the repository's evolution story."""
    commits = result.get("commits", [])
    risk_tl = result.get("risk_timeline", [])
    preds   = result.get("predictions", [])

    if not commits:
        return "No commit history available to summarize."

    commit_summaries = "\n".join(
        f"- [{c['date']}] {c['author']}: {c['message'][:80]}"
        for c in commits[:10]
    )
    risk_summary = ""
    if risk_tl:
        avg_risk = sum(r["risk_score"] for r in risk_tl) / len(risk_tl)
        max_risk_commit = max(risk_tl, key=lambda x: x["risk_score"])
        risk_summary = (
            f"Average risk score: {avg_risk:.1f}/100. "
            f"Highest risk commit: '{max_risk_commit['message']}' "
            f"(score {max_risk_commit['risk_score']})."
        )

    pred_files = ", ".join(p["file"] for p in preds[:3]) if preds else "none identified"

    prompt = f"""Analyze this repository's evolution and write a 3-4 sentence technical summary.

Recent commits:
{commit_summaries}

Risk analysis: {risk_summary}
Predicted high-risk files for future: {pred_files}

Write a concise, insightful summary about:
1. What kind of project this appears to be
2. The development pace and patterns
3. Risk trend (improving or worsening)
4. Key files to watch

Keep it technical but readable. No bullet points — flowing prose."""
    try:
        response = get_gemini_response(prompt, temperature=0.4)
        if "Gemini API Error" in response or "quota" in response.lower():
            return f"Analyzed {len(commits)} commits. {risk_summary} Top predicted risk files: {pred_files}."
        return response
    except Exception:
        return f"Analyzed {len(commits)} commits. {risk_summary}"