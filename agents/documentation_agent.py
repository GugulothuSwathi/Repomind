 # agents/documentation_agent.py
from __future__ import annotations
# ============================================
# RepoMind - Documentation Agent (FIXED)
#
# Fix: README detection now works for:
# - README.md / readme.md / Readme.md
# - README.rst / README.txt
# - README in any subfolder
# - Files with capital letters
# ============================================

import ast
import re
from utils.llm import get_gemini_response


def run_documentation_agent(files: dict[str, str]) -> dict:
    """Analyze and improve documentation across the repository."""

    missing_docs       = []
    generated_docs     = []
    total_documentable = 0
    python_files_scanned = 0
    python_parse_failures = 0

    # ---- Step 1: Find ALL undocumented functions/classes ----
    for filepath, content in files.items():
        if not filepath.endswith(".py"):
            continue
        python_files_scanned += 1
        try:
            tree = ast.parse(content)
        except SyntaxError:
            python_parse_failures += 1
            continue

        lines = content.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                total_documentable += 1

                has_docstring = (
                    node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Constant) and
                    isinstance(node.body[0].value.value, str)
                )

                if not has_docstring:
                    node_type    = "class" if isinstance(node, ast.ClassDef) else "function"
                    start        = node.lineno - 1
                    end          = min(start + 15, len(lines))
                    code_snippet = "\n".join(lines[start:end])
                    signature    = lines[start].strip() if start < len(lines) else ""

                    missing_docs.append({
                        "file":      filepath,
                        "name":      node.name,
                        "type":      node_type,
                        "line":      node.lineno,
                        "code":      code_snippet,
                        "signature": signature,
                    })

    # ---- Step 2: Generate docstrings ----
    for item in missing_docs[:3]:
        prompt = f"""Write a professional Python docstring for this {item['type']}.

Code:
```python
{item['code']}
```

Rules:
- Use Google-style docstring format
- First line: one sentence describing WHAT it does
- Include Args: section if there are parameters
- Include Returns: section if it returns something
- Be concise (3-6 lines max)
- Output ONLY the docstring starting with triple quotes

Example:
\"\"\"Authenticate a user and return a session token.

Args:
    username (str): The user's login name.
    password (str): The user's password.

Returns:
    str: A session token if authentication succeeds.
\"\"\"
"""
        generated_docstring = get_gemini_response(prompt, temperature=0.2)

        docstring = generated_docstring.strip()
        if "Gemini API Error" in docstring or "resource_exhausted" in docstring.lower():
            continue

        if not docstring.startswith('"""') and not docstring.startswith("'''"):
            match = re.search(r'""".*?"""', docstring, re.DOTALL)
            if match:
                docstring = match.group(0)

        generated_docs.append({
            "file":      item["file"],
            "name":      item["name"],
            "type":      item["type"],
            "line":      item["line"],
            "signature": item["signature"],
            "code":      item["code"],
            "docstring": docstring,
        })

    # ---- Step 3: Module summaries ----
    module_summaries = _generate_module_summaries(files)

    # ---- Step 4: README analysis (FIXED) ----
    readme_analysis = _analyze_readme(files)

    # ---- Step 5: Score ----
    documented_items = max(0, total_documentable - len(missing_docs))
    if total_documentable > 0:
        doc_coverage = int((documented_items / total_documentable) * 100)
    else:
        doc_coverage = 0

    readme_score = readme_analysis.get("score", 50)
    final_score  = int(doc_coverage * 0.6 + readme_score * 0.4)

    if total_documentable == 0:
        summary = (
            "No Python functions/classes were detected in scanned files. "
            f"README quality: **{readme_analysis.get('quality', 'Unknown')}**."
        )
    else:
        summary = (
            f"Found **{len(missing_docs)}** undocumented functions/classes out of "
            f"**{total_documentable}** total. "
            f"Documentation coverage: **{doc_coverage}%**. "
            f"README quality: **{readme_analysis.get('quality', 'Unknown')}**."
        )

    return {
        "missing_docs":     missing_docs,
        "generated_docs":   generated_docs,
        "module_summaries": module_summaries,
        "readme_analysis":  readme_analysis,
        "score":            final_score,
        "summary":          summary,
        "doc_coverage":     doc_coverage,
        "documented_items": documented_items,
        "total_items":      total_documentable,
        "python_files_scanned": python_files_scanned,
        "python_parse_failures": python_parse_failures,
    }


