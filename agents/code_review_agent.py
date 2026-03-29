 # agents/code_review_agent.py
# ============================================
# RepoMind - Code Review Agent
# Returns all fields expected by app.py
# ============================================

import ast
import re
import os
from utils.llm import get_gemini_response


def run_code_review_agent(files: dict[str, str]) -> dict:
    """
    Run deep code review on all files.
    Returns fields matching the app.py display function.
    """

    all_issues  = []
    file_scores = {}

    # ---- Build file/folder metadata ----
    all_paths   = list(files.keys())
    all_folders = sorted(set(
        p.rsplit("/", 1)[0] for p in all_paths if "/" in p
    ))

    code_extensions = (".py", ".js", ".ts", ".cs", ".java", ".go",
                       ".rb", ".php", ".cpp", ".c", ".jsx", ".tsx")
    source_files = [p for p in all_paths if any(p.endswith(e) for e in code_extensions)]

    # ---- Step 1: Local heuristic checks (no API, instant) ----
    for filepath, content in files.items():
        local_issues = _local_heuristic_review(filepath, content)
        all_issues.extend(local_issues)

    # ---- Step 2: Select files for AI review ----
    # Prioritise files that already have local issues
    flagged  = set(i["file"] for i in all_issues)
    priority = {k: v for k, v in files.items() if k in flagged and any(k.endswith(e) for e in code_extensions) and len(v) < 15000}
    others   = {k: v for k, v in files.items() if k not in flagged and any(k.endswith(e) for e in code_extensions) and len(v) < 15000}
    selected = dict(list(priority.items())[:2] + list(others.items())[:1])

    reviewed_paths = list(selected.keys())

    # ---- Step 3: AI review with code suggestions ----
    for filepath, content in selected.items():
        print(f"   AI reviewing: {filepath}")
        lang = _detect_language(filepath)

        prompt = f"""You are a senior {lang} engineer doing a thorough code review.

FILE: {filepath}
LANGUAGE: {lang}

CODE:
```
{content[:4000]}
```

Find real issues and provide WORKING CODE FIXES.
Rules:
- Fixes must NOT change program behavior
- Fixes must NOT increase time complexity
- Be specific about line numbers
- Maximum 4 issues per file

For each issue use EXACTLY this format:

---ISSUE---
TITLE: [short descriptive title]
FILE: {filepath}
LINE: [line number or range]
SEVERITY: [HIGH / MEDIUM / LOW]
CATEGORY: [Performance / Readability / Security / Best Practice / Complexity]
PROBLEM: [1-2 sentences: why this is a problem]
ORIGINAL_CODE:
```{lang.lower()}
[the problematic code snippet, max 8 lines]
```
SUGGESTED_CODE:
```{lang.lower()}
[the improved version with same functionality]
```
EXPLANATION: [one sentence: what changed and why it's better]
---END---

Focus on:
1. Reducing complexity (deep nesting → early returns)
2. Performance (O(n²) → O(n) using better data structures)
3. Readability (long methods, unclear names, long lines)
4. {lang} best practices
5. Potential bugs

End your response with:
SCORE: [0-100 integer for overall file quality]
"""

        response    = get_gemini_response(prompt, temperature=0.2)
        ai_issues   = _parse_ai_review(response, filepath, lang)
        all_issues.extend(ai_issues)
        file_scores[filepath] = _extract_score(response)

    # ---- Step 4: Calculate scores and stats ----
    overall_score = int(sum(file_scores.values()) / len(file_scores)) if file_scores else 75

    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 2))

    high   = sum(1 for i in all_issues if i.get("severity") == "HIGH")
    medium = sum(1 for i in all_issues if i.get("severity") == "MEDIUM")
    low    = sum(1 for i in all_issues if i.get("severity") == "LOW")

    highlights = sorted(file_scores.items(), key=lambda x: x[1])[:3]

    summary = (
        f"Reviewed **{len(reviewed_paths)}** files out of {len(all_paths)} total. "
        f"Found **{len(all_issues)}** issues: "
        f"🔴 {high} high, 🟡 {medium} medium, 🟢 {low} low. "
        f"Overall code quality score: **{overall_score}/100**."
    )

    return {
        # ---- Fields used by app.py display ----
        "summary":               summary,
        "issues":                all_issues,
        "score":                 overall_score,
        "highlights":            highlights,

        # ---- File/folder metadata ----
        "files_detected":        len(all_paths),
        "files_reviewed":        len(reviewed_paths),
        "total_findings":        len(all_issues),
        "folder_count":          len(all_folders),
        "source_files_detected": len(source_files),
        "total_items":           len(all_paths) + len(all_folders),

        # ---- Lists for expanders ----
        "detected_file_list":    all_paths,
        "reviewed_file_list":    reviewed_paths,
        "detected_folder_list":  all_folders,
    }


