 # agents/dependency_agent.py
from __future__ import annotations
# ============================================
# RepoMind - Dependency Agent (IMPROVED)
#
# Now shows:
# - Package name, current version, latest version
# - CVE IDs with descriptions
# - Exact upgrade commands
# - Risk level per package
# - Works for Python, JS, C#, Java
# ============================================

import re
import json
import requests
from utils.llm import get_gemini_response

OSV_API_URL  = "https://api.osv.dev/v1/query"
PYPI_API_URL = "https://pypi.org/pypi/{package}/json"


def run_dependency_agent(files: dict[str, str], requirements_content: str = "") -> dict:
    """Analyze dependencies for vulnerabilities and outdated packages."""

    # ---- Step 1: Find requirements ----
    if not requirements_content:
        for filepath, content in files.items():
            if "requirements" in filepath.lower() and filepath.endswith(".txt"):
                requirements_content = content
                print(f"   Found requirements: {filepath}")
                break

    # ---- Step 2: Handle non-Python repos ----
    if not requirements_content:
        detected = _extract_manifest_dependencies(files)
        if detected["packages"]:
            total   = len(detected["packages"])
            summary = (
                f"Detected **{total}** dependencies from "
                f"{', '.join(detected['sources'])}. "
                f"Showing package inventory — deep CVE scan runs for Python repos."
            )
            return {
                "packages":           detected["packages"],
                "vulnerabilities":    [],
                "outdated":           [],
                "score":              65,
                "summary":            summary,
                "ai_recommendations": "",
                "sources":            detected["sources"],
                "total_packages":     total,
            }
        return {
            "packages": [], "vulnerabilities": [], "outdated": [],
            "score": 50, "total_packages": 0, "sources": [],
            "summary": "No dependency files found (requirements.txt / package.json / .csproj / pom.xml).",
        }

    # ---- Step 3: Parse requirements.txt ----
    packages = _parse_requirements(requirements_content)
    print(f"   Parsed {len(packages)} packages")

    # ---- Step 4: Check each package ----
    checked      = []
    vulnerabilities = []
    outdated     = []

    # Keep network-bound checks bounded for responsive UX.
    for pkg in packages[:12]:
        print(f"   Checking: {pkg['name']} {pkg['version']}")

        vulns          = _check_osv_vulnerabilities(pkg["name"], pkg["version"])
        latest_version = _get_latest_version(pkg["name"])
        is_vulnerable  = len(vulns) > 0
        is_outdated    = (
            latest_version and
            latest_version != pkg["version"] and
            pkg["version"] != "latest"
        )

        # Determine risk level
        if is_vulnerable:
            cve_severities = [v.get("severity","UNKNOWN") for v in vulns]
            if "CRITICAL" in cve_severities:  risk = "CRITICAL"; status = "🚨 Vulnerable"
            elif "HIGH" in cve_severities:    risk = "HIGH";     status = "🔴 Vulnerable"
            else:                              risk = "MEDIUM";   status = "🟡 Vulnerable"
        elif is_outdated:
            risk   = "LOW"
            status = "🟡 Outdated"
        else:
            risk   = "SAFE"
            status = "✅ OK"

        # Build upgrade command
        upgrade_cmd = ""
        if is_vulnerable or is_outdated:
            target = latest_version if latest_version else ""
            upgrade_cmd = f"pip install --upgrade {pkg['name']}" + (f"=={target}" if target else "")

        package_info = {
            "name":          pkg["name"],
            "version":       pkg["version"],
            "latest_version": latest_version or "Unknown",
            "vulnerabilities": vulns,
            "is_vulnerable": is_vulnerable,
            "is_outdated":   is_outdated,
            "risk":          risk,
            "status":        status,
            "upgrade_cmd":   upgrade_cmd,
            "cve_ids":       [v.get("id","") for v in vulns],
        }

        checked.append(package_info)
        if is_vulnerable: vulnerabilities.append(package_info)
        if is_outdated:   outdated.append(package_info)

    # ---- Step 5: AI recommendations ----
    ai_recommendations = ""
    if vulnerabilities:
        vuln_lines = "\n".join([
            f"- {v['name']} {v['version']} → CVEs: {', '.join(v['cve_ids'][:2])}"
            for v in vulnerabilities[:5]
        ])
        prompt = f"""You are a Python security expert reviewing vulnerable dependencies.

Vulnerable packages found:
{vuln_lines}

For EACH package provide:
1. What the vulnerability allows an attacker to do (1 sentence, simple language)
2. Exact upgrade command
3. Any breaking changes to watch for when upgrading

Format each package as:
PACKAGE: [name]
RISK: [what attacker can do]
UPGRADE: pip install --upgrade [name]==[safe_version]
BREAKING: [yes/no — what to watch for]
---
"""
        ai_recommendations = get_gemini_response(prompt, temperature=0.2)

    # ---- Step 6: Score ----
    score  = 100
    score -= len(vulnerabilities) * 20
    score -= len(outdated) * 3
    score  = max(0, score)

    # Count by risk
    critical = sum(1 for p in vulnerabilities if p["risk"] == "CRITICAL")
    high     = sum(1 for p in vulnerabilities if p["risk"] == "HIGH")
    medium   = sum(1 for p in vulnerabilities if p["risk"] == "MEDIUM")

    summary = (
        f"Scanned **{len(checked)}** packages. "
        f"Found **{len(vulnerabilities)}** vulnerable "
        f"(🚨 {critical} critical, 🔴 {high} high, 🟡 {medium} medium) "
        f"and **{len(outdated)}** outdated. "
        f"Health score: **{score}/100**."
    )

    return {
        "packages":           checked,
        "vulnerabilities":    vulnerabilities,
        "outdated":           outdated,
        "ai_recommendations": ai_recommendations,
        "score":              score,
        "summary":            summary,
        "total_packages":     len(checked),
        "sources":            ["requirements.txt"],
        "risk_counts":        {"CRITICAL": critical, "HIGH": high, "MEDIUM": medium},
    }