def _generate_module_summaries(files: dict[str, str]) -> list[dict]:
    """Generate one-line summary for each Python module."""
    summaries = []
    py_files  = {k: v for k, v in files.items() if k.endswith(".py") and len(v) > 50}
    selected  = dict(list(py_files.items())[:6])

    for filepath, content in selected.items():
        existing_summary = ""
        try:
            tree = ast.parse(content)
            if (tree.body and
                isinstance(tree.body[0], ast.Expr) and
                isinstance(tree.body[0].value, ast.Constant)):
                existing_summary = tree.body[0].value.value.strip().split("\n")[0]
        except Exception:
            pass

        func_names  = re.findall(r"^def (\w+)",   content, re.MULTILINE)[:8]
        class_names = re.findall(r"^class (\w+)", content, re.MULTILINE)[:4]

        if existing_summary:
            summary      = existing_summary
            ai_generated = False
        else:
            prompt = f"""In ONE sentence (max 15 words), describe what this Python module does.

File: {filepath}
Functions: {', '.join(func_names[:6])}
Classes: {', '.join(class_names[:3])}

First 20 lines:
{chr(10).join(content.split(chr(10))[:20])}

Output ONLY the one-sentence summary, nothing else.
"""
            summary      = get_gemini_response(prompt, temperature=0.1).strip()
            ai_generated = True

        summaries.append({
            "file":         filepath,
            "summary":      summary[:150],
            "functions":    func_names,
            "classes":      class_names,
            "ai_generated": ai_generated,
            "line_count":   len(content.split("\n")),
        })

    return summaries


# ============================================================
# REPLACE YOUR ENTIRE _analyze_readme FUNCTION WITH THIS
# Find it in documentation_agent.py and replace it
# ============================================================

def _analyze_readme(files: dict[str, str]) -> dict:
    """
    FIXED README detection - works for any case, any location.
    """
    readme_content = ""
    readme_file    = ""

    # Single simple loop - checks every file
    # Extracts just the filename and does case-insensitive startswith check
    root_match   = None  # README at root level (preferred)
    subdir_match = None  # README in subfolder (fallback)

    for filepath, content in files.items():
        # Normalize slashes (Windows uses backslash sometimes)
        clean_path = filepath.replace("\\", "/")

        # Get just the filename — split by / and take last part
        basename = clean_path.split("/")[-1]

        # Case-insensitive check: does the filename START with "readme"?
        if basename.lower().startswith("readme"):

            # Is it at root level? (no slash in path = root level)
            is_root = "/" not in clean_path

            if is_root and root_match is None:
                root_match = (filepath, content)
            elif not is_root and subdir_match is None:
                subdir_match = (filepath, content)

    # Pick the best match
    if root_match:
        readme_file, readme_content = root_match
    elif subdir_match:
        readme_file, readme_content = subdir_match
    else:
        return {
            "found":       False,
            "quality":     "Missing",
            "score":       0,
            "missing": [
                "Project title and description",
                "Installation instructions",
                "Usage examples",
                "API documentation",
                "Contributing guidelines",
                "License information",
            ],
            "present":     [],
            "suggestion":  "Create a README.md — it is the first thing any developer sees.",
            "improvement": _generate_readme_template(),
        }

    # ---- Analyze README content ----
    text   = readme_content.lower()
    checks = {
        "Project description":     [r"^#\s", r"overview", r"about", r"what is", r"introduction"],
        "Installation":            [r"install", r"setup", r"getting started",
                                    r"pip install", r"nuget", r"npm install", r"dotnet add"],
        "Usage examples":          [r"usage", r"example", r"quick start",
                                    r"how to use", r"sample", r"```"],
        "API / Features":          [r"api", r"feature", r"endpoint",
                                    r"capabilities", r"method"],
        "Contributing guidelines": [r"contribut", r"development",
                                    r"pull request", r"fork", r"issue"],
        "License":                 [r"license", r"mit", r"apache", r"gpl", r"bsd"],
        "Screenshots / Demo":      [r"screenshot", r"demo", r"gif",
                                    r"video", r"preview", r"badge", r"!\["],
    }

    present = []
    missing = []
    for section, patterns in checks.items():
        if any(re.search(p, text, re.MULTILINE) for p in patterns):
            present.append(section)
        else:
            missing.append(section)

    score = int((len(present) / len(checks)) * 100)
    if score >= 85:   quality = "Excellent"
    elif score >= 70: quality = "Good"
    elif score >= 45: quality = "Fair"
    else:             quality = "Poor"

    improvement = ""
    improvement_error = ""
    if missing:
        prompt = f"""A README.md is missing these sections: {', '.join(missing[:3])}.

Write ONLY the missing sections in markdown format.
Keep each section to 3-5 lines max.
Start directly with markdown, no preamble.
"""
        improvement = get_gemini_response(prompt, temperature=0.3)
        if "Gemini API Error" in improvement or "resource_exhausted" in improvement.lower():
            improvement_error = improvement.strip()
            improvement = ""

    return {
        "found":       True,
        "file":        readme_file,
        "quality":     quality,
        "score":       score,
        "missing":     missing,
        "present":     present,
        "suggestion":  f"Add: {', '.join(missing[:3])}" if missing else "README looks great!",
        "improvement": improvement,
        "improvement_error": improvement_error,
        "length":      len(readme_content),
    }
def _generate_readme_template() -> str:
    return """## Suggested README.md Template
````markdown
# Project Name
Brief description of what this project does.

## Installation
```bash
pip install -r requirements.txt
# or for C#:
dotnet add package YourPackage
```

## Usage
```python
from mymodule import MyClass
obj = MyClass()
result = obj.do_something()
```

## Features
- Feature 1: description
- Feature 2: description

## Contributing
Pull requests welcome. Open an issue first to discuss changes.

## License
MIT
````
"""