# ============================================================
# LOCAL HEURISTIC REVIEW — fast, no API call
# ============================================================

def _local_heuristic_review(filepath: str, content: str) -> list[dict]:
    """Fast checks for any programming language."""
    issues = []
    lines  = content.split("\n")

    # --- Long lines ---
    long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 140]
    if long_lines:
        sample = lines[long_lines[0]-1].strip()
        issues.append({
            "file":           filepath,
            "severity":       "LOW",
            "category":       "Readability",
            "issue":          "Long lines reduce readability",
            "line":           ", ".join(str(l) for l in long_lines[:5]) + (f" (+{len(long_lines)-5} more)" if len(long_lines) > 5 else ""),
            "description":    f"Found {len(long_lines)} lines longer than 140 characters, which makes the file harder to review and maintain.",
            "fix":            "Wrap long expressions, split chained calls, or move large literals into named variables.",
            "original_code":  sample[:100] + ("..." if len(sample) > 100 else ""),
            "suggested_code": "// Break into multiple lines\nvar result = someObject\n    .method1(param1)\n    .method2(param2);",
            "source":         "Local Heuristics",
        })

    # --- Large file ---
    if len(lines) > 500:
        issues.append({
            "file":           filepath,
            "severity":       "MEDIUM",
            "category":       "Complexity",
            "issue":          "Large file size",
            "line":           "N/A",
            "description":    f"This file has {len(lines)} lines. Large files are harder to review and usually hide multiple responsibilities.",
            "fix":            "Split the file into smaller modules, each handling one clear responsibility.",
            "original_code":  None,
            "suggested_code": None,
            "source":         "Local Heuristics",
        })

    # --- Python AST ---
    if filepath.endswith(".py"):
        issues.extend(_check_python_ast(filepath, content))

    # --- TODO/FIXME ---
    for i, line in enumerate(lines):
        if re.search(r"\b(TODO|FIXME|HACK)\b", line, re.IGNORECASE):
            issues.append({
                "file":           filepath,
                "severity":       "LOW",
                "category":       "Best Practice",
                "issue":          "Unresolved TODO/FIXME",
                "line":           str(i+1),
                "description":    f"Unfinished work marker: `{line.strip()[:80]}`",
                "fix":            "Complete the task or create a proper issue ticket.",
                "original_code":  line.strip(),
                "suggested_code": None,
                "source":         "Local Heuristics",
            })

    # --- Deep nesting ---
    deep = [i+1 for i, line in enumerate(lines) if len(line) - len(line.lstrip()) >= 16 and line.strip()]
    if len(deep) >= 3:
        issues.append({
            "file":        filepath,
            "severity":    "MEDIUM",
            "category":    "Complexity",
            "issue":       "Deep nesting detected",
            "line":        str(deep[0]),
            "description": f"Found {len(deep)} lines with 4+ nesting levels. Deep nesting is hard to read and test.",
            "fix":         "Use early returns / guard clauses to flatten the nesting.",
            "original_code": (
                "if (condition1) {\n"
                "    if (condition2) {\n"
                "        if (condition3) {\n"
                "            doWork();\n"
                "        }\n"
                "    }\n"
                "}"
            ),
            "suggested_code": (
                "if (!condition1) return;\n"
                "if (!condition2) return;\n"
                "if (!condition3) return;\n"
                "doWork();"
            ),
            "source": "Local Heuristics",
        })

    return issues


