 # agents/security_agent.py
# ============================================
# RepoMind - Security Agent (IMPROVED)
#
# Scans ALL files, gives detailed output:
# - File name + line number
# - Risk type + reason
# - Code snippet showing the problem
# - Exact fix with code example
# - AI deep analysis
# ============================================

from __future__ import annotations
import re
from utils.llm import get_gemini_response


# ============================================
# SECURITY PATTERNS — works for ALL languages
# Python, JavaScript, C#, Java, Go, PHP, etc.
# ============================================
SECURITY_PATTERNS = {

    "SQL Injection": {
        "patterns": [
            r'execute\s*\(\s*["\'].*?\+',
            r'execute\s*\(\s*f["\']',
            r'execute\s*\(\s*".*?%s.*?".*?%',
            r'query\s*=\s*["\'].*?\+.*?["\']',
            r'ExecuteQuery\s*\(\s*["\'].*?\+',
            r'SqlCommand\s*\(\s*["\'].*?\+',
            r'Statement\.execute\s*\(\s*["\'].*?\+',
        ],
        "severity": "CRITICAL",
        "reason": "User input is directly concatenated into a SQL query string. An attacker can inject malicious SQL to access, modify, or delete any data in your database.",
        "fix": "Use parameterized queries:\n# Python:\ncursor.execute('SELECT * FROM users WHERE id=%s', (user_id,))\n# C#:\ncmd.Parameters.AddWithValue(\"@id\", userId);\n# Java:\nstmt = conn.prepareStatement(\"SELECT * FROM users WHERE id=?\");\nstmt.setInt(1, userId);",
        "cwe": "CWE-89",
    },

    "Hardcoded Password": {
        "patterns": [
            r'password\s*=\s*["\'][^"\']{3,}["\']',
            r'password\s*:\s*["\'][^"\']{3,}["\']',
            r'passwd\s*=\s*["\'][^"\']{3,}["\']',
            r'pwd\s*=\s*["\'][^"\']{4,}["\']',
            r'secret\s*=\s*["\'][^"\']{3,}["\']',
            r'api_key\s*=\s*["\'][^"\']{3,}["\']',
            r'apikey\s*=\s*["\'][^"\']{3,}["\']',
            r'SECRET_KEY\s*=\s*["\'][^"\']{3,}["\']',
            r'token\s*=\s*["\'][a-zA-Z0-9_\-]{10,}["\']',
        ],
        "severity": "CRITICAL",
        "reason": "A hardcoded credential is stored directly in source code. If this repo is pushed to GitHub or shared, attackers can extract and use the credential immediately.",
        "fix": "Move credentials to environment variables:\n# Python:\npassword = os.getenv('DB_PASSWORD')\n# .env file:\nDB_PASSWORD=your_actual_password\n# Never commit .env to git!",
        "cwe": "CWE-798",
    },

    "Hardcoded Connection String": {
        "patterns": [
            r'connectionstring\s*=\s*["\'][^"\']+["\']',
            r'jdbc:[a-z]+://[^\s"\']+',
            r'postgres://[^\s"\']+',
            r'mongodb\+srv://[^\s"\']+',
            r'mysql://[^\s"\']+',
            r'Server=.*;Database=.*;',
        ],
        "severity": "HIGH",
        "reason": "A database connection string with credentials appears hardcoded in source code, exposing database host, port, username and password.",
        "fix": "Store connection strings in environment variables or a secrets manager:\nconnection = os.getenv('DATABASE_URL')",
        "cwe": "CWE-312",
    },

    "Debug Mode Enabled": {
        "patterns": [
            r'DEBUG\s*=\s*True',
            r'debug\s*=\s*True',
            r'app\.run\(.*debug\s*=\s*True',
            r'\.EnableDetailedErrors\(\)',
            r'app\.UseDeveloperExceptionPage\(\)',
        ],
        "severity": "HIGH",
        "reason": "Debug mode is enabled. In production this exposes full stack traces, internal file paths, environment variables, and sometimes even source code to any visitor.",
        "fix": "Disable debug in production:\nDEBUG = os.getenv('DEBUG', 'False') == 'True'\n# Or use environment-based config",
        "cwe": "CWE-94",
    },

    "Code Injection (eval/exec)": {
        "patterns": [
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'compile\s*\(.*exec',
        ],
        "severity": "CRITICAL",
        "reason": "eval() or exec() executes arbitrary code. If any user-controlled input reaches these calls, attackers can run any code on your server — full system compromise.",
        "fix": "Remove eval/exec completely. Use safe alternatives:\n# Instead of eval for math: use ast.literal_eval()\n# Instead of eval for JSON: use json.loads()\n# Instead of dynamic code: use a lookup dict",
        "cwe": "CWE-95",
    },

    "Command Injection": {
        "patterns": [
            r'os\.system\s*\(',
            r'subprocess\.call\s*\(.*shell\s*=\s*True',
            r'subprocess\.run\s*\(.*shell\s*=\s*True',
            r'subprocess\.Popen\s*\(.*shell\s*=\s*True',
            r'Runtime\.getRuntime\(\)\.exec\(',
            r'Process\.Start\(',
        ],
        "severity": "HIGH",
        "reason": "Shell commands are being executed. If user input is included in the command string, attackers can inject system commands (e.g., '; rm -rf /' or '&& cat /etc/passwd').",
        "fix": "Use shell=False and pass args as a list:\n# SAFE:\nsubprocess.run(['ls', user_dir], shell=False)\n# UNSAFE:\nsubprocess.run(f'ls {user_dir}', shell=True)",
        "cwe": "CWE-78",
    },

    "SSL Verification Disabled": {
        "patterns": [
            r'verify\s*=\s*False',
            r'ssl_verify\s*=\s*False',
            r'checkCertificate\s*=\s*false',
            r'ServerCertificateCustomValidationCallback',
            r'InsecureRequestWarning',
            r'urllib3\.disable_warnings',
        ],
        "severity": "HIGH",
        "reason": "SSL/TLS certificate verification is disabled. This makes HTTPS connections insecure — a man-in-the-middle attacker can intercept and read all traffic between your app and the server.",
        "fix": "Never disable SSL verification in production:\n# Remove verify=False\nrequests.get(url)  # uses verify=True by default\n# If you have cert issues, add the cert file:\nrequests.get(url, verify='/path/to/cert.pem')",
        "cwe": "CWE-295",
    },

    "Potential XSS": {
        "patterns": [
            r'innerHTML\s*=',
            r'outerHTML\s*=',
            r'document\.write\s*\(',
            r'\.html\s*\(.*req\.',
            r'dangerouslySetInnerHTML',
            r'v-html\s*=',
        ],
        "severity": "HIGH",
        "reason": "User-controlled content is being rendered as raw HTML. Attackers can inject <script> tags to steal cookies, redirect users, or perform actions on their behalf.",
        "fix": "Always escape output:\n# Use textContent instead of innerHTML:\nelement.textContent = userInput;  // SAFE\nelement.innerHTML = userInput;    // UNSAFE\n# In templates, use auto-escaping",
        "cwe": "CWE-79",
    },

    "Weak Randomness": {
        "patterns": [
            r'\bimport random\b',
            r'random\.random\(',
            r'random\.randint\(',
            r'Math\.random\(',
            r'new Random\(',
        ],
        "severity": "MEDIUM",
        "reason": "The standard random module/function is NOT cryptographically secure. Using it for tokens, session IDs, passwords, or OTPs makes them predictable and guessable by attackers.",
        "fix": "Use cryptographically secure random:\n# Python:\nimport secrets\ntoken = secrets.token_hex(32)\notp = secrets.randbelow(1000000)\n# JavaScript:\ncrypto.getRandomValues(new Uint8Array(32))",
        "cwe": "CWE-338",
    },

    "Insecure Deserialization": {
        "patterns": [
            r'\bpickle\.loads\s*\(',
            r'\bpickle\.load\s*\(',
            r'yaml\.load\s*\([^,)]*\)',
            r'Marshal\.load\s*\(',
            r'ObjectInputStream',
        ],
        "severity": "CRITICAL",
        "reason": "Deserializing untrusted data using pickle/yaml.load/Marshal can allow attackers to execute arbitrary code by crafting malicious serialized objects.",
        "fix": "# Python pickle — avoid with untrusted data entirely\n# YAML: use safe_load instead:\nyaml.safe_load(data)  # SAFE\nyaml.load(data)        # UNSAFE — allows code execution",
        "cwe": "CWE-502",
    },

    "Exposed Private Key / Token": {
        "patterns": [
            r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
            r'sk_live_[a-zA-Z0-9]{20,}',
            r'sk_test_[a-zA-Z0-9]{20,}',
            r'AKIA[0-9A-Z]{16}',
            r'ghp_[a-zA-Z0-9]{36}',
            r'AIza[0-9A-Za-z_\-]{35}',
        ],
        "severity": "CRITICAL",
        "reason": "A real private key, API token, or access key appears to be hardcoded in the source code. This is an immediate security incident — anyone with access to this code can impersonate your service.",
        "fix": "1. IMMEDIATELY revoke/rotate this key\n2. Remove it from code\n3. Add it to .gitignore/.env\n4. Scan git history: git log -p | grep -i 'sk_live\\|AKIA\\|ghp_'",
        "cwe": "CWE-321",
    },
}


