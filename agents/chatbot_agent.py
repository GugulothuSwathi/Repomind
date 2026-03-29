 # agents/chatbot_agent.py
# ============================================

import time
import re
from collections import defaultdict

# Shown when the user asks about RepoMind (the app) and the LLM is unavailable.
REPOMIND_STATIC_INTRO = """**RepoMind** is an AI assistant for understanding and improving a codebase you analyze in this app.

It runs agents on your repository—code review, security scanning, documentation, dependencies, architecture, risk heatmaps, git history (Time Machine), and suggested fixes—then lets you explore results in tabs and chat here.

If you want details about **your analyzed project** (files, stack, issues), ask about *this repository*, *this codebase*, or *this project*."""

META_CHAT_TEMPERATURE = 0.72
REPO_CHAT_TEMPERATURE = 0.55
MIN_CHAT_API_INTERVAL_S = 1.2


class RepoChatbot:
    def __init__(self):
        self.is_indexed    = False
        self.files         = {}
        self.results       = {}
        self.time_machine  = None
        self.repo_summary  = ""
        self.file_index    = {}   # keyword → [filepaths]
        self._last_api_call = 0   # for rate limiting

    # ─────────────────────────────────────────────────────────────
    # INDEXING
    # ─────────────────────────────────────────────────────────────

    def index_repository(self, files: dict, results: dict,
                         time_machine_result=None):
        self.files        = files
        self.results      = results
        self.time_machine = time_machine_result

        # Build keyword index from filenames + content
        self._build_file_index()
        self.repo_summary = self._create_repo_summary()
        self.is_indexed   = True
        print(f"✅ Chatbot indexed {len(files)} files")

    def _build_file_index(self):
        """Index files by keywords for fast lookup."""
        index = defaultdict(set)

        for filepath, content in self.files.items():
            # Index by filename parts
            parts = re.split(r"[/._\-]", filepath.lower())
            for part in parts:
                if len(part) > 2:
                    index[part].add(filepath)

            # Index by content keywords (imports, class names, function names)
            for line in content.split("\n")[:50]:  # first 50 lines only
                line = line.strip().lower()
                if line.startswith(("import ", "from ", "class ", "def ")):
                    words = re.findall(r"[a-z_]{3,}", line)
                    for word in words:
                        index[word].add(filepath)

        self.file_index = {k: list(v) for k, v in index.items()}

    def _create_repo_summary(self) -> str:
        """Create a concise repo summary from all agent results."""
        sec  = self.results.get("security", {})
        cr   = self.results.get("code_review", {})
        dep  = self.results.get("dependency", {})
        doc  = self.results.get("documentation", {})
        arch = self.results.get("architecture", {})
        bf   = self.results.get("bug_fix", {})

        # Count file types
        ext_counts = defaultdict(int)
        for f in self.files:
            ext = f.rsplit(".", 1)[-1] if "." in f else "other"
            ext_counts[ext] += 1
        top_exts = sorted(ext_counts.items(), key=lambda x: -x[1])[:3]
        ext_str  = ", ".join(f"{e} ({c})" for e, c in top_exts)

        # Tech stack
        tech = arch.get("tech_stack", [])

        # Components
        comps = [c.get("name","") for c in arch.get("components", [])[:6]]

        # Issues
        issues   = cr.get("issues", [])
        high_iss = [i for i in issues if i.get("severity","").upper() == "HIGH"]

        # Vulnerabilities
        vulns = sec.get("vulnerabilities", [])

        # Commits
        commits = []
        if self.time_machine:
            commits = self.time_machine.get("commits", [])

        summary = f"""REPOSITORY SUMMARY:
Total files: {len(self.files)}
File types: {ext_str}
Technology Stack: {', '.join(tech) if tech else 'Unknown'}
Key Components: {', '.join(comps) if comps else 'Unknown'}

CODE QUALITY:
- Code review score: {cr.get('score', 'N/A')}/100
- Total issues: {len(issues)} ({len(high_iss)} high severity)
- Security risk: {sec.get('risk_level', 'UNKNOWN')}
- Total vulnerabilities: {sec.get('total_found', 0)}
- Documentation coverage: {doc.get('doc_coverage', 0)}%
- Dependency health score: {dep.get('score', 'N/A')}/100
- Auto-patches generated: {bf.get('stats', {}).get('total_patches', 0)}

TOP SECURITY ISSUES:
{self._format_top_vulns(vulns[:3])}

TOP CODE ISSUES:
{self._format_top_issues(high_iss[:3])}

GIT HISTORY:
- Commits tracked: {len(commits)}
{self._format_commits(commits[:3])}
"""
        return summary

    def _format_top_vulns(self, vulns):
        if not vulns:
            return "- None found"
        lines = []
        for v in vulns:
            lines.append(
                f"- {v.get('severity','?')} | {v.get('type','?')} "
                f"in {v.get('file','?')} line {v.get('line','?')}"
            )
        return "\n".join(lines)

    def _format_top_issues(self, issues):
        if not issues:
            return "- None found"
        lines = []
        for i in issues:
            lines.append(
                f"- {i.get('severity','?')} | {i.get('issue','?')} "
                f"in {i.get('file','?')} line {i.get('line','?')}"
            )
        return "\n".join(lines)

    def _format_commits(self, commits):
        if not commits:
            return "- No commit data"
        lines = []
        for c in commits:
            lines.append(
                f"- {c.get('sha','?')[:7]} | {c.get('message','?')[:60]} "
                f"by {c.get('author','?')}"
            )
        return "\n".join(lines)

    def _is_repomind_meta_question(self, question: str) -> bool:
        """True if the user is asking about RepoMind the application, not the analyzed repo."""
        q = question.lower()
        if "repomind" in q:
            return True
        repo_scope = any(
            w in q
            for w in (
                "repository",
                "this repo",
                "the repo",
                "codebase",
                "these files",
                "my code",
                "cloned repo",
                "uploaded",
            )
        )
        if repo_scope:
            return False
        meta_markers = (
            "what is this app",
            "what's this app",
            "what is this tool",
            "what's this tool",
            "this application",
            "this tool ",
            "this tool?",
            "this tool,",
            "about this tool",
            "about this app",
            "what can you do",
            "what do you do",
            "who are you",
            "what are you",
            "how do i use this",
            "how does this interface",
            "what does this program",
            "what does this software",
        )
        return any(m in q for m in meta_markers)

    # ─────────────────────────────────────────────────────────────
    # ASKING
    # ─────────────────────────────────────────────

    def ask(self, question: str) -> dict:
        """
        Answer a question about the repository.
        Returns dict with 'answer', 'relevant_files', 'relevant_commits'
        """
        if not self.is_indexed:
            return {
                "answer": "Please run the analysis first before asking questions.",
                "relevant_files": [],
                "relevant_commits": [],
            }

        question_lower = question.lower().strip()

        # Find relevant files based on question keywords
        relevant_files   = self._find_relevant_files(question_lower)
        relevant_commits = self._find_relevant_commits(question_lower)

        # Questions about RepoMind (the product), not the analyzed folder
        if self._is_repomind_meta_question(question):
            answer = self._answer_repomind_meta(question)
            return {
                "answer": answer,
                "relevant_files": [],
                "relevant_commits": [],
            }

        # Try to answer locally first (no API needed)
        local_answer = self._try_local_answer(question_lower)
        if local_answer:
            return {
                "answer":           local_answer,
                "relevant_files":   relevant_files,
                "relevant_commits": relevant_commits,
            }

        # Conversational answer about the analyzed repository (LLM)
        answer = self._ask_gemini_repo(question, relevant_files)

        return {
            "answer":           answer,
            "relevant_files":   relevant_files,
            "relevant_commits": relevant_commits,
        }

    def _find_relevant_files(self, question: str) -> list:
        """Find files relevant to the question."""
        relevant = set()

        # Extract meaningful keywords from question
        keywords = re.findall(r"[a-z_]{3,}", question)
        stop_words = {
            "what", "which", "where", "when", "how", "why", "who",
            "the", "this", "that", "with", "from", "have", "has",
            "are", "were", "will", "been", "file", "files", "code",
            "show", "tell", "give", "list", "most", "more", "any",
            "about", "does", "did", "can", "could", "would", "should",
        }
        keywords = [k for k in keywords if k not in stop_words]

        for kw in keywords:
            if kw in self.file_index:
                relevant.update(self.file_index[kw][:3])

        # If question mentions specific file extensions
        if ".py" in question or "python" in question:
            for f in self.files:
                if f.endswith(".py"):
                    relevant.add(f)
                    if len(relevant) >= 5:
                        break

        return list(relevant)[:5]

    def _find_relevant_commits(self, question: str) -> list:
        """Find commits relevant to the question."""
        if not self.time_machine:
            return []

        commits  = self.time_machine.get("commits", [])
        relevant = []

        keywords = re.findall(r"[a-z]{4,}", question)

        for commit in commits:
            msg = commit.get("message", "").lower()
            if any(kw in msg for kw in keywords):
                sha = commit.get("sha", "")[:7]
                relevant.append(f"{sha}: {commit.get('message','')[:50]}")

        return relevant[:3]

    # ─────────────────────────────────────────────────────────────
    # LOCAL ANSWERS (no API needed — instant + no quota issues)
    # ─────────────────────────────────────────────────────────────

    def _try_local_answer(self, question: str) -> str:
        """
        Answer common questions locally without API calls.
        Returns answer string or empty string if can't answer locally.
        """
        sec  = self.results.get("security", {})
        cr   = self.results.get("code_review", {})
        dep  = self.results.get("dependency", {})
        doc  = self.results.get("documentation", {})
        arch = self.results.get("architecture", {})
        bf   = self.results.get("bug_fix", {})

        # ── SECURITY questions ───────────────────────────────────
        if any(w in question for w in ["vulnerabilit", "security", "risk", "dangerous", "unsafe", "injection", "sql"]):
            vulns     = sec.get("vulnerabilities", [])
            risk      = sec.get("risk_level", "UNKNOWN")
            total     = sec.get("total_found", 0)
            score     = sec.get("score", "N/A")

            if total == 0:
                return f"✅ **No security vulnerabilities** found. Security score: {score}/100."

            lines = [f"🔒 **Security Risk Level: {risk}** | Score: {score}/100 | {total} vulnerabilities found\n"]
            by_sev = defaultdict(list)
            for v in vulns:
                by_sev[v.get("severity","LOW")].append(v)

            for sev in ["CRITICAL","HIGH","MEDIUM","LOW"]:
                if sev in by_sev:
                    lines.append(f"**{sev} ({len(by_sev[sev])}):**")
                    for v in by_sev[sev][:3]:
                        lines.append(
                            f"- {v.get('type','?')} in `{v.get('file','?')}` "
                            f"line {v.get('line','?')}"
                        )
            lines.append(f"\n💡 Check the **Auto-Fix tab** for {bf.get('stats',{}).get('security_fixes',0)} auto-patches.")
            return "\n".join(lines)

        # ── CODE QUALITY questions ───────────────────────────────
        if any(w in question for w in ["code quality", "code issue", "code review", "code problem", "code smell"]):
            issues = cr.get("issues", [])
            score  = cr.get("score", "N/A")
            high   = sum(1 for i in issues if i.get("severity","").upper() == "HIGH")
            med    = sum(1 for i in issues if i.get("severity","").upper() == "MEDIUM")
            low    = sum(1 for i in issues if i.get("severity","").upper() == "LOW")

            lines = [f"🔍 **Code Review Score: {score}/100** | {len(issues)} total issues\n"]
            lines.append(f"- 🔴 High: {high}  |  🟡 Medium: {med}  |  🟢 Low: {low}\n")

            if issues:
                lines.append("**Top Issues:**")
                for i in issues[:5]:
                    lines.append(
                        f"- [{i.get('severity','?')}] {i.get('issue','?')} "
                        f"in `{i.get('file','?')}` line {i.get('line','?')}"
                    )
            return "\n".join(lines)

        # ── ARCHITECTURE questions ───────────────────────────────
        if any(w in question for w in ["architect", "structure", "component", "module", "folder", "organiz"]):
            comps  = arch.get("components", [])
            tech   = arch.get("tech_stack", [])
            ai_d   = arch.get("ai_description", {})

            lines = [f"🏗️ **Repository Architecture**\n"]
            if tech:
                lines.append(f"**Tech Stack:** {', '.join(tech)}\n")
            if ai_d.get("architecture_pattern"):
                lines.append(f"**Pattern:** {ai_d['architecture_pattern']}\n")
            if comps:
                lines.append("**Components:**")
                for c in comps[:8]:
                    fc = c.get("file_count", len(c.get("files",[])))
                    lines.append(f"- {c.get('icon','📁')} **{c.get('name','?')}** — {fc} files")
            if ai_d.get("data_flow"):
                lines.append(f"\n**Data Flow:** {ai_d['data_flow']}")
            return "\n".join(lines)

        # ── FRAMEWORK / TECH STACK questions ────────────────────
        if any(w in question for w in ["framework", "tech", "stack", "language", "librar", "tool", "using"]):
            tech = arch.get("tech_stack", [])
            if tech:
                return f"🛠️ **Tech Stack detected:**\n" + "\n".join(f"- {t}" for t in tech)
            return "🛠️ Tech stack could not be detected automatically. Check the Architecture tab for more details."

        # ── DOCUMENTATION questions ──────────────────────────────
        if any(w in question for w in ["doc", "readme", "comment", "docstring", "document"]):
            coverage = doc.get("doc_coverage", 0)
            missing  = len(doc.get("missing_docs", []))
            score    = doc.get("score", "N/A")
            readme   = doc.get("readme_analysis", {})

            lines = [f"📄 **Documentation Score: {score}/100**\n"]
            lines.append(f"- Coverage: {coverage}%")
            lines.append(f"- Undocumented items: {missing}")
            if readme.get("found"):
                lines.append(f"- README quality: {readme.get('quality','?')}")
            else:
                lines.append("- ❌ No README found!")
            lines.append(f"\n💡 Check the **Docs tab** for AI-generated docstrings.")
            return "\n".join(lines)

        # ── DEPENDENCY questions ─────────────────────────────────
        if any(w in question for w in ["depend", "package", "librar", "requirement", "pip", "npm", "cve", "outdated", "vulnerabl"]):
            pkgs     = dep.get("packages", [])
            vulns    = dep.get("vulnerabilities", [])
            outdated = dep.get("outdated", [])
            score    = dep.get("score", "N/A")

            lines = [f"📦 **Dependency Health: {score}/100**\n"]
            lines.append(f"- Total packages: {len(pkgs)}")
            lines.append(f"- Vulnerable: {len(vulns)}")
            lines.append(f"- Outdated: {len(outdated)}")

            if vulns:
                lines.append("\n**Vulnerable packages:**")
                for v in vulns[:4]:
                    lines.append(
                        f"- 🔴 `{v.get('name','?')}` "
                        f"v{v.get('version','?')} → "
                        f"v{v.get('latest_version','?')}"
                    )
            return "\n".join(lines)

        # ── PATCHES / BUG FIX questions ──────────────────────────
        if any(w in question for w in ["patch", "fix", "bug", "auto", "repair", "resolve"]):
            stats   = bf.get("stats", {})
            patches = bf.get("patches", [])
            total   = stats.get("total_patches", 0)
            sec_f   = stats.get("security_fixes", 0)
            cq_f    = stats.get("code_quality_fixes", 0)

            lines = [f"🔧 **Auto-Patches Generated: {total}**\n"]
            lines.append(f"- Security fixes: {sec_f}")
            lines.append(f"- Code quality fixes: {cq_f}")

            if patches:
                lines.append("\n**Patches:**")
                for p in patches[:4]:
                    vuln = p.get("vulnerability", p.get("issue","Fix"))
                    lines.append(
                        f"- [{p.get('severity','?')}] {vuln} "
                        f"in `{p.get('file','?')}` line {p.get('line','?')}"
                    )
            lines.append("\n💡 Check the **Auto-Fix tab** to see before/after code.")
            return "\n".join(lines)

        # ── COMMIT / HISTORY questions ───────────────────────────
        if any(w in question for w in ["commit", "histor", "timeline", "git", "author", "who made", "change"]):
            if not self.time_machine:
                return "⏳ Time Machine data not available. Please enable the Time Machine Agent and re-analyze."

            commits = self.time_machine.get("commits", [])
            lines   = [f"⏳ **Git History: {len(commits)} commits tracked**\n"]

            # Count authors
            authors = defaultdict(int)
            for c in commits:
                authors[c.get("author","Unknown")] += 1

            if authors:
                lines.append("**Top Contributors:**")
                for author, count in sorted(authors.items(), key=lambda x: -x[1])[:4]:
                    lines.append(f"- {author}: {count} commits")

            if commits:
                lines.append("\n**Recent Commits:**")
                for c in commits[:5]:
                    sha = c.get("sha","")[:7]
                    msg = c.get("message","")[:60]
                    lines.append(f"- `{sha}` {msg}")

            return "\n".join(lines)

        # ── RISK / HEATMAP questions ─────────────────────────────
        if any(w in question for w in ["risk", "heatmap", "danger", "critical file", "risky"]):
            hm      = self.results.get("risk_heatmap", {})
            overall = hm.get("overall_risk_score", 0)
            top     = hm.get("top_risky_files", [])

            lines = [f"🗺️ **Repository Risk Score: {overall}/100**\n"]
            if top:
                lines.append("**Most Risky Files:**")
                for f in top[:5]:
                    lines.append(
                        f"- {f.get('emoji','⚠️')} `{f.get('file','?')}` "
                        f"— Risk: {f.get('score','?')}/100"
                    )
            return "\n".join(lines)

        # ── SCORE / OVERVIEW questions ───────────────────────────
        if any(w in question for w in [
            "score", "overview", "summar", "overall", "health"
        ]):
            scores = []
            for k in ["code_review","security","documentation","dependency"]:
                s = self.results.get(k,{}).get("score")
                if s is not None:
                    scores.append(s)
            overall = int(sum(scores)/len(scores)) if scores else 0

            arch = self.results.get("architecture", {})
            tech = arch.get("tech_stack", [])

            ext_counts = defaultdict(int)
            for f in self.files:
                ext = f.rsplit(".", 1)[-1] if "." in f else "other"
                ext_counts[ext] += 1
            top_exts = sorted(ext_counts.items(), key=lambda x: -x[1])[:3]

            lines = [f"🧠 **RepoMind Repository Overview**\n"]
            lines.append(f"**RepoScore™: {overall}/100**\n")
            lines.append(f"- 📁 Total files: {len(self.files)}")
            lines.append(f"- 🔤 File types: {', '.join(f'{e}({c})' for e,c in top_exts)}")
            if tech:
                lines.append(f"- 🛠️ Tech stack: {', '.join(tech)}")
            lines.append(f"\n**Agent Scores:**")
            lines.append(f"- 🔍 Code Review: {self.results.get('code_review',{}).get('score','N/A')}/100")
            lines.append(f"- 🔒 Security: {self.results.get('security',{}).get('score','N/A')}/100")
            lines.append(f"- 📄 Documentation: {self.results.get('documentation',{}).get('score','N/A')}/100")
            lines.append(f"- 📦 Dependencies: {self.results.get('dependency',{}).get('score','N/A')}/100")
            return "\n".join(lines)

        # ── FILE specific questions ──────────────────────────────
        if any(w in question for w in ["file", "most issue", "worst", "biggest problem"]):
            issues = cr.get("issues", [])
            by_file = defaultdict(list)
            for i in issues:
                by_file[i.get("file","?")].append(i)

            if by_file:
                worst = sorted(by_file.items(), key=lambda x: -len(x[1]))[:3]
                lines = ["📄 **Files with Most Issues:**\n"]
                for filepath, file_issues in worst:
                    high = sum(1 for i in file_issues if i.get("severity","").upper()=="HIGH")
                    lines.append(
                        f"- `{filepath}` — {len(file_issues)} issues "
                        f"({high} high severity)"
                    )
                return "\n".join(lines)

        # Can't answer locally — return empty to trigger API
        return ""

    # ─────────────────────────────────────────────────────────────
    # GEMINI API (with rate limiting + retry)
    # ─────────────────────────────────────────────────────────────

    def _answer_repomind_meta(self, question: str) -> str:
        """Fast local response about RepoMind (avoids unnecessary API latency/failures)."""
        _ = question
        return REPOMIND_STATIC_INTRO

    def _ask_gemini_repo(self, question: str, relevant_files: list) -> str:
        """Call Gemini for natural answers about the analyzed repository."""
        from utils.llm import get_gemini_response

        now = time.time()
        elapsed = now - self._last_api_call
        if elapsed < MIN_CHAT_API_INTERVAL_S:
            time.sleep(MIN_CHAT_API_INTERVAL_S - elapsed)

        file_context = ""
        if relevant_files:
            for fp in relevant_files[:2]:
                content = self.files.get(fp, "")
                file_context += f"\n--- {fp} ---\n{content[:800]}\n"

        prompt = f"""You are a helpful coding assistant inside RepoMind. The user has already run analysis on a **local repository**. Your job is to answer their question in clear, conversational language.

Use the facts below. If something is unknown from the data, say so—do not invent files, scores, or vulnerabilities.

REPOSITORY ANALYSIS (facts):
{self.repo_summary[:2200]}

RELEVANT FILE EXCERPTS:
{file_context[:1200] if file_context else '(No file excerpts matched keywords; rely on the summary above.)'}

USER QUESTION:
{question}

Guidelines:
- Answer the question directly (e.g. if they ask what the project is "about", infer from tech stack, components, and file types in the facts).
- Vary structure: prose, or short bullets when listing issues or features—not the same template every time.
- Keep it under 220 words unless they ask for exhaustive detail.
"""

        try:
            self._last_api_call = time.time()
            response = get_gemini_response(prompt, temperature=REPO_CHAT_TEMPERATURE)

            if not response or len(response.strip()) < 3:
                return self._fallback_repo_answer(question)
            if response.startswith("⚠️"):
                return response
            return response

        except Exception as e:
            err = str(e).lower()
            if "quota" in err or "rate" in err or "429" in err:
                return self._fallback_repo_answer(question)
            return (
                f"⚠️ Could not get AI response: {str(e)[:120]}\n\n"
                "Try again in a minute."
            )

    def _fallback_repo_answer(self, _question: str) -> str:
        """Short cached hint when the model is unavailable; avoids repeating the same giant block."""
        return (
            "I couldn’t reach the AI model right now, so here’s a compact snapshot from the last analysis:\n\n"
            f"{self.repo_summary[:800]}\n\n"
            "_If this looks stale, run analysis again or retry the chat in a minute._"
        )