def _check_python_ast(filepath: str, content: str) -> list[dict]:
    """Python-specific structural checks via AST."""
    issues = []
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return [{
            "file": filepath, "severity": "HIGH", "category": "Bug",
            "issue": "Python Syntax Error", "line": str(e.lineno),
            "description": str(e), "fix": "Fix the syntax error — this file cannot be imported.",
            "original_code": None, "suggested_code": None, "source": "AST Parser",
        }]

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Missing docstring
            has_doc = (
                node.body and
                isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, ast.Constant)
            )
            if not has_doc and not node.name.startswith("_"):
                issues.append({
                    "file":           filepath,
                    "severity":       "LOW",
                    "category":       "Readability",
                    "issue":          f"Missing docstring: `{node.name}()`",
                    "line":           str(node.lineno),
                    "description":    f"Function `{node.name}` has no docstring explaining what it does.",
                    "fix":            "Add a Google-style docstring right after the def line.",
                    "original_code":  f"def {node.name}(param):\n    pass  # no docstring",
                    "suggested_code": (
                        f'def {node.name}(param):\n'
                        f'    """What this function does.\n\n'
                        f'    Args:\n'
                        f'        param: Description of parameter.\n\n'
                        f'    Returns:\n'
                        f'        Description of return value.\n'
                        f'    """\n'
                        f'    pass'
                    ),
                    "source": "AST Parser",
                })

            # Long function
            func_len = (node.end_lineno - node.lineno) if hasattr(node, "end_lineno") else 0
            if func_len > 50:
                issues.append({
                    "file":           filepath,
                    "severity":       "MEDIUM",
                    "category":       "Complexity",
                    "issue":          f"Long function `{node.name}()` ({func_len} lines)",
                    "line":           str(node.lineno),
                    "description":    f"`{node.name}` is {func_len} lines long. Functions over 30 lines usually do too many things and are hard to test.",
                    "fix":            f"Split `{node.name}` into 2-3 smaller helper functions, each doing one clear task.",
                    "original_code":  f"def {node.name}():\n    # ... {func_len} lines of mixed logic ...",
                    "suggested_code": (
                        f"def {node.name}():\n"
                        f"    data = _fetch_data()     # extracted helper\n"
                        f"    result = _process(data)  # extracted helper\n"
                        f"    return _format(result)   # extracted helper\n\n"
                        f"def _fetch_data(): ...\n"
                        f"def _process(data): ...\n"
                        f"def _format(result): ..."
                    ),
                    "source": "AST Parser",
                })

    return issues


# ============================================================
# AI RESPONSE PARSER
# ============================================================

def _parse_ai_review(response: str, filepath: str, lang: str) -> list[dict]:
    """Parse Gemini's structured ---ISSUE--- blocks."""
    issues = []
    blocks = re.split(r"---ISSUE---", response)

    for block in blocks[1:]:
        if "---END---" not in block:
            continue
        block = block.split("---END---")[0].strip()

        issue = {
            "file":           filepath,
            "severity":       "MEDIUM",
            "category":       "General",
            "source":         f"Gemini AI ({lang})",
            "original_code":  None,
            "suggested_code": None,
        }

        # Extract code blocks
        orig = re.search(r"ORIGINAL_CODE:\s*```[^\n]*\n(.*?)```",   block, re.DOTALL)
        sugg = re.search(r"SUGGESTED_CODE:\s*```[^\n]*\n(.*?)```",  block, re.DOTALL)
        if orig: issue["original_code"]  = orig.group(1).strip()
        if sugg: issue["suggested_code"] = sugg.group(1).strip()

        # Extract text fields
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("TITLE:"):        issue["issue"]       = line.replace("TITLE:","").strip()
            elif line.startswith("FILE:"):       issue["file"]        = line.replace("FILE:","").strip()
            elif line.startswith("LINE:"):       issue["line"]        = line.replace("LINE:","").strip()
            elif line.startswith("SEVERITY:"):   issue["severity"]    = line.replace("SEVERITY:","").strip().upper()
            elif line.startswith("CATEGORY:"):   issue["category"]    = line.replace("CATEGORY:","").strip()
            elif line.startswith("PROBLEM:"):    issue["description"] = line.replace("PROBLEM:","").strip()
            elif line.startswith("EXPLANATION:"): issue["fix"]        = line.replace("EXPLANATION:","").strip()

        if "issue" in issue:
            issues.append(issue)

    return issues


# ============================================================
# HELPERS
# ============================================================

def _detect_language(filepath: str) -> str:
    ext_map = {
        ".py":"Python", ".js":"JavaScript", ".ts":"TypeScript",
        ".cs":"C#", ".java":"Java", ".go":"Go", ".rs":"Rust",
        ".cpp":"C++", ".c":"C", ".rb":"Ruby", ".php":"PHP",
        ".swift":"Swift", ".kt":"Kotlin", ".jsx":"React JSX", ".tsx":"React TSX",
    }
    for ext, lang in ext_map.items():
        if filepath.endswith(ext): return lang
    return "Code"


def _extract_score(response: str) -> int:
    for line in response.split("\n"):
        if line.strip().startswith("SCORE:"):
            try:
                return min(100, max(0, int("".join(filter(str.isdigit, line.replace("SCORE:","").strip()[:3])))))
            except Exception:
                pass
    return 72