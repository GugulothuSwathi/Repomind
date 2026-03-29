 # agents/bug_fix_agent.py
from __future__ import annotations
# ============================================
# RepoMind - Bug Fix Agent (FINAL FIX)
# ============================================

import re
from utils.llm import get_gemini_response


def run_bug_fix_agent(
    files: dict[str, str],
    security_results: dict,
    code_review_results: dict,
) -> dict:
    """Generate automatic patches for all detected issues."""

    # Print all file keys for debugging
    for k in list(files.keys())[:15]:
        print(f"   FILE: {k}")

    vulns = security_results.get("vulnerabilities", [])
    print(f"   Vulnerabilities from security agent: {len(vulns)}")
    for v in vulns:
        print(f"   VULN: {v.get('type')} | file={v.get('file')} | snippet={v.get('code_snippet','')[:50]}")

    patches = []

    # ======================================================
    # METHOD 1: Fix directly from security agent results
    # Uses code_snippet even if file path doesn't match
    # ======================================================
    for vuln in vulns[:2]:
        filepath = vuln.get("file", "")
        snippet  = vuln.get("code_snippet", "").strip()

        # Try to find the file with fuzzy matching
        matched_path = _find_file(filepath, files)

        if matched_path:
            # We have the actual file — get more context
            try:
                line_num     = int(str(vuln.get("line", 1)).split(",")[0].strip())
                lines        = files[matched_path].split("\n")
                start        = max(0, line_num - 6)
                end          = min(len(lines), line_num + 8)
                code_context = "\n".join(lines[start:end])
            except Exception:
                code_context = snippet or ""
        elif snippet:
            # No file match but we have a snippet — use it directly
            matched_path = filepath if filepath else "unknown.py"
            code_context = snippet
        else:
            continue

        if not code_context:
            continue

        lang  = _detect_language(matched_path)
        patch = _generate_patch_from_vuln(vuln, matched_path, code_context, lang)
        if patch:
            patches.append(patch)

    # ======================================================
    # METHOD 2: Directly scan files with broader patterns
    # This catches things the security agent might miss
    # ======================================================
    print(f"   Method 1 found {len(patches)} patches. Running Method 2...")
    direct = _direct_file_scan(files)
    for p in direct:
        dupe = any(
            x["file"] == p["file"] and x["vulnerability"] == p["vulnerability"]
            for x in patches
        )
        if not dupe:
            patches.append(p)

    # ======================================================
    # METHOD 3: Code review HIGH issues
    # ======================================================
    for issue in code_review_results.get("issues", [])[:1]:
        if issue.get("severity", "").upper() != "HIGH":
            continue
        already_fixed = issue.get("after_code") or issue.get("suggested_code")
        original      = issue.get("before_code") or issue.get("original_code", "")
        filepath      = issue.get("file", "")
        matched       = _find_file(filepath, files)

        if already_fixed and original:
            patches.append({
                "type":          "Code Quality Fix",
                "issue":         issue.get("issue", "Code Issue"),
                "vulnerability": issue.get("issue", "Code Issue"),
                "file":          matched or filepath,
                "line":          str(issue.get("line", "?")),
                "severity":      "HIGH",
                "original_code": original,
                "fixed_code":    already_fixed,
                "explanation":   issue.get("fix", "Code quality improvement."),
                "steps":         [],
                "cwe":           "",
                "priority":      2,
            })

    patches.sort(key=lambda x: x.get("priority", 2))
    sec_fixes  = sum(1 for p in patches if p.get("type") == "Security Fix")
    code_fixes = sum(1 for p in patches if p.get("type") == "Code Quality Fix")

    return {
        "patches": patches,
        "summary": f"Generated **{len(patches)}** patches: 🔒 **{sec_fixes}** security, ✨ **{code_fixes}** code quality.",
        "stats":   {"total_patches": len(patches), "security_fixes": sec_fixes, "code_quality_fixes": code_fixes},
    }


