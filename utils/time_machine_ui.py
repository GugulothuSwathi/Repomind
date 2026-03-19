# ============================================
# RepoMind - Time Machine Tab UI
# File: utils/time_machine_ui.py
#
# USAGE: Import and call show_time_machine(result)
# inside your app.py tab.
# ============================================

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime


def show_time_machine(data: dict):
    """
    Renders the full Repository Time Machine dashboard tab.
    Call this inside your Streamlit tab.

    Args:
        data: dict returned by run_time_machine_agent()
    """
    if not data:
        st.info("⏳ Time Machine Agent was not run.")
        return

    if data.get("error"):
        st.error(f"❌ Time Machine Error: {data['error']}")
        st.info("💡 Make sure `git` is installed and the repository is public (or your GITHUB_TOKEN has access).")
        return

    commits     = data.get("commits", [])
    file_evo    = data.get("file_evolution", [])
    risk_tl     = data.get("risk_timeline", [])
    arch_snaps  = data.get("arch_snapshots", [])
    predictions = data.get("predictions", [])
    summary     = data.get("summary", "")

    # ── Header ───────────────────────────────────────────────────────────
    st.markdown("### ⏳ Repository Time Machine")
    st.caption(f"Analyzed {len(commits)} commits · Tracking code evolution, risk trends & predictions")

    if summary:
        st.markdown(
            f"<div style='background:#161b22;border:1px solid #30363d;border-radius:10px;"
            f"padding:16px;margin-bottom:16px;color:#c9d1d9;'>"
            f"🧠 <b>AI Evolution Summary</b><br><br>{summary}</div>",
            unsafe_allow_html=True,
        )

    # ── Top metrics ───────────────────────────────────────────────────────
    if commits and risk_tl:
        avg_risk   = sum(r["risk_score"] for r in risk_tl) / len(risk_tl)
        max_risk   = max(r["risk_score"] for r in risk_tl)
        trend      = _risk_trend(risk_tl)
        trend_icon = "📈" if trend > 0 else "📉" if trend < 0 else "➡️"

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Commits Analyzed", len(commits))
        m2.metric("Avg Risk Score",   f"{avg_risk:.1f}/100")
        m3.metric("Peak Risk",        f"{max_risk}/100")
        m4.metric("Risk Trend",       f"{trend_icon} {'Rising' if trend > 0 else 'Falling' if trend < 0 else 'Stable'}")

    st.markdown("---")

    # ── Tabs inside the Time Machine tab ─────────────────────────────────
    sub_tabs = st.tabs([
        "📊 Risk Timeline",
        "📁 File Evolution",
        "🏗️ Architecture Evolution",
        "🔮 Predictive Risk",
        "📋 Commit History",
    ])

    # ── SUB-TAB 1: Risk Timeline ──────────────────────────────────────────
    with sub_tabs[0]:
        _show_risk_timeline(risk_tl)

    # ── SUB-TAB 2: File Evolution ─────────────────────────────────────────
    with sub_tabs[1]:
        _show_file_evolution(file_evo)

    # ── SUB-TAB 3: Architecture Evolution ────────────────────────────────
    with sub_tabs[2]:
        _show_arch_evolution(arch_snaps)

    # ── SUB-TAB 4: Predictive Risk ────────────────────────────────────────
    with sub_tabs[3]:
        _show_predictive_risk(predictions)

    # ── SUB-TAB 5: Commit History ─────────────────────────────────────────
    with sub_tabs[4]:
        _show_commit_history(commits)


# ─────────────────────────────────────────────
# SUB-SECTION RENDERERS
# ─────────────────────────────────────────────

