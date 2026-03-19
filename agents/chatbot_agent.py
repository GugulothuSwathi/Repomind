 # agents/chatbot_agent.py
from __future__ import annotations
# ============================================
# RepoMind - Enhanced Repository Chatbot Agent ⭐
#
# RAG over ALL agent results + Time Machine data:
# - Code review, security, deps, architecture
# - Commit history, risk timeline, arch snapshots
# - Predictive risk
# ============================================

from typing import Optional
from utils.llm import get_gemini_response


class RepoChatbot:

    def __init__(self):
        self.files         = {}
        self.analysis      = {}
        self.time_machine  = {}
        self.is_indexed    = False
        self.chat_history  = []
        self.repo_summary  = ""

    # ─────────────────────────────────────────────
    # INDEXING
    # ─────────────────────────────────────────────

    def index_repository(
        self,
        files: dict[str, str],
        analysis_results: Optional[dict] = None,
        time_machine_result: Optional[dict] = None,
    ) -> None:
        self.files        = files
        self.analysis     = analysis_results or {}
        self.time_machine = time_machine_result or {}
        self.repo_summary = self._create_repo_summary()
        self.is_indexed   = True
        print(f"Chatbot indexed {len(files)} files + time machine data")

    # ─────────────────────────────────────────────
    # QUERYING
    # ─────────────────────────────────────────────

    def ask(self, question: str) -> dict:
        if not self.is_indexed:
            return {
                "answer": "Repository not indexed yet. Please run analysis first.",
                "relevant_files": [],
                "relevant_commits": [],
                "confidence": "LOW",
            }

        relevant_files = self._find_relevant_files(question)
        time_ctx       = self._build_time_machine_context(question)
        agent_ctx      = self._build_agent_context(question)
        file_ctx       = self._build_file_context(relevant_files)

        history_text = ""
        if self.chat_history:
            history_text = "\n\nPrevious conversation:\n"
            for turn in self.chat_history[-3:]:
                history_text += f"User: {turn['question']}\nAssistant: {turn['answer'][:300]}\n\n"

        prompt = f"""You are RepoMind, an expert AI assistant with deep knowledge of this code repository.
You have access to: code files, security scans, code review results, dependency analysis, architecture diagrams, commit history, risk timelines, and predictive risk data.

REPOSITORY OVERVIEW:
{self.repo_summary}

AGENT ANALYSIS RESULTS:
{agent_ctx}

TIME MACHINE DATA (Commit History & Risk):
{time_ctx}

RELEVANT SOURCE FILES:
{file_ctx}
{history_text}

USER QUESTION: {question}

INSTRUCTIONS:
- Answer clearly and specifically. Reference commit hashes, file names, or line numbers when relevant.
- For timeline questions ("last 3 months", "before v1.0"), use the commit history data.
- For risk questions, reference specific risk scores and the files/commits involved.
- For architecture questions, describe the module structure.
- For prediction questions, use the predictive risk data.
- Format code with markdown code blocks.
- If referencing a commit, mention its hash (first 8 chars) and date.
- Keep the answer focused and useful.
- If data is unavailable, say so clearly rather than guessing.
"""

        answer = get_gemini_response(prompt, temperature=0.35)

        if "Gemini API Error" in answer or ("quota" in answer.lower() and len(answer) > 200):
            answer = self._fallback_answer(question)

        self.chat_history.append({"question": question, "answer": answer})

        return {
            "answer":           answer,
            "relevant_files":   [f["path"] for f in relevant_files],
            "relevant_commits": self._find_relevant_commits(question),
            "confidence":       "HIGH" if (relevant_files or time_ctx) else "MEDIUM",
        }

    # ─────────────────────────────────────────────
    # CONTEXT BUILDERS
    # ─────────────────────────────────────────────

    def _build_time_machine_context(self, question: str) -> str:
        if not self.time_machine or self.time_machine.get("error"):
            return "No time machine data available."

        parts = []
        q     = question.lower()

        commits = self.time_machine.get("commits", [])
        if commits:
            parts.append(f"COMMIT HISTORY ({len(commits)} commits):")
            for c in commits[:15]:
                parts.append(f"  [{c['hash'][:8]}] {c['date']} | {c['author']} | {c['message'][:70]}")

        risk_tl = self.time_machine.get("risk_timeline", [])
        if risk_tl:
            parts.append(f"\nRISK TIMELINE:")
            show_all = any(k in q for k in ["risk","danger","vuln","safe","trend","timeline","history"])
            for r in (risk_tl if show_all else risk_tl[-5:]):
                parts.append(
                    f"  [{r['hash'][:8]}] {r['date']} | Risk: {r['risk_score']}/100 "
                    f"({r['risk_level']}) | Dominant: {r.get('dominant_risk','?')} | {r['message'][:50]}"
                )
            scores = [r["risk_score"] for r in risk_tl]
            parts.append(f"  Avg: {sum(scores)/len(scores):.1f} | Max: {max(scores)} | Min: {min(scores)}")

        file_evo = self.time_machine.get("file_evolution", [])
        if file_evo and any(k in q for k in ["file","added","removed","changed","evolution","history"]):
            parts.append(f"\nFILE EVOLUTION:")
            for evo in file_evo[:10]:
                parts.append(
                    f"  {evo['date']} | +{len(evo.get('files_added',[]))} "
                    f"-{len(evo.get('files_removed',[]))} "
                    f"~{len(evo.get('files_modified',[]))} | Total: {evo['total_files']} | {evo['message'][:50]}"
                )

        arch_snaps = self.time_machine.get("arch_snapshots", [])
        if arch_snaps and any(k in q for k in ["architect","module","structure","dependency","diagram"]):
            parts.append(f"\nARCHITECTURE SNAPSHOTS:")
            for snap in arch_snaps[:5]:
                nodes = snap.get("nodes", [])
                if nodes:
                    parts.append(
                        f"  [{snap['hash'][:8]}] {snap['date']} | "
                        f"Modules: {', '.join(nodes[:8])} | Deps: {len(snap.get('edges',[]))}"
                    )

        predictions = self.time_machine.get("predictions", [])
        if predictions and any(k in q for k in ["predict","future","next","risky","likely","bug"]):
            parts.append(f"\nPREDICTED HIGH-RISK FILES:")
            for pred in predictions[:8]:
                parts.append(
                    f"  {pred['file']} | Score: {pred['predicted_score']}/100 "
                    f"({pred['risk_level']}) | Churn: {pred['churn_lines']} | "
                    f"Bug commits: {pred['bug_commits']} | {pred['reason']}"
                )

        return "\n".join(parts) if parts else "Time machine data available but no relevant entries."

    def _build_agent_context(self, question: str) -> str:
        if not self.analysis:
            return "No agent analysis available."

        parts = []
        q     = question.lower()

        sec = self.analysis.get("security", {})
        if sec and any(k in q for k in ["security","vuln","risk","danger","cve","safe","issue"]):
            vulns = sec.get("vulnerabilities", [])
            parts.append(f"SECURITY: Risk={sec.get('risk_level','?')} | Vulns={sec.get('total_found',0)} | Score={sec.get('score','?')}/100")
            for v in vulns[:5]:
                parts.append(f"  [{v.get('severity','?')}] {v.get('file','?')} line {v.get('line','?')}: {v.get('type','?')}")

        cr = self.analysis.get("code_review", {})
        if cr and any(k in q for k in ["code","review","issue","quality","smell","fix","problem"]):
            issues = cr.get("issues", [])
            parts.append(f"CODE REVIEW: Score={cr.get('score','?')}/100 | Issues={len(issues)}")
            for issue in issues[:5]:
                parts.append(f"  [{issue.get('severity','?')}] {issue.get('file','?')}: {issue.get('issue','?')}")

        dep = self.analysis.get("dependency", {})
        if dep and any(k in q for k in ["depend","package","library","require","pip","npm","import"]):
            parts.append(
                f"DEPENDENCIES: Score={dep.get('score','?')}/100 | "
                f"Packages={dep.get('total_packages',0)} | "
                f"Vulnerable={len(dep.get('vulnerabilities',[]))}"
            )

        arch = self.analysis.get("architecture", {})
        if arch and any(k in q for k in ["architect","structure","module","component","design","pattern"]):
            components = arch.get("components", [])
            tech       = arch.get("tech_stack", [])
            parts.append(f"ARCHITECTURE: Components={len(components)} | Tech={', '.join(tech[:6])}")
            for comp in components[:6]:
                parts.append(f"  {comp.get('icon','•')} {comp.get('name','?')} ({len(comp.get('files',[]))} files)")

        hm = self.analysis.get("risk_heatmap", {})
        if hm and any(k in q for k in ["risk","heatmap","worst","hotspot","dangerous"]):
            top = hm.get("top_risky_files", [])
            parts.append(f"RISK HEATMAP: Overall={hm.get('overall_risk_score','?')}/100")
            for f in top[:5]:
                parts.append(f"  {f['file']}: {f['score']}/100")

        if not parts:
            parts.append(
                f"Security={self.analysis.get('security',{}).get('risk_level','N/A')} | "
                f"CodeReview={self.analysis.get('code_review',{}).get('score','N/A')}/100 | "
                f"Deps vulns={len(self.analysis.get('dependency',{}).get('vulnerabilities',[]))}"
            )

        return "\n".join(parts)

    def _build_file_context(self, relevant_files: list[dict]) -> str:
        if not relevant_files:
            return "No directly matching source files found."
        parts      = []
        total_chars = 0
        for f in relevant_files:
            if total_chars >= 4000:
                break
            snippet = f"\n=== {f['path']} ===\n{f['content'][:700]}\n"
            parts.append(snippet)
            total_chars += len(snippet)
        return "".join(parts)

    def _find_relevant_files(self, question: str, top_k: int = 5) -> list[dict]:
        STOP_WORDS = {
            "the","is","in","it","to","a","an","and","or","what","where",
            "how","which","who","when","why","show","tell","explain","find",
            "get","me","i","you","this","that","these","those","are","was",
        }
        keywords = [
            w.strip("?.,!") for w in question.lower().split()
            if w not in STOP_WORDS and len(w) > 2
        ]
        scored = []
        for filepath, content in self.files.items():
            score = 0
            cl = content.lower()
            fl = filepath.lower()
            for kw in keywords:
                if kw in fl:
                    score += 10
                score += cl.count(kw)
            if score > 0:
                scored.append({"path": filepath, "content": content[:2000], "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _find_relevant_commits(self, question: str) -> list[str]:
        commits = self.time_machine.get("commits", [])
        if not commits:
            return []
        q       = question.lower()
        relevant = []
        for c in commits:
            msg = c.get("message", "").lower()
            if any(w in msg for w in q.split() if len(w) > 3):
                relevant.append(c["hash"][:8])
        return relevant[:5]

    def _create_repo_summary(self) -> str:
        files     = list(self.files.keys())
        ext_count: dict[str, int] = {}
        for f in files:
            ext = f.rsplit(".", 1)[-1] if "." in f else "other"
            ext_count[ext] = ext_count.get(ext, 0) + 1
        ext_str  = ", ".join(f"{k}:{v}" for k, v in sorted(ext_count.items(), key=lambda x: -x[1])[:6])
        commits  = self.time_machine.get("commits", [])
        preds    = self.time_machine.get("predictions", [])
        return (
            f"Files: {len(files)} | Types: {ext_str}\n"
            f"Commits analyzed: {len(commits)}\n"
            f"High-risk predictions: {len([p for p in preds if p.get('risk_level')=='HIGH'])}\n"
            f"Key files: {', '.join(files[:8])}"
        )

    def _fallback_answer(self, question: str) -> str:
        q       = question.lower()
        risk_tl = self.time_machine.get("risk_timeline", [])
        commits = self.time_machine.get("commits", [])

        if risk_tl and any(k in q for k in ["risk","danger","safe","vuln"]):
            scores = [r["risk_score"] for r in risk_tl]
            max_r  = max(risk_tl, key=lambda x: x["risk_score"])
            return (
                f"**Risk Summary** ({len(risk_tl)} commits):\n\n"
                f"- Average: **{sum(scores)/len(scores):.1f}/100**\n"
                f"- Highest: `{max_r['hash'][:8]}` on {max_r['date']} — **{max_r['risk_score']}/100**\n"
                f"  `{max_r['message'][:70]}`\n"
                f"- Trend: {'📈 Rising' if scores[-1] > scores[0] else '📉 Falling'}"
            )

        preds = self.time_machine.get("predictions", [])
        if preds and any(k in q for k in ["predict","future","next","risky"]):
            lines = ["**Predicted High-Risk Files:**\n"]
            for p in preds[:5]:
                lines.append(f"- `{p['file']}` — **{p['predicted_score']}/100** | {p['reason']}")
            return "\n".join(lines)

        if commits and any(k in q for k in ["commit","history","author","who","when","change"]):
            lines = [f"**Last {min(len(commits),8)} commits:**\n"]
            for c in commits[:8]:
                lines.append(f"- `{c['hash'][:8]}` {c['date']} | **{c['author']}**: {c['message'][:70]}")
            return "\n".join(lines)

        sec = self.analysis.get("security", {})
        if sec and any(k in q for k in ["security","vuln","cve"]):
            return (
                f"**Security Summary:**\n\n"
                f"- Risk Level: **{sec.get('risk_level','?')}**\n"
                f"- Vulnerabilities: **{sec.get('total_found',0)}**\n"
                f"- Score: **{sec.get('score','?')}/100**"
            )

        return (
            f"**Repository Summary:**\n\n"
            f"- Files analyzed: **{len(self.files)}**\n"
            f"- Commits in time machine: **{len(commits)}**\n"
            f"- Security risk: **{self.analysis.get('security',{}).get('risk_level','N/A')}**\n"
            f"- Code review score: **{self.analysis.get('code_review',{}).get('score','N/A')}/100**\n\n"
            "_(Gemini quota exceeded — showing cached data. Try again in ~1 minute.)_"
        )