def _direct_file_scan(files: dict) -> list[dict]:
    """
    Scan files directly — MUCH broader patterns than security agent.
    Catches dvpwa-style async SQL, aiohttp patterns, etc.
    """
    patches = []

    # Very broad patterns — catches more variations
    PATTERNS = [
        {
            "name":    "SQL Injection",
            "regexes": [
                r'["\']SELECT.*WHERE.*["\'].*\+',       # "SELECT...WHERE..." + var
                r'["\']INSERT.*VALUES.*["\'].*\+',
                r'["\']UPDATE.*SET.*["\'].*\+',
                r'["\']DELETE.*FROM.*["\'].*\+',
                r'execute\s*\(\s*["\'].*\{',            # execute("...{var}...")
                r'execute\s*\(\s*f["\']',               # execute(f"...")
                r'format\s*\(.*\).*execute',            # .format().execute
                r'\.format\(.*\)',                      # any .format() near SQL keywords
                r'%s.*%.*["\']',                        # "...%s..." % var  (old style)
                r'conn\.execute\s*\(\s*["\']',          # conn.execute("...")
                r'cursor\.execute\s*\(\s*["\'].*\+',   # cursor.execute("..." + var)
                r'db\.execute\s*\(\s*["\'].*\+',
            ],
            "severity": "CRITICAL",
            "cwe":      "CWE-89",
            "fix":      "Use parameterized queries:\nawait conn.execute('SELECT * FROM t WHERE id=$1', user_id)\n# Never concatenate user input into SQL strings",
            "reason":   "User input is concatenated into SQL — attacker can manipulate the query.",
        },
        {
            "name":    "Hardcoded Secret",
            "regexes": [
                r'(password|passwd|secret|key|token)\s*[=:]\s*["\'][^"\']{5,}["\']',
                r'SECRET_KEY\s*=\s*["\'][^"\']+["\']',
                r'DATABASE_URL\s*=\s*["\'][^"\']+["\']',
                r'API_KEY\s*=\s*["\'][^"\']+["\']',
            ],
            "severity": "CRITICAL",
            "cwe":      "CWE-798",
            "fix":      "Use environment variables:\nimport os\npassword = os.getenv('PASSWORD')\n# Store actual values in .env file (never commit it)",
            "reason":   "Hardcoded credentials are exposed to anyone who reads the source code.",
        },
        {
            "name":    "Debug Mode Enabled",
            "regexes": [
                r'debug\s*=\s*True',
                r'DEBUG\s*=\s*True',
                r'\.run\(.*debug\s*=\s*True',
                r"app\.run\(",
            ],
            "severity": "HIGH",
            "cwe":      "CWE-94",
            "fix":      "Disable debug in production:\nDEBUG = os.getenv('DEBUG', 'False') == 'True'\n# Set DEBUG=False in production environment",
            "reason":   "Debug mode exposes stack traces and internal details to attackers.",
        },
        {
            "name":    "Code Injection",
            "regexes": [
                r'\beval\s*\(',
                r'\bexec\s*\(',
                r'__import__\s*\(',
            ],
            "severity": "CRITICAL",
            "cwe":      "CWE-95",
            "fix":      "Remove eval()/exec():\n# Use json.loads() instead of eval() for data\n# Use a lookup dict instead of exec() for dynamic dispatch",
            "reason":   "eval()/exec() executes arbitrary code — if user input reaches these, full server compromise is possible.",
        },
        {
            "name":    "Command Injection",
            "regexes": [
                r'os\.system\s*\(',
                r'shell\s*=\s*True',
                r'subprocess\.call\s*\(',
            ],
            "severity": "HIGH",
            "cwe":      "CWE-78",
            "fix":      "Use shell=False:\nsubprocess.run(['command', arg], shell=False, capture_output=True)",
            "reason":   "Shell commands with user input allow arbitrary system command execution.",
        },
        {
            "name":    "SSL Verification Disabled",
            "regexes": [r'verify\s*=\s*False'],
            "severity": "HIGH",
            "cwe":      "CWE-295",
            "fix":      "Remove verify=False:\nrequests.get(url)  # verify=True is the default",
            "reason":   "Disabling SSL verification allows man-in-the-middle attacks.",
        },
    ]

    code_files = {
        k: v for k, v in files.items()
        if k.endswith((".py", ".js", ".ts", ".php")) and len(v) > 20
    }

    print(f"   Direct scan: checking {len(code_files)} code files")

    for filepath, content in code_files.items():
        lines = content.split("\n")
        lang  = _detect_language(filepath)

        for pat in PATTERNS:
            found_line    = None
            found_snippet = None

            for regex in pat["regexes"]:
                matches = list(re.finditer(regex, content, re.IGNORECASE | re.MULTILINE))
                if matches:
                    m        = matches[0]
                    line_num = content[:m.start()].count("\n") + 1
                    start    = max(0, line_num - 4)
                    end      = min(len(lines), line_num + 6)
                    found_line    = line_num
                    found_snippet = "\n".join(lines[start:end])
                    break

            if not found_snippet:
                continue

            vuln_info = {
                "type":     pat["name"],
                "severity": pat["severity"],
                "cwe":      pat["cwe"],
                "fix":      pat["fix"],
                "reason":   pat["reason"],
            }

            patch = _generate_patch_from_vuln(
                vuln_info, filepath, found_snippet, lang, found_line
            )
            if patch:
                patches.append(patch)
                break  # one patch per file per vuln type

    return patches