def _show_risk_timeline(risk_tl: list[dict]):
    st.markdown("#### 📊 Risk Score Over Time")
    st.caption("Each point is a commit. Hover to see commit message and risk breakdown.")

    if not risk_tl:
        st.info("No risk data available.")
        return

    df = pd.DataFrame(risk_tl)

    # Reverse so oldest → newest left to right
    df = df.iloc[::-1].reset_index(drop=True)
    df["index"] = range(len(df))
    df["short_msg"] = df["message"].str[:50]

    color_map = {"CRITICAL": "#f85149", "HIGH": "#e3b341", "MEDIUM": "#d29922", "LOW": "#3fb950"}

    # ── Line chart ───────────────────────────────────────────────────────
    fig = go.Figure()

    # Colored background bands
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(248,81,73,0.08)",  line_width=0)
    fig.add_hrect(y0=50, y1=70,  fillcolor="rgba(227,179,65,0.08)", line_width=0)
    fig.add_hrect(y0=30, y1=50,  fillcolor="rgba(210,153,34,0.08)", line_width=0)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(63,185,80,0.08)",  line_width=0)

    # Main risk line
    fig.add_trace(go.Scatter(
        x=df["index"],
        y=df["risk_score"],
        mode="lines+markers",
        name="Risk Score",
        line=dict(color="#58a6ff", width=2.5),
        marker=dict(
            size=10,
            color=df["risk_level"].map(color_map).fillna("#8b949e"),
            line=dict(color="#0d1117", width=1.5),
        ),
        customdata=df[["short_msg", "date", "dominant_risk"]].values,
        hovertemplate=(
            "<b>Commit:</b> %{customdata[0]}<br>"
            "<b>Date:</b> %{customdata[1]}<br>"
            "<b>Risk Score:</b> %{y}/100<br>"
            "<b>Dominant risk:</b> %{customdata[2]}<extra></extra>"
        ),
    ))

    # Security sub-line
    fig.add_trace(go.Scatter(
        x=df["index"], y=df["security_score"],
        mode="lines", name="Security",
        line=dict(color="#f85149", width=1.2, dash="dot"),
        opacity=0.6,
    ))
    # Complexity sub-line
    fig.add_trace(go.Scatter(
        x=df["index"], y=df["complexity_score"],
        mode="lines", name="Complexity",
        line=dict(color="#e3b341", width=1.2, dash="dot"),
        opacity=0.6,
    ))

    fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),
        height=380,
        margin=dict(t=30, b=50, l=50, r=20),
        xaxis=dict(
            title="Commits (oldest → newest)",
            showgrid=False,
            tickvals=df["index"].tolist(),
            ticktext=[d[:10] for d in df["date"].tolist()],
            tickangle=-45,
        ),
        yaxis=dict(title="Risk Score", range=[0, 100], gridcolor="#21262d"),
        legend=dict(bgcolor="#161b22", bordercolor="#30363d"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Heatmap per commit × risk category ───────────────────────────────
    st.markdown("#### 🔥 Risk Heatmap")
    # Make unique commit labels by adding index number
    commit_labels = [f"#{i+1} {d[:10]}" for i, d in enumerate(df["date"].tolist())]

    heat_df = pd.DataFrame({
        "Commit":     commit_labels,
        "Security":   df["security_score"].tolist(),
        "Complexity": df["complexity_score"].tolist(),
        "Dependency": df["dependency_score"].tolist(),
    }).set_index("Commit").T

    fig2 = px.imshow(
        heat_df,
        color_continuous_scale=[[0, "#1a2744"], [0.3, "#d29922"], [0.7, "#e3b341"], [1, "#f85149"]],
        aspect="auto",
        title="Risk Category Heatmap (darker = higher risk)",
    )
    fig2.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),
        height=200,
        margin=dict(t=40, b=30, l=100, r=20),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig2, use_container_width=True)