def _parse_requirements(content: str) -> list[dict]:
    packages = []
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith(("#", "git+", "http://", "https://", "-r", "-e")):
            continue
        match = re.match(r"([a-zA-Z0-9_\-\.]+)\s*([=<>!~]+\s*[\d\.]+)?", line)
        if match:
            name         = match.group(1).lower()
            version_spec = match.group(2) or ""
            version      = re.sub(r"[=<>!~\s]", "", version_spec) if version_spec else "latest"
            packages.append({"name": name, "version": version})
    return packages


def _check_osv_vulnerabilities(package_name: str, version: str) -> list[dict]:
    try:
        payload: dict = {"package": {"name": package_name, "ecosystem": "PyPI"}}
        if version and version != "latest":
            payload["version"] = version

        response = requests.post(OSV_API_URL, json=payload, timeout=10)
        if response.status_code == 200:
            vulns = response.json().get("vulns", [])
            result = []
            for v in vulns[:3]:
                # Extract affected versions
                affected_versions = []
                for affected in v.get("affected", [])[:1]:
                    for rng in affected.get("ranges", [])[:1]:
                        for evt in rng.get("events", []):
                            if "introduced" in evt:
                                affected_versions.append(f"≥{evt['introduced']}")
                            if "fixed" in evt:
                                affected_versions.append(f"fixed in {evt['fixed']}")

                result.append({
                    "id":               v.get("id", "Unknown"),
                    "summary":          v.get("summary", "No description")[:120],
                    "severity":         _get_severity(v),
                    "affected_versions": ", ".join(affected_versions[:2]),
                    "published":        v.get("published", "")[:10],
                    "link":             f"https://osv.dev/vulnerability/{v.get('id','')}",
                })
            return result
    except Exception:
        pass
    return []


def _get_latest_version(package_name: str) -> str:
    try:
        url      = PYPI_API_URL.format(package=package_name)
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            return response.json()["info"]["version"]
    except Exception:
        pass
    return ""


def _get_severity(vuln: dict) -> str:
    for val in vuln.get("database_specific", {}).values():
        if isinstance(val, str) and val.upper() in ("CRITICAL","HIGH","MEDIUM","LOW"):
            return val.upper()
    sev = vuln.get("severity", [])
    if sev:
        score = sev[0].get("score", "")
        if score:
            try:
                s = float(score)
                if s >= 9.0: return "CRITICAL"
                if s >= 7.0: return "HIGH"
                if s >= 4.0: return "MEDIUM"
                return "LOW"
            except Exception:
                pass
        return sev[0].get("type", "UNKNOWN")
    return "UNKNOWN"


def _extract_manifest_dependencies(files: dict[str, str]) -> dict:
    packages: list[dict] = []
    sources:  list[str]  = []

    for path, content in files.items():
        p = path.lower()

        if p.endswith("package.json"):
            try:
                data     = json.loads(content)
                all_deps = {**data.get("dependencies",{}), **data.get("devDependencies",{})}
                for name, version in all_deps.items():
                    packages.append({
                        "name": name, "version": str(version),
                        "latest_version": "Unknown", "vulnerabilities": [],
                        "is_vulnerable": False, "is_outdated": False,
                        "risk": "UNKNOWN", "status": "ℹ️ Detected",
                        "upgrade_cmd": f"npm install {name}@latest",
                        "cve_ids": [],
                    })
                if all_deps: sources.append(path)
            except Exception:
                pass

        elif p.endswith(".csproj"):
            refs = re.findall(
                r'PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"', content
            )
            for name, version in refs:
                packages.append({
                    "name": name, "version": version,
                    "latest_version": "Unknown", "vulnerabilities": [],
                    "is_vulnerable": False, "is_outdated": False,
                    "risk": "UNKNOWN", "status": "ℹ️ Detected",
                    "upgrade_cmd": f"dotnet add package {name}",
                    "cve_ids": [],
                })
            if refs: sources.append(path)

        elif p.endswith("pom.xml"):
            deps = re.findall(
                r"<dependency>\s*<groupId>([^<]+)</groupId>\s*"
                r"<artifactId>([^<]+)</artifactId>\s*<version>([^<]+)</version>",
                content, flags=re.DOTALL,
            )
            for group, artifact, version in deps:
                packages.append({
                    "name": f"{group}:{artifact}", "version": version,
                    "latest_version": "Unknown", "vulnerabilities": [],
                    "is_vulnerable": False, "is_outdated": False,
                    "risk": "UNKNOWN", "status": "ℹ️ Detected",
                    "upgrade_cmd": f"<!-- Update version in pom.xml to latest -->",
                    "cve_ids": [],
                })
            if deps: sources.append(path)

    seen   = set()
    unique = []
    for pkg in packages:
        key = (pkg["name"], pkg["version"])
        if key not in seen:
            seen.add(key)
            unique.append(pkg)

    return {"packages": unique[:150], "sources": sources}