def run_security_agent(files: dict[str, str]) -> dict:
    """
    Scan ALL repository files for security vulnerabilities.
    Returns detailed findings with file, line, reason, and fix.
    """

    vulnerabilities = []
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    files_with_issues = set()

    # ---- Step 1: Pattern scan ALL files ----
    for filepath, content in files.items():
        lines = content.split("\n")

        for vuln_type, vuln_info in SECURITY_PATTERNS.items():
            already_reported = False  # report once per vuln type per file

            for pattern in vuln_info["patterns"]:
                if already_reported:
                    break

                matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))

                for match in matches:
                    line_num  = content[:match.start()].count("\n") + 1
                    line_text = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                    # Skip if it looks like a comment or test file
                    if line_text.startswith(("#", "//", "*", "<!--")):
                        continue

                    sev = vuln_info["severity"]

                    vulnerabilities.append({
                        "type":         vuln_type,
                        "file":         filepath,
                        "line":         str(line_num),
                        "severity":     sev,
                        "reason":       vuln_info["reason"],
                        "fix":          vuln_info["fix"],
                        "cwe":          vuln_info.get("cwe", ""),
                        "code_snippet": line_text[:120],
                        "source":       "Pattern Scanner",
                    })

                    severity_counts[sev] = severity_counts.get(sev, 0) + 1
                    files_with_issues.add(filepath)
                    already_reported = True
                    break

    print(f"   Pattern scan complete: {len(vulnerabilities)} findings in {len(files_with_issues)} files")

    # ---- Step 2: AI deep analysis on riskiest files ----
    risky_files  = list(files_with_issues)[:3]
    ai_analysis  = ""
    ai_findings  = []

    if risky_files:
        risky_content = ""
        for fp in risky_files:
            risky_content += f"\n\n=== FILE: {fp} ===\n{files.get(fp,'')[:1500]}"

        found_types = list(set(v["type"] for v in vulnerabilities[:8]))

        prompt = f"""You are a senior cybersecurity engineer (OWASP Top 10 expert).

I already found these vulnerability types via pattern matching:
{found_types}

Do a DEEPER security review of these files. Find things the pattern scanner MISSED:
- Logic flaws in authentication / authorization
- Missing input validation
- Insecure data exposure
- Race conditions
- Business logic vulnerabilities
- Missing rate limiting

FILES TO REVIEW:
{risky_content}

For EACH additional vulnerability you find, use EXACTLY this format:

---VULN---
TYPE: [vulnerability name]
FILE: [exact filename]
LINE: [line number]
SEVERITY: [CRITICAL / HIGH / MEDIUM / LOW]
REASON: [1-2 sentences: why this is dangerous and what an attacker can do]
CODE: [the problematic line or snippet]
FIX: [concrete fix with code example]
---END---

Only report NEW issues not already covered by pattern matching.
Maximum 5 additional findings.
"""
        ai_response = get_gemini_response(prompt, temperature=0.1)
        ai_findings = _parse_ai_findings(ai_response, files)
        ai_analysis = ai_response

        # Add AI findings to vulnerabilities
        for f in ai_findings:
            vulnerabilities.append(f)
            sev = f.get("severity", "MEDIUM")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # ---- Step 3: Calculate score ----
    score  = 100
    score -= severity_counts.get("CRITICAL", 0) * 25
    score -= severity_counts.get("HIGH",     0) * 15
    score -= severity_counts.get("MEDIUM",   0) * 7
    score -= severity_counts.get("LOW",      0) * 2
    score  = max(0, score)

    # ---- Step 4: Risk level ----
    if severity_counts.get("CRITICAL", 0) > 0:
        risk_level = "CRITICAL"
    elif severity_counts.get("HIGH", 0) >= 3:
        risk_level = "HIGH"
    elif severity_counts.get("HIGH", 0) > 0 or severity_counts.get("MEDIUM", 0) >= 3:
        risk_level = "MEDIUM"
    elif len(vulnerabilities) > 0:
        risk_level = "LOW"
    else:
        risk_level = "SAFE"

    # ---- Step 5: Sort by severity ----
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    vulnerabilities.sort(key=lambda x: sev_order.get(x.get("severity","LOW"), 3))

    print(f"   Security scan done. Risk level: {risk_level}, Score: {score}/100")

    return {
        "vulnerabilities":  vulnerabilities,
        "severity_counts":  severity_counts,
        "risk_level":       risk_level,
        "score":            score,
        "ai_analysis":      ai_analysis,
        "ai_findings":      ai_findings,
        "total_found":      len(vulnerabilities),
        "files_scanned":    len(files),
        "files_affected":   len(files_with_issues),
    }


def _parse_ai_findings(response: str, files: dict) -> list[dict]:
    """Parse ---VULN--- blocks from AI response."""
    findings = []
    blocks   = re.split(r"---VULN---", response)

    for block in blocks[1:]:
        if "---END---" not in block:
            continue
        block = block.split("---END---")[0].strip()

        finding = {"source": "Gemini AI Deep Scan", "severity": "MEDIUM"}

        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("TYPE:"):     finding["type"]         = line.replace("TYPE:","").strip()
            elif line.startswith("FILE:"):   finding["file"]         = line.replace("FILE:","").strip()
            elif line.startswith("LINE:"):   finding["line"]         = line.replace("LINE:","").strip()
            elif line.startswith("SEVERITY:"): finding["severity"]   = line.replace("SEVERITY:","").strip().upper()
            elif line.startswith("REASON:"): finding["reason"]       = line.replace("REASON:","").strip()
            elif line.startswith("CODE:"):   finding["code_snippet"] = line.replace("CODE:","").strip()
            elif line.startswith("FIX:"):    finding["fix"]          = line.replace("FIX:","").strip()

        # Map to standard fields
        finding["description"] = finding.get("reason", "")
        finding["cwe"]         = ""

        if "type" in finding:
            findings.append(finding)

    return findings