def _show_file_evolution(file_evo: list[dict]):
    st.markdown("#### 📁 File Count Evolution")
    st.caption("How the repository grew (or shrank) over time.")

    if not file_evo:
        st.info("No file evolution data available.")
        return

    df = pd.DataFrame(file_evo).iloc[::-1].reset_index(drop=True)
    df["index"] = range(len(df))

    # Stacked bar: files added vs removed
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["index"], y=df["files_added"].apply(len),
        name="Files Added", marker_color="#3fb950",
        customdata=df["message"].str[:60],
        hovertemplate="<b>+%{y} files</b><br>%{customdata}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df["index"], y=[-len(r) for r in df["files_removed"]],
        name="Files Removed", marker_color="#f85149",
        customdata=df["message"].str[:60],
        hovertemplate="<b>-%{y} files</b><br>%{customdata}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["index"], y=df["total_files"],
        name="Total Files", mode="lines+markers",
        line=dict(color="#58a6ff", width=2),
        yaxis="y2",
    ))

    fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),
        barmode="relative",
        height=360,
        margin=dict(t=20, b=50),
        xaxis=dict(
            title="Commits (oldest → newest)",
            tickvals=df["index"].tolist(),
            ticktext=[d[:10] for d in df["date"].tolist()],
            tickangle=-45, showgrid=False,
        ),
        yaxis=dict(title="Files Changed", gridcolor="#21262d"),
        yaxis2=dict(title="Total Files", overlaying="y", side="right", showgrid=False),
        legend=dict(bgcolor="#161b22", bordercolor="#30363d"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Most changed files table ──────────────────────────────────────────
    st.markdown("#### 🔄 Most Modified Files")
    from collections import Counter
    mod_counter: Counter = Counter()
    for evo in file_evo:
        for f in evo.get("files_modified", []):
            mod_counter[f] += 1
        for f in evo.get("files_added", []):
            mod_counter[f] += 1

    if mod_counter:
        top_files = mod_counter.most_common(10)
        rows = [{"File": f, "Changes Across Commits": c} for f, c in top_files]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _show_arch_evolution(arch_snaps: list[dict]):
    st.markdown("#### 🏗️ Architecture Evolution")
    st.caption("Select a commit to see the module dependency graph at that point in time.")

    if not arch_snaps:
        st.info("No architecture snapshots available.")
        return

    # Filter to snaps that actually have nodes
    valid_snaps = [s for s in arch_snaps if s.get("nodes")]
    if not valid_snaps:
        st.info("No Python module changes detected in the analyzed commits.")
        return

    commit_labels = [f"{s['date'][:10]} — {s['message'][:45]}" for s in valid_snaps]
    selected_idx  = st.select_slider(
        "Select commit",
        options=list(range(len(valid_snaps))),
        format_func=lambda i: commit_labels[i],
        value=len(valid_snaps) - 1,
    )

    snap = valid_snaps[selected_idx]

    col1, col2 = st.columns([3, 1])
    with col1:
        mermaid = snap.get("mermaid", "")
        if mermaid:
            st.markdown(f"```mermaid\n{mermaid}\n```")
        else:
            st.info("No module graph for this commit.")

    with col2:
        st.markdown(f"**📅 Date:** `{snap['date'][:10]}`")
        st.markdown(f"**📝 Commit:** {snap['message'][:60]}")
        nodes = snap.get("nodes", [])
        edges = snap.get("edges", [])
        st.metric("Modules", len(nodes))
        st.metric("Dependencies", len(edges))
        if nodes:
            st.markdown("**Modules:**")
            for n in nodes[:10]:
                st.markdown(f"- `{n}`")


def _show_predictive_risk(predictions: list[dict]):
    st.markdown("#### 🔮 Predicted High-Risk Files")
    st.caption("Files most likely to need attention in the near future, based on churn + bug history.")

    if not predictions:
        st.success("✅ No significant risk patterns detected. Repository looks stable!")
        return

    color_map = {"HIGH": "#f85149", "MEDIUM": "#e3b341", "LOW": "#3fb950"}
    level_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}

    # Bar chart
    df = pd.DataFrame(predictions[:10])
    fig = px.bar(
        df, x="predicted_score", y="file",
        orientation="h",
        color="risk_level",
        color_discrete_map=color_map,
        title="Predicted Risk Score by File",
        labels={"predicted_score": "Predicted Risk (0-100)", "file": "File"},
    )
    fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),
        height=min(300 + len(predictions) * 25, 550),
        margin=dict(t=40, b=20, l=20, r=20),
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detail cards
    st.markdown("---")
    for pred in predictions[:8]:
        level = pred["risk_level"]
        color = color_map.get(level, "#8b949e")
        icon  = level_icon.get(level, "⚪")

        with st.expander(
            f"{icon} `{pred['file']}` — Predicted Risk: **{pred['predicted_score']}/100**",
            expanded=(level == "HIGH"),
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("Predicted Score", f"{pred['predicted_score']}/100")
            c2.metric("Total Churn Lines", pred["churn_lines"])
            c3.metric("Bug-Fix Commits", pred["bug_commits"])
            st.markdown(f"**💡 Reason:** {pred['reason']}")
            st.markdown(
                f"<small style='color:#8b949e;'>Risk Level: "
                f"<span style='color:{color};font-weight:700;'>{level}</span></small>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<div style='background:#162032;border:1px solid #1f6feb;border-radius:8px;"
        "padding:12px;margin-top:12px;'>"
        "🤖 <b>How predictions work:</b> We score each file using a weighted formula: "
        "45% churn frequency + 40% bug-fix commit density + 15% recent repo risk trend. "
        "No ML model needed — pure signal analysis.</div>",
        unsafe_allow_html=True,
    )


def _show_commit_history(commits: list[dict]):
    st.markdown("#### 📋 Full Commit History")

    if not commits:
        st.info("No commits available.")
        return

    rows = []
    for c in commits:
        rows.append({
            "Date":    c["date"],
            "Author":  c["author"],
            "Message": c["message"][:80],
            "Hash":    c["hash"][:8],
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Author activity
    from collections import Counter
    author_counts = Counter(c["author"] for c in commits)
    if len(author_counts) > 1:
        st.markdown("#### 👥 Contributor Activity")
        auth_df = pd.DataFrame(
            [{"Author": a, "Commits": n} for a, n in author_counts.most_common(10)]
        )
        fig = px.bar(auth_df, x="Author", y="Commits", color="Commits",
                     color_continuous_scale=[[0, "#1f6feb"], [1, "#58a6ff"]])
        fig.update_layout(
            paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            font=dict(color="#e6edf3"), height=280,
            margin=dict(t=20, b=40), showlegend=False,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _risk_trend(risk_tl: list[dict]) -> float:
    """Positive = risk increasing, Negative = improving."""
    if len(risk_tl) < 4:
        return 0
    first_half  = risk_tl[:len(risk_tl) // 2]
    second_half = risk_tl[len(risk_tl) // 2:]
    avg_first   = sum(r["risk_score"] for r in first_half)  / len(first_half)
    avg_second  = sum(r["risk_score"] for r in second_half) / len(second_half)
    return avg_second - avg_first