def _generate_patch_from_vuln(vuln, filepath, code_context, lang, line_num=None):
    """Ask Gemini to generate a fix."""
    if not code_context.strip():
        return None

    line_ref = line_num or vuln.get("line", "?")

    prompt = f"""You are a security engineer. Fix this {lang} security vulnerability.

VULNERABILITY: {vuln.get('type', 'Security Issue')}
SEVERITY: {vuln.get('severity', 'HIGH')}
FILE: {filepath}

VULNERABLE CODE:
```{lang.lower()}
{code_context}
```

PROBLEM: {vuln.get('reason', '')}
FIX APPROACH: {vuln.get('fix', '')}

Rules:
- Fix ONLY the security issue
- Keep all other logic IDENTICAL
- Add a 1-line comment explaining the security fix
- The fixed code must be complete and runnable

Respond in EXACTLY this format — no extra text before or after:

EXPLANATION: [one sentence: what you changed and why]

STEPS:
1. [first change]
2. [second change if any]

ORIGINAL_CODE:
```{lang.lower()}
{code_context}
```

FIXED_CODE:
```{lang.lower()}
[your complete corrected version here]
```
"""

    response    = get_gemini_response(prompt, temperature=0.1)
    fixed_code  = _extract_tagged_block(response, "FIXED_CODE")
    orig_code   = _extract_tagged_block(response, "ORIGINAL_CODE") or code_context
    explanation = _extract_field(response, "EXPLANATION")
    steps       = _extract_steps(response)

    if not fixed_code:
        return None

    return {
        "type":          "Security Fix",
        "vulnerability": vuln.get("type", "Security Issue"),
        "file":          filepath,
        "line":          str(line_ref),
        "severity":      vuln.get("severity", "HIGH"),
        "original_code": orig_code,
        "fixed_code":    fixed_code,
        "explanation":   explanation,
        "steps":         steps,
        "cwe":           vuln.get("cwe", ""),
        "priority":      1,
    }


def _find_file(filepath: str, files: dict) -> str:
    if not filepath: return ""
    fp = filepath.replace("\\", "/")
    if fp in files: return fp
    if filepath in files: return filepath
    for k in files:
        kn = k.replace("\\", "/")
        if kn.endswith(fp) or fp.endswith(kn): return k
    base = fp.split("/")[-1]
    for k in files:
        if k.replace("\\", "/").split("/")[-1] == base: return k
    fp_parts = set(fp.split("/"))
    best, score = "", 0
    for k in files:
        s = len(fp_parts & set(k.replace("\\", "/").split("/")))
        if s > score: best, score = k, s
    return best if score >= 1 else ""


def _extract_tagged_block(response: str, tag: str) -> str:
    m = re.search(rf"{tag}:\s*```[^\n]*\n(.*?)```", response, re.DOTALL | re.IGNORECASE)
    if m: return m.group(1).strip()
    if tag == "FIXED_CODE":
        blocks = re.findall(r"```[^\n]*\n(.*?)```", response, re.DOTALL)
        if blocks: return blocks[-1].strip()
    return ""


def _extract_field(response: str, field: str) -> str:
    for line in response.split("\n"):
        if line.strip().upper().startswith(field.upper() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def _extract_steps(response: str) -> list[str]:
    steps, active = [], False
    for line in response.split("\n"):
        if line.strip().upper().startswith("STEPS:"): active = True; continue
        if active:
            s = line.strip()
            if re.match(r"^\d+\.", s): steps.append(re.sub(r"^\d+\.\s*", "", s))
            elif s.startswith(("ORIGINAL_CODE", "FIXED_CODE")): break
    return steps


def _detect_language(filepath: str) -> str:
    for ext, lang in {".py":"Python",".js":"JavaScript",".ts":"TypeScript",
                      ".cs":"C#",".java":"Java",".go":"Go",".php":"PHP"}.items():
        if filepath.endswith(ext): return lang
    return "Python"