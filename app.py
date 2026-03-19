 # app.py
# ============================================
# RepoMind - Main Streamlit Application
#
# This is the ENTRY POINT of the entire app.
# Run it with: streamlit run app.py
#
# This file:
# 1. Sets up the page layout and styling
# 2. Shows the input screen (GitHub URL + API keys)
# 3. Orchestrates all agents when user clicks "Analyze"
# 4. Displays results in a beautiful dashboard
# ============================================

import streamlit as st
import time
import os
import json
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Import our utilities
from utils.config import APP_NAME, APP_TAGLINE
from utils.github_helper import get_repo_files, get_repo_info, get_requirements_txt

# Import all agents
from agents.code_review_agent    import run_code_review_agent
from agents.security_agent       import run_security_agent
from agents.documentation_agent  import run_documentation_agent
from agents.dependency_agent     import run_dependency_agent
from agents.bug_fix_agent        import run_bug_fix_agent
from agents.risk_heatmap_agent   import run_risk_heatmap_agent
from agents.architecture_agent   import run_architecture_agent
from agents.chatbot_agent        import RepoChatbot 
from agents.time_machine_agent   import run_time_machine_agent
from utils.time_machine_ui       import show_time_machine
from collections import defaultdict
from pdf_generator import generate_repomind_report
import streamlit.components.v1 as components
# ============================================
# PAGE CONFIGURATION
# This MUST be the first Streamlit command!
# ============================================
st.set_page_config(
    page_title="RepoMind",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================
# CUSTOM CSS - Makes the app look professional
# ============================================
st.markdown("""
<style>
    /* Import modern fonts */
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Overall theme */
    .main {
        background: #0a0e1a;
        color: #e2e8f0;
    }

    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ============================================
       PREMIUM FINTECH ANIMATION SYSTEM
       Smooth, staggered, and interactive
    ============================================ */
    
    * {
        --transition-fast: 0.18s;
        --transition-normal: 0.28s;
        --transition-smooth: 0.42s;
        --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
        --ease-out-cubic: cubic-bezier(0.33, 1, 0.68, 1);
        --ease-in-out-cubic: cubic-bezier(0.4, 0, 0.2, 1);
        --ease-soft: cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }

    /* Hero banner */
    .hero-banner {
        background: linear-gradient(135deg, #1a1f3c 0%, #0d1117 50%, #1a2744 100%);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 40px;
        text-align: center;
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
        animation: heroSlideIn 0.72s var(--ease-out-expo) 1.6s both;
    }
    @keyframes heroSlideIn {
        0% { opacity: 0; transform: translateY(28px); filter: blur(8px); }
        100% { opacity: 1; transform: translateY(0); filter: blur(0); }
    }
    .hero-banner::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(88,166,255,0.05) 0%, transparent 60%);
        pointer-events: none;
    }
    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #58a6ff, #bc8cff, #79c0ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        padding: 0;
        animation: titleReveal 0.68s var(--ease-out-expo) 1.8s both;
    }
    @keyframes titleReveal {
        0% { opacity: 0; transform: translateY(20px) scale(0.95); }
        100% { opacity: 1; transform: translateY(0) scale(1); }
    }
    .hero-tagline {
        color: #8b949e;
        font-size: 1.1rem;
        margin-top: 8px;
        font-family: 'Space Grotesk', sans-serif;
        animation: taglineReveal 0.62s var(--ease-out-expo) 2s both;
    }
    @keyframes taglineReveal {
        0% { opacity: 0; letter-spacing: 4px; }
        100% { opacity: 1; letter-spacing: 0; }
    }
    .hero-badges {
        margin-top: 16px;
        display: flex;
        gap: 8px;
        justify-content: center;
        flex-wrap: wrap;
        animation: badgesSlideIn 0.58s var(--ease-out-expo) 2.2s both;
    }
    @keyframes badgesSlideIn {
        0% { opacity: 0; transform: translateY(16px); }
        100% { opacity: 1; transform: translateY(0); }
    }

    /* Metric cards */
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: all var(--transition-smooth) var(--ease-out-cubic);
        backdrop-filter: blur(8px);
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(135deg, rgba(88, 166, 255, 0.1), transparent);
        opacity: 0;
        transition: opacity var(--transition-smooth) var(--ease-out-cubic);
        pointer-events: none;
    }
    .metric-card:hover {
        border-color: #58a6ff;
        box-shadow: 0 16px 48px rgba(88, 166, 255, 0.12);
        transform: translateY(-6px);
    }
    .metric-card:hover::before {
        opacity: 1;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        transition: transform var(--transition-normal) var(--ease-soft);
    }
    .metric-card:hover .metric-value {
        transform: scale(1.08);
    }
    .metric-label {
        color: #8b949e;
        font-size: 0.85rem;
        margin-top: 4px;
        transition: color var(--transition-normal) var(--ease-soft);
    }
    .metric-card:hover .metric-label {
        color: #58a6ff;
    }

    /* Risk colors */
    .risk-critical {color: #f85149 !important;}
    .risk-high     {color: #e3b341 !important;}
    .risk-medium   {color: #d29922 !important;}
    .risk-low      {color: #3fb950 !important;}
    .risk-safe     {color: #58a6ff !important;}

    /* Section headers */
    .section-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.4rem;
        font-weight: 600;
        color: #e6edf3;
        padding: 12px 0;
        border-bottom: 2px solid #21262d;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
        animation: headerSlide 0.48s var(--ease-out-expo) forwards;
    }
    @keyframes headerSlide {
        0% { opacity: 0; transform: translateX(-12px); }
        100% { opacity: 1; transform: translateX(0); }
    }

    /* Issue cards */
    .issue-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 8px;
        transition: all var(--transition-smooth) var(--ease-out-cubic);
        backdrop-filter: blur(6px);
    }
    .issue-card:hover {
        transform: translateX(4px);
        border-color: #30363d;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }
    .issue-card.critical {border-left: 4px solid #f85149;}
    .issue-card.high     {border-left: 4px solid #e3b341;}
    .issue-card.medium   {border-left: 4px solid #d29922;}
    .issue-card.low      {border-left: 4px solid #3fb950;}

    /* Patch cards */
    .patch-card {
        background: #0d1117;
        border: 1px solid #238636;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        transition: all var(--transition-smooth) var(--ease-out-cubic);
    }
    .patch-card:hover {
        box-shadow: 0 12px 32px rgba(56, 211, 137, 0.15);
        transform: translateY(-2px);
    }

    /* Code style */
    code {
        background: #161b22;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85em;
        transition: all var(--transition-fast);
    }
    code:hover {
        background: #1c2128;
        color: #58a6ff;
    }

    /* Chat message styling */
    .chat-user {
        background: #1c2128;
        border: 1px solid #30363d;
        border-radius: 12px 12px 4px 12px;
        padding: 12px 16px;
        margin: 8px 0;
        animation: chatSlideIn 0.4s var(--ease-out-expo);
    }
    .chat-bot {
        background: #162032;
        border: 1px solid #1f6feb;
        border-radius: 12px 12px 12px 4px;
        padding: 12px 16px;
        margin: 8px 0;
        animation: chatSlideIn 0.4s var(--ease-out-expo);
    }
    @keyframes chatSlideIn {
        0% { opacity: 0; transform: translateY(12px); }
        100% { opacity: 1; transform: translateY(0); }
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #238636, #2ea043) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        padding: 12px 28px !important;
        font-size: 1rem !important;
        transition: all var(--transition-smooth) var(--ease-out-cubic) !important;
        position: relative !important;
        overflow: hidden !important;
    }
    .stButton > button::before {
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.15);
        transform: translate(-50%, -50%);
        transition: width var(--transition-smooth), height var(--transition-smooth);
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 32px rgba(46, 160, 67, 0.3) !important;
    }
    .stButton > button:hover::before {
        width: 300px;
        height: 300px;
    }

    /* Input boxes */
    .stTextInput > div > div > input {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        color: #e6edf3 !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
        transition: all var(--transition-normal) var(--ease-out-cubic) !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.1) !important;
        transform: translateY(-1px);
    }

    /* Sidebar */
    .css-1d391kg {background: #161b22 !important;}

    /* Sidebar professional styling */
    section[data-testid="sidebar"] {
        background: #0d1117 !important;
        border-right: 1px solid #21262d !important;
    }
    
    section[data-testid="sidebar"] h2,
    section[data-testid="sidebar"] h3 {
        color: #e6edf3 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
    }
    
    section[data-testid="sidebar"] .stMarkdown {
        animation: sidebarFadeIn 0.52s var(--ease-out-expo) forwards;
    }
    @keyframes sidebarFadeIn {
        0% { opacity: 0; transform: translateX(-12px); }
        100% { opacity: 1; transform: translateX(0); }
    }
    
    /* Checkbox styling in sidebar */
    section[data-testid="sidebar"] .stCheckbox {
        animation: checkboxSlide 0.42s var(--ease-soft) forwards;
    }
    @keyframes checkboxSlide {
        0% { opacity: 0; transform: translateX(-8px); }
        100% { opacity: 1; transform: translateX(0); }
    }
    
    section[data-testid="sidebar"] .stCheckbox label {
        color: #9fb0c4 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 500 !important;
        transition: all var(--transition-normal) var(--ease-out-cubic) !important;
        cursor: pointer !important;
    }
    
    section[data-testid="sidebar"] .stCheckbox:hover label {
        color: #58a6ff !important;
        transform: translateX(2px);
    }
    
    section[data-testid="sidebar"] .stCheckbox input[type="checkbox"] {
        accent-color: #58a6ff !important;
        cursor: pointer !important;
        transition: all var(--transition-fast) !important;
    }
    
    section[data-testid="sidebar"] .stCheckbox input[type="checkbox"]:hover {
        filter: brightness(1.2);
    }
    
    section[data-testid="sidebar"] .stCheckbox input[type="checkbox"]:checked {
        background: #58a6ff !important;
        border-color: #79c0ff !important;
        box-shadow: 0 0 8px rgba(88, 166, 255, 0.4) !important;
    }
    
    /* Sidebar links */
    section[data-testid="sidebar"] a {
        color: #58a6ff !important;
        transition: all var(--transition-normal) var(--ease-out-cubic) !important;
    }
    
    section[data-testid="sidebar"] a:hover {
        color: #79c0ff !important;
        text-decoration: underline !important;
    }
    
    section[data-testid="sidebar"] ul {
        color: #8b949e !important;
    }
    
    section[data-testid="sidebar"] li {
        transition: all var(--transition-normal) var(--ease-out-cubic) !important;
    }
    
    section[data-testid="sidebar"] li:hover {
        color: #d8e8ff !important;
    }
    
    /* Sidebar dividers */
    section[data-testid="sidebar"] hr {
        border-color: #21262d !important;
        margin: 16px 0 !important;
        opacity: 0.5 !important;
    }
    
    section[data-testid="sidebar"] small {
        color: #6e7681 !important;
        font-size: 0.75rem !important;
    }

    /* Score ring container */
    .score-ring-container {
        display: flex;
        justify-content: center;
        margin: 20px 0;
    }

    /* Tag badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 2px;
        position: relative;
        overflow: hidden;
        transition: transform var(--transition-normal) var(--ease-out-cubic), box-shadow var(--transition-normal) var(--ease-out-cubic), border-color var(--transition-normal) var(--ease-out-cubic);
    }
    .badge:hover {
        transform: translateY(-2px) scale(1.03);
        box-shadow: 0 8px 20px rgba(88, 166, 255, 0.16);
    }
    .badge::after {
        content: "";
        position: absolute;
        top: 0;
        left: -130%;
        width: 55%;
        height: 100%;
        pointer-events: none;
        background: linear-gradient(100deg, transparent 0%, rgba(255, 255, 255, 0.22) 45%, transparent 100%);
        transition: left 0.38s var(--ease-out-expo);
    }
    .badge:hover::after {
        left: 130%;
    }
    .badge-critical {background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid #f85149;}
    .badge-high     {background: rgba(227,179,65,0.15); color: #e3b341; border: 1px solid #e3b341;}
    .badge-medium   {background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid #d29922;}
    .badge-low      {background: rgba(63,185,80,0.15);  color: #3fb950; border: 1px solid #3fb950;}
    .badge-safe     {background: rgba(88,166,255,0.15); color: #58a6ff; border: 1px solid #58a6ff;}

    /* Tab hover interaction animation */
    div[data-baseweb="tab-list"] {
        gap: 8px;
    }
    div[data-baseweb="tab-list"] button[role="tab"] {
        position: relative;
        border: 1px solid #30363d !important;
        border-radius: 999px !important;
        background: rgba(22, 27, 34, 0.9) !important;
        color: #9fb0c4 !important;
        padding: 0.45rem 0.95rem !important;
        transition: transform var(--transition-normal) var(--ease-out-cubic), box-shadow var(--transition-normal) var(--ease-out-cubic), border-color var(--transition-normal) var(--ease-out-cubic), color var(--transition-normal) var(--ease-out-cubic);
        overflow: hidden;
    }
    div[data-baseweb="tab-list"] button[role="tab"]::before {
        content: "";
        position: absolute;
        inset: 0;
        opacity: 0;
        pointer-events: none;
        background: linear-gradient(120deg, rgba(88, 166, 255, 0.18), rgba(121, 192, 255, 0.08));
        transition: opacity var(--transition-normal) var(--ease-out-cubic);
    }
    div[data-baseweb="tab-list"] button[role="tab"]::after {
        content: "";
        position: absolute;
        left: 14px;
        right: 14px;
        bottom: 4px;
        height: 2px;
        border-radius: 2px;
        transform: scaleX(0);
        transform-origin: center;
        background: linear-gradient(90deg, #58a6ff, #79c0ff);
        transition: transform var(--transition-normal) var(--ease-out-cubic);
    }
    div[data-baseweb="tab-list"] button[role="tab"]:hover {
        transform: translateY(-2px);
        border-color: #58a6ff !important;
        color: #d8e8ff !important;
        box-shadow: 0 10px 24px rgba(17, 84, 153, 0.28);
    }
    div[data-baseweb="tab-list"] button[role="tab"]:hover::before {
        opacity: 1;
    }
    div[data-baseweb="tab-list"] button[role="tab"]:hover::after {
        transform: scaleX(1);
    }
    div[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] {
        color: #eaf3ff !important;
        border-color: #79c0ff !important;
        box-shadow: 0 0 0 1px rgba(121, 192, 255, 0.32), 0 8px 22px rgba(17, 84, 153, 0.22);
        animation: tabActivePop 0.34s var(--ease-out-expo);
    }
    div[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"]::before,
    div[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"]::after {
        opacity: 1;
        transform: scaleX(1);
    }

    /* Click-open motion for tab content */
    @keyframes tabActivePop {
        0% {
            transform: translateY(0) scale(0.97);
            box-shadow: 0 0 0 0 rgba(121, 192, 255, 0);
        }
        55% {
            transform: translateY(-1px) scale(1.02);
            box-shadow: 0 0 0 4px rgba(121, 192, 255, 0.16);
        }
        100% {
            transform: translateY(0) scale(1);
            box-shadow: 0 0 0 1px rgba(121, 192, 255, 0.32), 0 8px 22px rgba(17, 84, 153, 0.22);
        }
    }
    @keyframes agentPanelReveal {
        0% {
            opacity: 0;
            transform: translateY(16px) scale(0.985);
            filter: saturate(0.85);
        }
        65% {
            opacity: 1;
            transform: translateY(-2px) scale(1.005);
            filter: saturate(1.05);
        }
        100% {
            opacity: 1;
            transform: translateY(0) scale(1);
            filter: saturate(1);
        }
    }

    /* Main dashboard agent tabs */
    .stTabs [data-baseweb="tab-panel"] {
        transform-origin: top center;
        will-change: transform, opacity;
    }
    .stTabs [data-baseweb="tab-panel"]:not([aria-hidden="true"]) {
        animation: agentPanelReveal 0.52s var(--ease-out-expo);
    }

    /* Animate key content containers globally when shown */
    .stTabs [data-baseweb="tab-panel"] .stExpander,
    .stTabs [data-baseweb="tab-panel"] [data-testid="stMetric"],
    .stTabs [data-baseweb="tab-panel"] [data-testid="stAlert"],
    .stTabs [data-baseweb="tab-panel"] [data-testid="stMarkdownContainer"] {
        animation: agentPanelReveal 0.58s var(--ease-out-expo);
        animation-fill-mode: both;
    }
    .stTabs [data-baseweb="tab-panel"] .stExpander:nth-of-type(1),
    .stTabs [data-baseweb="tab-panel"] [data-testid="stMetric"]:nth-of-type(1) {
        animation-delay: 0.03s;
    }
    .stTabs [data-baseweb="tab-panel"] .stExpander:nth-of-type(2),
    .stTabs [data-baseweb="tab-panel"] [data-testid="stMetric"]:nth-of-type(2) {
        animation-delay: 0.06s;
    }
    .stTabs [data-baseweb="tab-panel"] .stExpander:nth-of-type(3),
    .stTabs [data-baseweb="tab-panel"] [data-testid="stMetric"]:nth-of-type(3) {
        animation-delay: 0.09s;
    }
    .stTabs [data-baseweb="tab-panel"] .stExpander:nth-of-type(4),
    .stTabs [data-baseweb="tab-panel"] [data-testid="stMetric"]:nth-of-type(4) {
        animation-delay: 0.12s;
    }

    /* Expandable containers smooth reveal */
    .stExpander {
        animation: expanderSlide 0.42s var(--ease-out-expo) forwards;
    }
    @keyframes expanderSlide {
        0% { opacity: 0; transform: translateY(12px); }
        100% { opacity: 1; transform: translateY(0); }
    }

    @media (prefers-reduced-motion: reduce) {
        .badge,
        .badge::after,
        div[data-baseweb="tab-list"] button[role="tab"],
        div[data-baseweb="tab-list"] button[role="tab"]::before,
        div[data-baseweb="tab-list"] button[role="tab"]::after,
        .stTabs [data-baseweb="tab-panel"],
        .stTabs [data-baseweb="tab-panel"] .stExpander,
        .stTabs [data-baseweb="tab-panel"] [data-testid="stMetric"],
        .stTabs [data-baseweb="tab-panel"] [data-testid="stAlert"],
        .stTabs [data-baseweb="tab-panel"] [data-testid="stMarkdownContainer"],
        .stButton > button,
        .stTextInput > div > div > input {
            transition: none !important;
            animation: none !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# SESSION STATE INITIALIZATION
# Streamlit re-runs the script on every interaction.
# Session state is how we PERSIST data between reruns.
# ============================================
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False

if "results" not in st.session_state:
    st.session_state.results = {}

if "chatbot" not in st.session_state:
    st.session_state.chatbot = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "repo_files" not in st.session_state:
    st.session_state.repo_files = {}

if "repo_info" not in st.session_state:
    st.session_state.repo_info = {}

if "analyzed_url" not in st.session_state:
    st.session_state.analyzed_url = ""
if "time_machine_result" not in st.session_state:
    st.session_state.time_machine_result = None

if "dashboard_open_fx" not in st.session_state:
    st.session_state.dashboard_open_fx = False

if "show_splash" not in st.session_state:
    st.session_state.show_splash = True

if "splash_complete" not in st.session_state:
    st.session_state.splash_complete = False

# ============================================
# SPLASH SCREEN / INTRO ANIMATION
# Mnemonic-style Apple TV opening
# ============================================
if st.session_state.show_splash and not st.session_state.splash_complete:
    st.markdown("""
    <style>
        @keyframes mnemonicReveal {
            0% {
                opacity: 0;
                transform: scale(0.4) rotate(-8deg);
                filter: blur(12px) saturate(0);
            }
            35% {
                opacity: 0.7;
                transform: scale(1.08) rotate(2deg);
                filter: blur(2px) saturate(0.8);
            }
            65% {
                opacity: 1;
                transform: scale(0.98) rotate(-1deg);
                filter: blur(0) saturate(1);
            }
            100% {
                opacity: 1;
                transform: scale(1) rotate(0deg);
                filter: blur(0) saturate(1);
            }
        }
        @keyframes iconFloatIn {
            0% {
                opacity: 0;
                transform: translateY(40px) scale(0.6);
            }
            60% {
                opacity: 1;
                transform: translateY(-8px) scale(1.05);
            }
            100% {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        @keyframes textFadeIn {
            0% {
                opacity: 0;
                letter-spacing: 8px;
            }
            50% {
                opacity: 0.8;
            }
            100% {
                opacity: 1;
                letter-spacing: 1px;
            }
        }
        @keyframes containerDim {
            0% {
                background: rgba(10, 14, 26, 0);
                backdrop-filter: blur(0px);
            }
            40% {
                background: rgba(10, 14, 26, 0.3);
                backdrop-filter: blur(8px);
            }
            100% {
                background: rgba(10, 14, 26, 0.95);
                backdrop-filter: blur(16px);
            }
        }
        
        .splash-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            background: radial-gradient(ellipse at center, #1a2744 0%, #0a0e1a 100%);
            animation: containerDim 0.6s ease-in-out forwards;
            overflow: hidden;
        }
        
        .splash-content {
            text-align: center;
            animation: mnemonicReveal 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        
        .splash-icon {
            font-size: 5.5rem;
            line-height: 1;
            margin-bottom: 24px;
            filter: drop-shadow(0 20px 40px rgba(88, 166, 255, 0.15));
            animation: iconFloatIn 0.55s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
        }
        
        .splash-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 3.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #58a6ff, #bc8cff, #79c0ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            animation: textFadeIn 0.65s ease-out 0.15s forwards;
            opacity: 0;
        }
        
        .splash-subtitle {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1rem;
            color: #8b949e;
            margin-top: 12px;
            animation: textFadeIn 0.7s ease-out 0.25s forwards;
            opacity: 0;
            letter-spacing: 2px;
        }
        
        .splash-dots {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-top: 32px;
            animation: textFadeIn 0.75s ease-out 0.35s forwards;
            opacity: 0;
        }
        
        .splash-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #58a6ff;
            opacity: 0.3;
        }
        .splash-dot:nth-child(1) {
            animation: pulse 0.8s ease-in-out 0.4s infinite;
        }
        .splash-dot:nth-child(2) {
            animation: pulse 0.8s ease-in-out 0.52s infinite;
        }
        .splash-dot:nth-child(3) {
            animation: pulse 0.8s ease-in-out 0.64s infinite;
        }
        
        @keyframes pulse {
            0%, 100% {
                opacity: 0.3;
                transform: scale(1);
            }
            50% {
                opacity: 1;
                transform: scale(1.2);
            }
        }
        
        .splash-glow {
            position: absolute;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(88, 166, 255, 0.08), transparent);
            border-radius: 50%;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            pointer-events: none;
            animation: glowPulse 2s ease-in-out infinite;
        }
        
        @keyframes glowPulse {
            0%, 100% {
                transform: translate(-50%, -50%) scale(0.8);
                opacity: 0.4;
            }
            50% {
                transform: translate(-50%, -50%) scale(1.2);
                opacity: 0.2;
            }
        }
    </style>
    
    <div class="splash-container">
        <div class="splash-glow"></div>
        <div class="splash-content">
            <div class="splash-icon">🧠</div>
            <h1 class="splash-title">RepoMind</h1>
            <p class="splash-subtitle">AI-POWERED INTELLIGENCE</p>
            <div class="splash-dots">
                <div class="splash-dot"></div>
                <div class="splash-dot"></div>
                <div class="splash-dot"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Auto-transition after animation completes
    time.sleep(1.4)
    st.session_state.splash_complete = True
    st.session_state.show_splash = False
    st.rerun()

# ============================================
# HERO SECTION
# ============================================
st.markdown("""
<div class="hero-banner">
    <p class="hero-title">🧠 RepoMind</p>
    <p class="hero-tagline">AI-Powered Repository Intelligence Platform</p>
    <div class="hero-badges">
        <span class="badge badge-safe">🔍 Code Review</span>
        <span class="badge badge-critical">🔒 Security</span>
        <span class="badge badge-medium">📄 Documentation</span>
        <span class="badge badge-high">📦 Dependencies</span>
        <span class="badge badge-low">🔧 Auto-Fix</span>
        <span class="badge badge-safe">🗺️ Risk Heatmap</span>
        <span class="badge badge-safe">🏗️ Architecture</span>
        <span class="badge badge-safe">🤖 AI Chatbot</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================
# SIDEBAR - Configuration Panel
# ============================================
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("---")

    # Agent selection
    st.markdown("### 🤖 Select Agents")
    run_code_review  = st.checkbox("Code Review Agent",    value=True)
    run_security     = st.checkbox("Security Agent",       value=True)
    run_docs         = st.checkbox("Documentation Agent",  value=True)
    run_deps         = st.checkbox("Dependency Agent",     value=True)
    run_bugfix       = st.checkbox("Bug Fix Agent",      value=True)
    run_heatmap      = st.checkbox("Risk Heatmap Agent", value=True)
    run_arch         = st.checkbox("Architecture Agent", value=True)
    run_chatbot_init = st.checkbox("Chatbot Agent",      value=True)
    run_time_machine  = st.checkbox("Time Machine Agent",  value=True)

    st.markdown("---")

    # Links
    st.markdown("### 🔗 Quick Links")
    st.markdown("- [Get Gemini Key (FREE)](https://aistudio.google.com)")
    st.markdown("- [Get GitHub Token](https://github.com/settings/tokens)")
    st.markdown("- [GitHub: RepoMind](https://github.com)")

    st.markdown("---")
    st.markdown(f"<small>RepoMind v1.0.0 | Built with ❤️</small>", unsafe_allow_html=True)


# ============================================
# MAIN PANEL - Input Section
# ============================================
if not st.session_state.analysis_complete:

    st.markdown("### 🔗 Enter GitHub Repository URL")

    col1, col2 = st.columns([3, 1])

    with col1:
        github_url = st.text_input(
            "GitHub URL",
            placeholder="https://github.com/owner/repository",
            label_visibility="collapsed"
        )

    with col2:
        analyze_button = st.button("🚀 Analyze Repository", use_container_width=True)

    # Example repos for easy testing
    st.markdown("**Quick test with these repos:**")
    example_cols = st.columns(4)
    examples = [
        ("Flask", "https://github.com/pallets/flask"),
        ("FastAPI", "https://github.com/tiangolo/fastapi"),
        ("Django", "https://github.com/django/django"),
        ("Requests", "https://github.com/psf/requests"),
    ]
    for i, (name, url) in enumerate(examples):
        if example_cols[i].button(f"Try {name}", use_container_width=True):
            github_url = url
            analyze_button = True


    # ==========================================
    # ANALYSIS EXECUTION
    # This runs when user clicks "Analyze"
    # ==========================================
    if analyze_button and github_url:

        # Validate inputs
        if not os.getenv("GEMINI_API_KEY"):
            st.error("⚠️ GEMINI_API_KEY is not set. Add it to your .env file.")
            st.stop()

        if not os.getenv("GITHUB_TOKEN"):
            st.error("⚠️ GITHUB_TOKEN is not set. Add it to your .env file.")
            st.stop()

        if "github.com" not in github_url:
            st.error("⚠️ Please enter a valid GitHub URL")
            st.stop()

        # ---- Start Analysis ----
        progress_container = st.container()
        analysis_start = time.perf_counter()

        with progress_container:
            head_left, head_right = st.columns([4, 1])
            with head_left:
                st.markdown("### ⚡ Analysis in Progress...")
            with head_right:
                elapsed_text = st.empty()
                elapsed_text.markdown("**⏱️ 0.0s**")

            repo_open_text = st.empty()
            repo_open_text.caption("📂 Repository open time: calculating...")

            def _update_elapsed() -> None:
                elapsed_text.markdown(f"**⏱️ {time.perf_counter() - analysis_start:.1f}s**")

            progress_bar = st.progress(0)
            status_text  = st.empty()

            # File loading animation during analysis
            st.markdown("""
            <style>
                @keyframes fileSlide {
                    0% { transform: translateY(-100%); opacity: 0; }
                    20% { opacity: 1; }
                    80% { opacity: 1; }
                    100% { transform: translateY(100%); opacity: 0; }
                }
                @keyframes filePulse {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                }
                @keyframes docStack {
                    0% { transform: translateX(0) rotate(0deg); opacity: 0.6; }
                    50% { transform: translateX(8px) rotate(2deg); opacity: 0.8; }
                    100% { transform: translateX(0) rotate(0deg); opacity: 0.6; }
                }
                
                .loading-animation {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    margin: 24px 0;
                    gap: 16px;
                }
                
                .file-icon {
                    width: 60px;
                    height: 80px;
                    background: linear-gradient(135deg, #58a6ff, #79c0ff);
                    border-radius: 6px;
                    position: relative;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 12px 32px rgba(88, 166, 255, 0.2);
                    animation: filePulse 2s ease-in-out infinite;
                }
                
                .file-icon::before {
                    content: "";
                    position: absolute;
                    width: 3px;
                    height: 20px;
                    background: rgba(255, 255, 255, 0.4);
                    border-radius: 2px;
                    animation: fileSlide 1.6s ease-in-out infinite;
                }
                
                .file-icon::after {
                    content: "";
                    position: absolute;
                    width: 40px;
                    height: 50px;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    border-radius: 4px;
                    pointer-events: none;
                }
                
                .stack-files {
                    position: relative;
                    width: 80px;
                    height: 70px;
                }
                
                .doc {
                    position: absolute;
                    width: 50px;
                    height: 65px;
                    background: #161b22;
                    border: 1.5px solid #30363d;
                    border-radius: 4px;
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                    padding: 8px;
                    box-sizing: border-box;
                }
                
                .doc::before,
                .doc::after {
                    content: "";
                    height: 2px;
                    background: #30363d;
                    border-radius: 1px;
                }
                
                .doc:nth-child(1) {
                    left: 0;
                    top: 0;
                    animation: docStack 1.8s ease-in-out infinite;
                }
                .doc:nth-child(2) {
                    left: 12px;
                    top: 8px;
                    animation: docStack 1.8s ease-in-out 0.2s infinite;
                }
                .doc:nth-child(3) {
                    left: 24px;
                    top: 16px;
                    animation: docStack 1.8s ease-in-out 0.4s infinite;
                }
                
                .loading-text {
                    color: #8b949e;
                    font-size: 0.9rem;
                    font-family: 'Space Grotesk', sans-serif;
                    letter-spacing: 0.5px;
                }
                
                .loading-dot {
                    display: inline-block;
                    width: 4px;
                    height: 4px;
                    background: #58a6ff;
                    border-radius: 50%;
                    animation: dotPulse 1.4s ease-in-out infinite;
                }
                .loading-dot:nth-child(2) { animation-delay: 0.2s; }
                .loading-dot:nth-child(3) { animation-delay: 0.4s; }
                
                @keyframes dotPulse {
                    0%, 100% { opacity: 0.4; transform: scale(0.8); }
                    50% { opacity: 1; transform: scale(1.2); }
                }
            </style>
            
            <div class="loading-animation">
                <div class="file-icon"></div>
                <div class="stack-files">
                    <div class="doc"></div>
                    <div class="doc"></div>
                    <div class="doc"></div>
                </div>
                <div>
                    <div class="loading-text">Analyzing<span class="loading-dot"></span><span class="loading-dot"></span><span class="loading-dot"></span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            results = {}

            try:
                # Step 1: Fetch repo files
                fetch_start = time.perf_counter()
                status_text.markdown("**📥 Fetching repository files...**")
                progress_bar.progress(5)
                _update_elapsed()

                repo_info = get_repo_info(github_url)
                st.session_state.repo_info = repo_info

                if "error" in repo_info:
                    st.error(f"❌ Could not access repository: {repo_info['error']}")
                    st.stop()

                def _on_fetch_progress(file_count: int, dirs_scanned: int, api_calls: int) -> None:
                    _update_elapsed()
                    status_text.markdown(
                        "**📥 Fetching repository files... "
                        f"{file_count} files collected | {dirs_scanned} folders scanned | "
                        f"{api_calls} GitHub API calls**"
                    )
                    fetch_progress = 5 + min(9, file_count // 6 + dirs_scanned // 10)
                    progress_bar.progress(fetch_progress)

                files = get_repo_files(
                    github_url,
                    max_files=70,
                    max_dirs=90,
                    progress_callback=_on_fetch_progress,
                )
                st.session_state.repo_files = files
                st.session_state.analyzed_url = github_url
                st.session_state.chat_history = []

                if "ERROR" in files:
                    st.error(f"❌ {files['ERROR']}")
                    st.stop()

                requirements = get_requirements_txt(github_url)

                repo_open_seconds = time.perf_counter() - fetch_start
                repo_open_text.caption(f"📂 Repository open time: {repo_open_seconds:.1f}s")

                _update_elapsed()
                status_text.markdown(f"**✅ Fetched {len(files)} files from {repo_info['name']}**")
                progress_bar.progress(15)
                _update_elapsed()
                time.sleep(0.3)

                # Step 2: Code Review Agent
                if run_code_review:
                    status_text.markdown("**🔍 Running Code Review Agent...**")
                    results["code_review"] = run_code_review_agent(files)
                    progress_bar.progress(30)
                    _update_elapsed()
                    status_text.markdown(f"**✅ Code Review: Found {len(results['code_review'].get('issues', []))} issues**")
                    time.sleep(0.2)

                # Step 3: Security Agent
                if run_security:
                    status_text.markdown("**🔒 Running Security Agent...**")
                    results["security"] = run_security_agent(files)
                    progress_bar.progress(45)
                    _update_elapsed()
                    status_text.markdown(f"**✅ Security: Found {results['security'].get('total_found', 0)} vulnerabilities**")
                    time.sleep(0.2)

                # Step 4: Documentation Agent
                if run_docs:
                    status_text.markdown("**📄 Running Documentation Agent...**")
                    results["documentation"] = run_documentation_agent(files)
                    progress_bar.progress(55)
                    _update_elapsed()
                    status_text.markdown(f"**✅ Documentation: Score {results['documentation'].get('score', 0)}/100**")
                    time.sleep(0.2)

                # Step 5: Dependency Agent
                if run_deps:
                    status_text.markdown("**📦 Running Dependency Agent...**")
                    results["dependency"] = run_dependency_agent(files, requirements)
                    progress_bar.progress(65)
                    _update_elapsed()
                    status_text.markdown(f"**✅ Dependencies: {results['dependency'].get('total_packages', 0)} packages analyzed**")
                    time.sleep(0.2)

                # Step 6: Bug Fix Agent
                if run_bugfix and "security" in results and "code_review" in results:
                    status_text.markdown("**🔧 Running Bug Fix Agent...**")
                    results["bug_fix"] = run_bug_fix_agent(
                        files,
                        results.get("security", {}),
                        results.get("code_review", {}),
                    )
                    progress_bar.progress(75)
                    _update_elapsed()
                    status_text.markdown(f"**✅ Bug Fix: Generated {results['bug_fix'].get('stats', {}).get('total_patches', 0)} patches**")
                    time.sleep(0.2)

                # Step 7: Risk Heatmap Agent
                if run_heatmap and "security" in results and "code_review" in results:
                    status_text.markdown("**🗺️ Running Risk Heatmap Agent...**")
                    results["risk_heatmap"] = run_risk_heatmap_agent(
                        files,
                        results.get("security", {}),
                        results.get("code_review", {}),
                        results.get("dependency", {}),
                    )
                    progress_bar.progress(85)
                    _update_elapsed()
                    status_text.markdown(f"**✅ Risk Heatmap: Overall risk {results['risk_heatmap'].get('overall_risk_score', 0)}/100**")
                    time.sleep(0.2)

                # Step 8: Architecture Agent
                if run_arch:
                    status_text.markdown("**🏗️ Running Architecture Agent...**")
                    results["architecture"] = run_architecture_agent(files, repo_info)
                    progress_bar.progress(93)
                    _update_elapsed()
                    status_text.markdown("**✅ Architecture diagram generated!**")
                    time.sleep(0.2)

                # Step 9: Initialize Chatbot
                if run_chatbot_init:
                    status_text.markdown("**🤖 Initializing Repository Chatbot...**")
                    chatbot = RepoChatbot()
                    chatbot.index_repository(
                    files,
                    results,
                    time_machine_result=st.session_state.get("time_machine_result"),
                   )
                    st.session_state.chatbot = chatbot
                    progress_bar.progress(97)
                    _update_elapsed()
                    status_text.markdown("**✅ Chatbot ready! Ask me anything about the repo.**")
                if run_time_machine:
                    status_text.markdown("**⏳ Running Time Machine Agent...**")
                    tm_result = run_time_machine_agent(github_url, max_commits=12)
                    st.session_state.time_machine_result = tm_result
                    progress_bar.progress(100)
                    _update_elapsed()
                    if tm_result.get("error"):
                        status_text.markdown(f"**⚠️ Time Machine: {tm_result['error'][:80]}**")
                    else:
                        status_text.markdown(f"**✅ Time Machine: Analyzed {len(tm_result.get('commits', []))} commits!**")

                # ---- Save results and show dashboard ----
                st.session_state.results = results
                st.session_state.analysis_complete = True
                st.session_state.dashboard_open_fx = True

                time.sleep(0.5)
                st.rerun()  # Refresh to show dashboard

            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                st.exception(e)  # Show full traceback for debugging


# ============================================
# DASHBOARD - Show results after analysis
# ============================================
if False and st.session_state.analysis_complete:

    results   = st.session_state.results
    repo_info = st.session_state.repo_info

    # ---- Repo Header ----
    st.markdown(f"""
    <div style="background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <h2 style="margin:0; color: #58a6ff;">📦 {repo_info.get('name', 'Repository')}</h2>
        <p style="color: #8b949e; margin: 4px 0;">{repo_info.get('description', '')}</p>
        <p style="color: #8b949e; font-size: 0.85rem; margin: 0;">
            ⭐ {repo_info.get('stars', 0)} stars  |  
            🍴 {repo_info.get('forks', 0)} forks  |  
            ⚠️ {repo_info.get('open_issues', 0)} open issues  |  
            🔤 {repo_info.get('language', 'Unknown')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ---- RepoScore (the "wow" single number) ----
    _display_repo_score(results)

    # ---- Agent Result Tabs ----
    tabs = st.tabs([
        "🔍 Code Review",
        "🔒 Security",
        "📄 Docs",
        "📦 Dependencies",
        "🔧 Auto-Fix",
        "🗺️ Risk Heatmap",
        "🏗️ Architecture",
        "🤖 Chatbot",
        "⏳ Time Machine",
    ])

    # TAB 1: Code Review
    with tabs[0]:
        _show_code_review(results.get("code_review", {}))

    # TAB 2: Security
    with tabs[1]:
        _show_security(results.get("security", {}))

    # TAB 3: Documentation
    with tabs[2]:
        _show_documentation(results.get("documentation", {}))

    # TAB 4: Dependencies
    with tabs[3]:
        _show_dependencies(results.get("dependency", {}))

    # TAB 5: Bug Fix
    with tabs[4]:
        _show_bug_fixes(results.get("bug_fix", {}))

    # TAB 6: Risk Heatmap
    with tabs[5]:
        _show_risk_heatmap(results.get("risk_heatmap", {}))

    # TAB 7: Architecture
    with tabs[6]:
        _show_architecture(results.get("architecture", {}))

    # TAB 8: Chatbot
    with tabs[7]:
        _show_chatbot()
    with tabs[8]:
        show_time_machine(st.session_state.get("time_machine_result") or {})
    # ---- PDF Download ----
    st.markdown("---")
    st.markdown("### 📥 Download Report")
    col_pdf1, col_pdf2, col_pdf3 = st.columns([1, 1, 2])
    with col_pdf1:
        if st.button("📄 Generate PDF Report", use_container_width=True):
            with st.spinner("📄 Generating PDF..."):
                try:
                    pdf_bytes = generate_repomind_report(
                        st.session_state.results,
                        st.session_state.repo_info
                    )
                    repo_name = st.session_state.repo_info.get("name","repo")
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"repomind_{repo_name}_report.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                    st.success("✅ PDF ready! Click Download PDF above.")
                except Exception as e:
                    st.error(f"❌ PDF error: {str(e)}")

    _show_pr_comment_section(results, repo_info) 
     # ---- Reset Button ----
    st.markdown("---")
    if st.button("🔄 Analyze Another Repository"):
        st.session_state.analysis_complete = False
        st.session_state.results           = {}
        st.session_state.chatbot           = None
        st.session_state.chat_history      = []
        st.session_state.repo_files        = {}
        st.session_state.repo_info         = {}
        st.rerun()


# ============================================
# DISPLAY FUNCTIONS
# Each function renders one tab of the dashboard
# ============================================

def _show_agent_pipeline(results: dict):
    """Shows the agent collaboration pipeline with live results."""

    sec_count   = results.get("security",{}).get("total_found", 0)
    cr_count    = len(results.get("code_review",{}).get("issues", []))
    patch_count = results.get("bug_fix",{}).get("stats",{}).get("total_patches", 0)
    risk_score  = results.get("risk_heatmap",{}).get("overall_risk_score", 0)

    scores = [results.get(k,{}).get("score") for k in
              ["code_review","security","documentation","dependency"]]
    scores = [s for s in scores if s is not None]
    repo_score = int(sum(scores)/len(scores)) if scores else 0

    sc = ("#3fb950" if repo_score>=80 else
          "#d29922" if repo_score>=60 else "#f85149")

    st.markdown(f"""
    <div style='background:#161b22;border:1px solid #30363d;
    border-radius:12px;padding:18px 20px;margin:16px 0;'>
        <div style='color:#8b949e;font-size:0.78rem;font-weight:600;
        letter-spacing:1px;margin-bottom:12px;'>
            🤖 &nbsp; AGENT COLLABORATION PIPELINE
        </div>
        <div style='display:flex;align-items:center;gap:6px;
        flex-wrap:wrap;justify-content:center;'>
            <div style='text-align:center;'>
                <div style='background:#0d1117;border:1px solid #58a6ff;
                color:#58a6ff;padding:8px 14px;border-radius:8px;
                font-size:0.82rem;font-weight:600;'>📥 GitHub Repo</div>
                <div style='color:#8b949e;font-size:0.7rem;margin-top:3px;'>Input</div>
            </div>
            <div style='color:#30363d;font-size:1.2rem;'>→</div>
            <div style='text-align:center;'>
                <div style='background:#0d1117;border:1px solid #3fb950;
                color:#3fb950;padding:8px 14px;border-radius:8px;
                font-size:0.82rem;font-weight:600;'>🔍 Code Review</div>
                <div style='color:#3fb950;font-size:0.7rem;margin-top:3px;'>{cr_count} issues</div>
            </div>
            <div style='color:#30363d;font-size:1.2rem;'>→</div>
            <div style='text-align:center;'>
                <div style='background:#0d1117;border:1px solid #f85149;
                color:#f85149;padding:8px 14px;border-radius:8px;
                font-size:0.82rem;font-weight:600;'>🔒 Security</div>
                <div style='color:#f85149;font-size:0.7rem;margin-top:3px;'>{sec_count} vulns</div>
            </div>
            <div style='color:#30363d;font-size:1.2rem;'>→</div>
            <div style='text-align:center;'>
                <div style='background:#0d1117;border:1px solid #e3b341;
                color:#e3b341;padding:8px 14px;border-radius:8px;
                font-size:0.82rem;font-weight:600;'>🔧 Auto-Fix</div>
                <div style='color:#e3b341;font-size:0.7rem;margin-top:3px;'>{patch_count} patches</div>
            </div>
            <div style='color:#30363d;font-size:1.2rem;'>→</div>
            <div style='text-align:center;'>
                <div style='background:#0d1117;border:1px solid #bc8cff;
                color:#bc8cff;padding:8px 14px;border-radius:8px;
                font-size:0.82rem;font-weight:600;'>🗺️ Risk Heatmap</div>
                <div style='color:#bc8cff;font-size:0.7rem;margin-top:3px;'>risk: {risk_score}/100</div>
            </div>
            <div style='color:#30363d;font-size:1.2rem;'>→</div>
            <div style='text-align:center;'>
                <div style='background:#0d1117;
                border:2px solid {sc};color:{sc};
                padding:8px 14px;border-radius:8px;
                font-size:0.9rem;font-weight:700;'>📊 {repo_score}/100</div>
                <div style='color:#8b949e;font-size:0.7rem;margin-top:3px;'>RepoScore™</div>
            </div>
        </div>
        <div style='color:#8b949e;font-size:0.72rem;text-align:center;
        margin-top:10px;border-top:1px solid #21262d;padding-top:8px;'>
            ↑ Agents collaborate in sequence — each feeds results into the next
        </div>
    </div>
    """, unsafe_allow_html=True)
def _display_repo_score(results: dict):
    _show_agent_pipeline(results)
    """Display the overall RepoScore and key metrics."""

    # Calculate RepoScore from all agent scores
    scores = []
    if "code_review" in results:
        scores.append(results["code_review"].get("score", 70))
    if "security" in results:
        scores.append(results["security"].get("score", 100))
    if "documentation" in results:
        scores.append(results["documentation"].get("score", 50))
    if "dependency" in results:
        scores.append(results["dependency"].get("score", 100))

    repo_score = int(sum(scores) / len(scores)) if scores else 70

    # Determine label
    if repo_score >= 80:
        score_color = "#3fb950"
        score_label = "Excellent"
        score_emoji = "🟢"
    elif repo_score >= 60:
        score_color = "#d29922"
        score_label = "Good"
        score_emoji = "🟡"
    elif repo_score >= 40:
        score_color = "#e3b341"
        score_label = "Needs Work"
        score_emoji = "🟠"
    else:
        score_color = "#f85149"
        score_label = "Critical"
        score_emoji = "🔴"

    # Create gauge chart using plotly
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=repo_score,
        title={"text": "RepoScore™", "font": {"size": 20, "color": "#e6edf3"}},
        number={"font": {"size": 48, "color": score_color}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
            "bar":  {"color": score_color},
            "bgcolor": "#161b22",
            "bordercolor": "#30363d",
            "steps": [
                {"range": [0,  40], "color": "rgba(248,81,73,0.2)"},
                {"range": [40, 60], "color": "rgba(227,179,65,0.2)"},
                {"range": [60, 80], "color": "rgba(210,153,34,0.2)"},
                {"range": [80, 100],"color": "rgba(63,185,80,0.2)"},
            ],
            "threshold": {
                "line":  {"color": score_color, "width": 4},
                "thickness": 0.75,
                "value": repo_score
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        height=250,
        margin=dict(t=40, b=0, l=40, r=40),
        font={"color": "#e6edf3"},
    )

    # Layout: gauge + 4 metrics
    col_gauge, col_metrics = st.columns([1, 2])

    with col_gauge:
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<h3 style='text-align:center; color:{score_color};'>{score_emoji} {score_label}</h3>", unsafe_allow_html=True)

    with col_metrics:
        st.markdown("### 📊 Agent Scores")
        m1, m2, m3, m4 = st.columns(4)

        with m1:
            score = results.get("code_review", {}).get("score", "N/A")
            st.metric("Code Review", f"{score}/100")
        with m2:
            score = results.get("security", {}).get("score", "N/A")
            st.metric("Security", f"{score}/100")
        with m3:
            score = results.get("documentation", {}).get("score", "N/A")
            st.metric("Docs", f"{score}/100")
        with m4:
            score = results.get("dependency", {}).get("score", "N/A")
            st.metric("Dependencies", f"{score}/100")

        # Summary stats
        st.markdown("---")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            count = len(results.get("code_review", {}).get("issues", []))
            st.metric("Code Issues", count)
        with s2:
            count = results.get("security", {}).get("total_found", 0)
            st.metric("Vulnerabilities", count)
        with s3:
            count = len(results.get("bug_fix", {}).get("patches", []))
            st.metric("Auto-Patches", count)
        with s4:
            count = len(results.get("dependency", {}).get("vulnerabilities", []))
            st.metric("Vuln Packages", count)


AGENT_GUIDES = {
    "code_review": {
        "title": "Code Review Agent",
        "what": "Automatically reviews code like a senior software engineer to catch quality and performance issues early.",
        "why": "Manual reviews are slow, depend on developer availability, and may miss issues. AI gives consistent checks for every analysis run.",
        "tasks": [
            "Analyze repository source files as if they were PR changes",
            "Detect inefficient logic patterns and code smells",
            "Identify bad coding practices",
            "Suggest concrete improvements and refactoring ideas",
            "Score quality with clear issue-level evidence",
        ],
        "how": [
            "Get repository files through GitHub API helper",
            "Select representative code files",
            "Run local AST/heuristic checks",
            "Send selected code to LLM for deeper review",
            "Return structured findings with severity and fixes",
        ],
        "tools": "Gemini/OpenAI compatible LLM, Python AST parser, local heuristics, optional pylint integration",
        "keys": "GITHUB_TOKEN, GEMINI_API_KEY",
    },
    "security": {
        "title": "Security Agent",
        "what": "Scans code for security vulnerabilities using pattern matching and optional AI deep analysis.",
        "why": "Security defects can cause data exposure, account compromise, and production incidents if not caught early.",
        "tasks": [
            "Detect hardcoded secrets and unsafe runtime patterns",
            "Find injection and command execution risks",
            "Assign severity and overall repository risk level",
            "Recommend targeted remediations",
            "Provide file and line-level evidence",
        ],
        "how": [
            "Parse source files and apply security regex rules",
            "Aggregate findings by severity",
            "Run AI deep analysis on highest-risk files",
            "Compute normalized security score",
            "Return vulnerability report with fixes",
        ],
        "tools": "Regex engine, LLM deep analysis, risk scoring",
        "keys": "GITHUB_TOKEN, GEMINI_API_KEY",
    },
    "documentation": {
        "title": "Documentation Agent",
        "what": "Evaluates code and README documentation quality and identifies missing docs.",
        "why": "Poor docs increase onboarding time and make maintenance harder across teams.",
        "tasks": [
            "Find undocumented functions and classes",
            "Measure documentation coverage",
            "Assess README completeness",
            "Generate candidate docstrings",
            "Provide actionable documentation improvements",
        ],
        "how": [
            "Parse Python files via AST",
            "Track documented vs undocumented symbols",
            "Analyze README section coverage",
            "Optionally generate docstrings with LLM",
            "Compute final docs quality score",
        ],
        "tools": "AST parser, README section analyzer, optional LLM generation",
        "keys": "GITHUB_TOKEN, GEMINI_API_KEY (for docstring generation)",
    },
    "dependencies": {
        "title": "Dependency Agent",
        "what": "Finds dependency risks by reading dependency manifests and checking known vulnerabilities.",
        "why": "Outdated or vulnerable dependencies are a major source of security and reliability incidents.",
        "tasks": [
            "Read requirements and manifest files",
            "Check Python dependencies against OSV/PyPI",
            "List vulnerable or outdated packages",
            "Summarize ecosystem coverage and limitations",
            "Provide upgrade recommendations",
        ],
        "how": [
            "Extract dependencies from requirements.txt/package.json/csproj/pom",
            "Query vulnerability/version services where supported",
            "Score dependency health",
            "Return package-by-package status table",
            "Generate remediation tips",
        ],
        "tools": "OSV API, PyPI API, manifest parsers, optional LLM recommendations",
        "keys": "GITHUB_TOKEN, GEMINI_API_KEY (optional for recommendations)",
    },
    "bug_fix": {
        "title": "Bug Fix Agent",
        "what": "Generates suggested patches for security and high-priority code issues.",
        "why": "Teams can move faster when the system proposes concrete fixes instead of only listing problems.",
        "tasks": [
            "Prioritize fixable high-impact findings",
            "Produce minimal patch suggestions",
            "Explain each fix and why it helps",
            "Separate security and quality patch types",
            "Return patch stats for implementation planning",
        ],
        "how": [
            "Read issue context from security/code review outputs",
            "Build focused prompts around affected code snippets",
            "Generate corrected code suggestions",
            "Extract explanation + patch blocks",
            "Publish patch list with priority",
        ],
        "tools": "LLM patch generation, structured patch parser",
        "keys": "GITHUB_TOKEN, GEMINI_API_KEY",
    },
    "risk_heatmap": {
        "title": "Risk Heatmap Agent",
        "what": "Builds a file and module level risk profile with weighted scoring.",
        "why": "Heatmaps show where to focus engineering effort first instead of scanning long issue lists.",
        "tasks": [
            "Compute file-level risk scores",
            "Aggregate risk by module/folder",
            "Combine security, complexity, and lint signals",
            "Highlight top risky files",
            "Visualize risk distribution",
        ],
        "how": [
            "Join security and code-review findings",
            "Estimate complexity and lint burden",
            "Apply weighted risk formula",
            "Rank files/modules by risk",
            "Return chart-friendly structures",
        ],
        "tools": "Local scoring heuristics, weighted risk model, visualization-ready outputs",
        "keys": "GITHUB_TOKEN",
    },
    "architecture": {
        "title": "Architecture Agent",
        "what": "Generates architecture summaries, components, and diagrams from repository structure and imports.",
        "why": "A clear architecture view accelerates onboarding and helps identify design bottlenecks.",
        "tasks": [
            "Map components and top-level modules",
            "Extract import dependency edges",
            "Detect likely tech stack",
            "Generate Mermaid architecture diagram",
            "Provide architecture recommendations",
        ],
        "how": [
            "Build folder tree from repository files",
            "Parse language-specific import statements",
            "Infer high-level components",
            "Generate visual graph connections",
            "Summarize design with AI narrative",
        ],
        "tools": "Import parser, Mermaid generator, LLM architecture summarizer",
        "keys": "GITHUB_TOKEN, GEMINI_API_KEY",
    },
}


def _render_agent_guide(agent_key: str):
    guide = AGENT_GUIDES.get(agent_key)
    if not guide:
        return

    with st.expander("📘 Agent Details", expanded=False):
        st.markdown(f"**{guide['title']}**")
        st.markdown(f"**What it does:** {guide['what']}")
        st.markdown(f"**Why it matters:** {guide['why']}")
        st.markdown("**Tasks performed:**")
        for task in guide["tasks"]:
            st.markdown(f"- {task}")
        st.markdown("**How it works:**")
        for idx, step in enumerate(guide["how"], start=1):
            st.markdown(f"{idx}. {step}")
        st.markdown(f"**Tools:** {guide['tools']}")
        st.markdown(f"**API keys needed:** {guide['keys']}")


def _group_issues_by_file(issues: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for issue in issues:
        file_path = issue.get("file", "Unknown")
        grouped.setdefault(file_path, []).append(issue)
    return grouped


def _parent_folder(file_path: str) -> str:
    if "/" not in file_path:
        return "root"
    return file_path.rsplit("/", 1)[0]


def _show_code_review(data: dict):
    """Display Code Review Agent results."""
    if not data:
        st.info("Code Review Agent was not run.")
        return

    _render_agent_guide("code_review")

    st.markdown(f"### 🔍 Code Review Results")
    st.markdown(data.get("summary", ""))

    c1, c2, c3 = st.columns(3)
    c1.metric("Files Detected", data.get("files_detected", 0))
    c2.metric("Files Reviewed", data.get("files_reviewed", 0))
    c3.metric("Total Findings", data.get("total_findings", len(data.get("issues", []))))

    c4, c5, c6 = st.columns(3)
    c4.metric("Folders Detected", data.get("folder_count", 0))
    c5.metric("Source Files", data.get("source_files_detected", 0))
    c6.metric("Files + Folders", data.get("total_items", 0))

    detected_files = data.get("detected_file_list", [])
    reviewed_files = data.get("reviewed_file_list", [])
    detected_folders = data.get("detected_folder_list", [])

    if detected_files:
        with st.expander(f"📁 Files Detected ({len(detected_files)})", expanded=False):
            for path in detected_files[:200]:
                st.markdown(f"- `{path}`")

    if detected_folders:
        with st.expander(f"🗂️ Folders Detected ({len(detected_folders)})", expanded=False):
            for folder in detected_folders[:200]:
                st.markdown(f"- `{folder}`")

    if reviewed_files:
        with st.expander(f"👀 Files Reviewed ({len(reviewed_files)})", expanded=True):
            for path in reviewed_files:
                st.markdown(f"- `{path}`")

    highlights = data.get("highlights", [])
    if highlights:
        st.markdown("#### Worst Scoring Files")
        for path, score in highlights:
            st.markdown(f"- `{path}`: **{score}/100**")

    issues = data.get("issues", [])
    if not issues:
        st.success("✅ No issues found!")
        return

    st.markdown("#### Findings Summary")
    severity_counts = {
        "HIGH": sum(1 for issue in issues if issue.get("severity", "").upper() == "HIGH"),
        "MEDIUM": sum(1 for issue in issues if issue.get("severity", "").upper() == "MEDIUM"),
        "LOW": sum(1 for issue in issues if issue.get("severity", "").upper() == "LOW"),
    }
    s1, s2, s3 = st.columns(3)
    s1.metric("High", severity_counts["HIGH"])
    s2.metric("Medium", severity_counts["MEDIUM"])
    s3.metric("Low", severity_counts["LOW"])

    # Filter by severity
    severity_filter = st.selectbox(
        "Filter by severity",
        ["All", "HIGH", "MEDIUM", "LOW"],
        key="cr_filter"
    )

    filtered = issues if severity_filter == "All" else [
        i for i in issues if i.get("severity", "").upper() == severity_filter
    ]

    st.markdown(f"Showing **{len(filtered)}** issues")

    grouped_issues = _group_issues_by_file(filtered[:30])
    for file_path, file_issues in grouped_issues.items():
        folder = _parent_folder(file_path)
        with st.expander(f"📄 {file_path} ({len(file_issues)} finding{'s' if len(file_issues) != 1 else ''})", expanded=False):
            st.markdown(f"**File:** `{file_path}`")
            st.markdown(f"**Folder:** `{folder}`")
            st.markdown(f"**Total findings in this file:** {len(file_issues)}")
            st.markdown("---")

            for index, issue in enumerate(file_issues, start=1):
                severity = issue.get("severity", "LOW").upper()
                severity_badge = {
                    "HIGH": "🔴 HIGH",
                    "MEDIUM": "🟡 MEDIUM",
                    "LOW": "🟢 LOW",
                }.get(severity, severity)

                st.markdown(f"**Issue {index}:** {severity_badge}")
                st.markdown(f"**Location:** line `{issue.get('line', 'Unknown')}`")
                st.markdown(f"**Issue:** {issue.get('issue', 'Issue')}")
                st.markdown(f"**Description:** {issue.get('description', '')}")
                if issue.get("fix"):
                    st.markdown(f"**Suggestion:** {issue.get('fix', '')}")
                if issue.get("original_code"):
                    st.markdown("**Current code block:**")
                    st.code(issue.get("original_code", ""), language="python")
                if issue.get("suggested_code"):
                    st.markdown("**Suggested optimized code:**")
                    st.code(issue.get("suggested_code", ""), language="python")
                st.markdown(f"**Source:** {issue.get('source', 'Unknown')}")
                if index != len(file_issues):
                    st.markdown("---")


def _show_security(data: dict):
    """Display Security Agent results."""
    if not data:
        st.info("Security Agent was not run.")
        return

    _render_agent_guide("security")

    risk_level = data.get("risk_level", "UNKNOWN")
    risk_colors = {
        "CRITICAL": "#f85149",
        "HIGH":     "#e3b341",
        "MEDIUM":   "#d29922",
        "LOW":      "#3fb950",
        "SAFE":     "#58a6ff",
    }
    color = risk_colors.get(risk_level, "#8b949e")

    st.markdown("### 🔒 Security Analysis")

    # ---- Top stats row ----
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(
        f"<div style='background:#161b22;border:2px solid {color};"
        f"border-radius:10px;padding:16px;text-align:center;'>"
        f"<div style='font-size:0.85rem;color:#8b949e;'>Overall Risk</div>"
        f"<div style='font-size:1.6rem;font-weight:700;color:{color};'>{risk_level}</div>"
        f"</div>",
        unsafe_allow_html=True
    )
    col2.metric("Files Scanned",  data.get("files_scanned",  0))
    col3.metric("Files Affected", data.get("files_affected", 0))
    col4.metric("Total Findings", data.get("total_found",    0))

    st.markdown("")

    # ---- Severity counts ----
    counts = data.get("severity_counts", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🚨 Critical", counts.get("CRITICAL", 0))
    c2.metric("🔴 High",     counts.get("HIGH",     0))
    c3.metric("🟡 Medium",   counts.get("MEDIUM",   0))
    c4.metric("🟢 Low",      counts.get("LOW",      0))

    # ---- Bar chart ----
    if any(counts.values()):
        fig = px.bar(
            x=list(counts.keys()),
            y=list(counts.values()),
            color=list(counts.keys()),
            color_discrete_map={
                "CRITICAL": "#f85149",
                "HIGH":     "#e3b341",
                "MEDIUM":   "#d29922",
                "LOW":      "#3fb950",
            },
            title="Vulnerabilities by Severity",
        )
        fig.update_layout(
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            font={"color": "#e6edf3"},
            showlegend=False,
            height=280,
            margin=dict(t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---- Vulnerabilities list ----
    vulns = data.get("vulnerabilities", [])
    if not vulns:
        st.success("✅ No vulnerabilities detected! This repository looks secure.")
        return

    st.markdown("---")
    st.markdown(f"### 🔍 Findings ({len(vulns)} total)")

    # Filter
    sev_filter = st.selectbox(
        "Filter by severity",
        ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
        key="sec_filter"
    )
    filtered = vulns if sev_filter == "All" else [
        v for v in vulns if v.get("severity", "").upper() == sev_filter
    ]

    # Group by file
    from collections import defaultdict
    by_file = defaultdict(list)
    for v in filtered:
        by_file[v.get("file", "Unknown")].append(v)

    for filepath, file_vulns in by_file.items():
        worst_sev  = file_vulns[0].get("severity", "LOW")
        sev_emoji  = {"CRITICAL": "🚨", "HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(worst_sev, "⚠️")
        auto_open  = worst_sev == "CRITICAL"

        with st.expander(
            f"{sev_emoji} {filepath}  —  {len(file_vulns)} finding{'s' if len(file_vulns) != 1 else ''}",
            expanded=auto_open
        ):
            st.markdown(f"**📁 File:** `{filepath}`")
            st.markdown("---")

            for idx, vuln in enumerate(file_vulns, 1):
                sev   = vuln.get("severity", "MEDIUM").upper()
                badge = {
                    "CRITICAL": "🚨 CRITICAL",
                    "HIGH":     "🔴 HIGH",
                    "MEDIUM":   "🟡 MEDIUM",
                    "LOW":      "🟢 LOW",
                }.get(sev, sev)
                cwe = vuln.get("cwe", "")

                st.markdown(
                    f"**Finding {idx}: {badge}**" +
                    (f"  `{cwe}`" if cwe else "")
                )
                st.markdown(f"**🏷️ Type:** {vuln.get('type', 'Unknown')}")
                st.markdown(f"**📍 Line:** `{vuln.get('line', '?')}`")

                # Reason / description
                reason = vuln.get("reason") or vuln.get("description", "")
                if reason:
                    st.markdown(f"**⚠️ Why it's dangerous:** {reason}")

                # Vulnerable code snippet
                snippet = vuln.get("code_snippet", "")
                if snippet:
                    st.markdown("**💀 Vulnerable code:**")
                    st.code(snippet, language="python")

                # Fix with code
                fix = vuln.get("fix", "")
                if fix:
                    st.markdown("**✅ How to fix:**")
                    st.code(fix, language="python")

                st.markdown(
                    f"<small>🔍 Detected by: {vuln.get('source', 'Scanner')}</small>",
                    unsafe_allow_html=True
                )

                if idx != len(file_vulns):
                    st.markdown("---")

    # ---- AI deep analysis ----
    ai = data.get("ai_analysis", "")
    if ai:
        with st.expander("🤖 AI Deep Security Analysis (Additional Findings)"):
            st.markdown(ai)

def _show_documentation(data: dict):
    """Display Documentation Agent results."""
    if not data:
        st.info("Documentation Agent was not run.")
        return

    _render_agent_guide("documentation")

    st.markdown("### 📄 Documentation Analysis")
    st.markdown(data.get("summary", ""))

    # ---- Coverage metrics ----
    total_items = data.get("total_items", 0)
    coverage_value = f"{data.get('doc_coverage', 0)}%" if total_items > 0 else "N/A"

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Doc Coverage",       coverage_value)
    d2.metric("Documented Items",   data.get("documented_items", 0))
    d3.metric("Undocumented Items", len(data.get("missing_docs", [])))
    d4.metric("Total Python Items", total_items)

    if total_items == 0:
        scanned = data.get("python_files_scanned", 0)
        failed = data.get("python_parse_failures", 0)
        st.info(
            "No Python functions/classes were detected for documentation metrics. "
            f"Scanned Python files: {scanned}. Parse failures: {failed}."
        )

    st.markdown("---")

    # ---- README Analysis ----
    readme = data.get("readme_analysis", {})
    if readme:
        st.markdown("#### 📋 README Analysis")

        if readme.get("found"):
            quality = readme.get("quality", "Unknown")
            q_emoji = {"Excellent": "🟢", "Good": "🟡", "Fair": "🟠", "Poor": "🔴"}.get(quality, "⚪")
            q_color = {"Excellent": "#3fb950", "Good": "#d29922", "Fair": "#e3b341", "Poor": "#f85149"}.get(quality, "#8b949e")

            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(
                    f"<div style='background:#161b22;border:2px solid {q_color};"
                    f"border-radius:10px;padding:20px;text-align:center;'>"
                    f"<div style='color:#8b949e;font-size:0.85rem;'>README Quality</div>"
                    f"<div style='color:{q_color};font-size:2rem;font-weight:700;'>{q_emoji} {quality}</div>"
                    f"<div style='color:#8b949e;font-size:0.8rem;margin-top:4px;'>"
                    f"{readme.get('score', 0)}/100 score • {readme.get('length', 0)} chars</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with col2:
                # Present sections
                present = readme.get("present", [])
                missing_sec = readme.get("missing", [])
                if present:
                    st.markdown("**✅ Sections present:**")
                    for s in present:
                        st.markdown(f"  ✅ {s}")
                if missing_sec:
                    st.markdown("**❌ Missing sections:**")
                    for s in missing_sec:
                        st.markdown(f"  ❌ {s}")

            if readme.get("suggestion"):
                st.info(f"💡 **Tip:** {readme['suggestion']}")

            # Show improvement suggestions
            improvement = readme.get("improvement", "")
            if improvement:
                with st.expander("🤖 AI-Generated Missing Sections (copy and add to your README)"):
                    st.markdown(improvement)

            improvement_error = readme.get("improvement_error", "")
            if improvement_error:
                st.warning(
                    "Could not generate missing README sections from Gemini right now "
                    "(API/quota issue). The missing-section checklist above is still valid."
                )

        else:
            st.error("❌ No README.md found! This is the most important documentation file.")
            improvement = readme.get("improvement", "")
            if improvement:
                with st.expander("🤖 Suggested README Template — click to copy"):
                    st.markdown(improvement)

    st.markdown("---")

    # ---- Module Summaries ----
    module_summaries = data.get("module_summaries", [])
    if module_summaries:
        st.markdown("#### 📦 Module Summaries")
        st.caption("What each file does — at a glance")

        for mod in module_summaries:
            ai_badge = "🤖 AI" if mod.get("ai_generated") else "📝 Existing"
            with st.expander(
                f"📄 {mod['file']}  —  {mod['line_count']} lines  [{ai_badge}]",
                expanded=False
            ):
                st.markdown(f"**📝 Summary:** {mod['summary']}")

                col1, col2 = st.columns(2)
                with col1:
                    if mod.get("functions"):
                        st.markdown("**Functions:**")
                        for fn in mod["functions"][:8]:
                            st.markdown(f"  - `{fn}()`")
                with col2:
                    if mod.get("classes"):
                        st.markdown("**Classes:**")
                        for cls in mod["classes"]:
                            st.markdown(f"  - `{cls}`")

    st.markdown("---")

    # ---- Auto-Generated Docstrings ----
    generated = data.get("generated_docs", [])
    if generated:
        st.markdown(f"#### 🤖 Auto-Generated Docstrings ({len(generated)} generated)")
        st.caption("Copy these into your code to improve documentation instantly")

        for doc in generated:
            node_emoji = "🏛️" if doc.get("type") == "class" else "⚙️"
            with st.expander(
                f"{node_emoji} `{doc.get('name', 'Unknown')}()` "
                f"— {doc.get('file', '')} line {doc.get('line', '?')}",
                expanded=False
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**📄 Current code (no docstring):**")
                    st.code(doc.get("code", ""), language="python")

                with col2:
                    st.markdown("**✅ Suggested docstring to add:**")
                    st.code(doc.get("docstring", ""), language="python")

                st.markdown(
                    f"**📁 File:** `{doc.get('file','')}` | "
                    f"**Line:** `{doc.get('line','?')}` | "
                    f"**Type:** `{doc.get('type','function')}`"
                )
                st.info(
                    f"💡 Add this docstring right after: `{doc.get('signature','def ...:')}`"
                )

    # ---- Full list of undocumented items ----
    missing = data.get("missing_docs", [])
    if missing:
        st.markdown("---")
        st.markdown(f"#### ⚠️ All Undocumented Functions/Classes ({len(missing)} total)")

        # Group by file
        from collections import defaultdict
        by_file = defaultdict(list)
        for item in missing:
            by_file[item.get("file", "Unknown")].append(item)

        for filepath, items in by_file.items():
            with st.expander(
                f"📄 {filepath} — {len(items)} undocumented item{'s' if len(items) != 1 else ''}",
                expanded=False
            ):
                for item in items:
                    node_emoji = "🏛️" if item.get("type") == "class" else "⚙️"
                    st.markdown(
                        f"{node_emoji} **`{item.get('name', 'Unknown')}()`** "
                        f"— line `{item.get('line', '?')}` "
                        f"({item.get('type', 'function')})"
                    )

# ============================================================
# REPLACE YOUR _show_dependencies FUNCTION WITH THIS
# ============================================================

def _show_dependencies(data: dict):
    """Display Dependency Agent results."""
    if not data:
        st.info("Dependency Agent was not run.")
        return

    _render_agent_guide("dependencies")

    st.markdown("### 📦 Dependency Analysis")
    st.markdown(data.get("summary", ""))

    sources = data.get("sources", [])
    if sources:
        st.caption(f"📂 Sources: {', '.join(sources[:5])}")

    packages = data.get("packages", [])
    if not packages:
        st.warning("No dependency files found (requirements.txt / package.json / .csproj / pom.xml).")
        return

    # ---- Top metrics ----
    vulns    = data.get("vulnerabilities", [])
    outdated = data.get("outdated", [])
    rc       = data.get("risk_counts", {})

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Packages",  data.get("total_packages", len(packages)))
    m2.metric("🚨 Vulnerable",   len(vulns))
    m3.metric("🟡 Outdated",     len(outdated))
    m4.metric("Health Score",    f"{data.get('score', 0)}/100")
    m5.metric("CVEs Found",      sum(len(p.get("vulnerabilities",[])) for p in packages))

    st.markdown("---")

    # ---- Vulnerable packages — detailed cards ----
    if vulns:
        st.markdown(f"### 🚨 Vulnerable Packages ({len(vulns)})")
        st.caption("These packages have known CVEs and should be upgraded immediately.")

        for pkg in vulns:
            risk  = pkg.get("risk", "MEDIUM")
            color = {"CRITICAL":"#f85149","HIGH":"#e3b341","MEDIUM":"#d29922"}.get(risk,"#8b949e")
            badge = {"CRITICAL":"🚨 CRITICAL","HIGH":"🔴 HIGH","MEDIUM":"🟡 MEDIUM"}.get(risk, risk)

            with st.expander(
                f"{badge}  |  {pkg['name']}  "
                f"v{pkg['version']} → v{pkg['latest_version']}  "
                f"|  {len(pkg.get('vulnerabilities',[]))} CVE(s)",
                expanded=(risk == "CRITICAL")
            ):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**📦 Package:**  `{pkg['name']}`")
                col2.markdown(f"**Current:**  `{pkg['version']}`")
                col3.markdown(f"**Latest:**  `{pkg['latest_version']}`")

                st.markdown(f"**Risk Level:** <span style='color:{color};font-weight:700;'>{badge}</span>",
                            unsafe_allow_html=True)

                # CVE details
                cve_list = pkg.get("vulnerabilities", [])
                if cve_list:
                    st.markdown("**Known CVEs:**")
                    for cve in cve_list:
                        cve_id   = cve.get("id","Unknown")
                        summary  = cve.get("summary","No description")
                        sev      = cve.get("severity","UNKNOWN")
                        affected = cve.get("affected_versions","")
                        link     = cve.get("link","")
                        pub      = cve.get("published","")

                        sev_color = {"CRITICAL":"#f85149","HIGH":"#e3b341",
                                     "MEDIUM":"#d29922","LOW":"#3fb950"}.get(sev,"#8b949e")

                        st.markdown(
                            f"<div style='background:#161b22;border-left:4px solid {sev_color};"
                            f"border-radius:6px;padding:12px;margin:6px 0;'>"
                            f"<b style='color:{sev_color};'>{cve_id}</b>"
                            f"<span style='color:#8b949e;font-size:0.8rem;margin-left:8px;'>"
                            f"Severity: {sev}"
                            + (f" | Published: {pub}" if pub else "")
                            + (f" | Affected: {affected}" if affected else "")
                            + f"</span><br>"
                            f"<span style='color:#e6edf3;'>{summary}</span>"
                            + (f"<br><a href='{link}' target='_blank' style='color:#58a6ff;font-size:0.8rem;'>🔗 View on OSV</a>" if link else "")
                            + f"</div>",
                            unsafe_allow_html=True
                        )

                # Upgrade command
                cmd = pkg.get("upgrade_cmd","")
                if cmd:
                    st.markdown("**✅ Fix — run this command:**")
                    st.code(cmd, language="bash")

    # ---- Outdated packages ----
    if outdated:
        st.markdown("---")
        st.markdown(f"### 🟡 Outdated Packages ({len(outdated)})")
        st.caption("No known CVEs but newer versions are available.")

        for pkg in outdated:
            with st.expander(
                f"🟡 {pkg['name']}  v{pkg['version']} → v{pkg['latest_version']}"
            ):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**Package:** `{pkg['name']}`")
                col2.markdown(f"**Current:** `{pkg['version']}`")
                col3.markdown(f"**Latest:** `{pkg['latest_version']}`")
                cmd = pkg.get("upgrade_cmd","")
                if cmd:
                    st.markdown("**Upgrade command:**")
                    st.code(cmd, language="bash")

    # ---- Full package table ----
    st.markdown("---")
    st.markdown(f"### 📋 All Packages ({len(packages)} total)")

    # Filter
    status_filter = st.selectbox(
        "Filter",
        ["All", "Vulnerable", "Outdated", "OK"],
        key="dep_filter"
    )

    if status_filter == "Vulnerable":
        filtered = [p for p in packages if p.get("is_vulnerable")]
    elif status_filter == "Outdated":
        filtered = [p for p in packages if p.get("is_outdated") and not p.get("is_vulnerable")]
    elif status_filter == "OK":
        filtered = [p for p in packages if not p.get("is_vulnerable") and not p.get("is_outdated")]
    else:
        filtered = packages

    rows = []
    for pkg in filtered:
        rows.append({
            "Status":   pkg.get("status", ""),
            "Package":  pkg["name"],
            "Current":  pkg["version"],
            "Latest":   pkg.get("latest_version","Unknown"),
            "CVEs":     len(pkg.get("vulnerabilities",[])),
            "Risk":     pkg.get("risk","SAFE"),
        })

    if rows:
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ---- AI recommendations ----
    ai = data.get("ai_recommendations","")
    if ai:
        with st.expander("🤖 AI Upgrade Recommendations"):
            st.markdown(ai)


# ============================================================
# REPLACE YOUR _show_bug_fixes FUNCTION WITH THIS
# ============================================================

def _show_bug_fixes(data: dict):
    """Display Bug Fix Agent results."""
    if not data:
        st.info("Bug Fix Agent was not run.")
        return

    _render_agent_guide("bug_fix")

    st.markdown("### 🔧 Automatic Bug Fixes & Patches")
    st.markdown(data.get("summary", ""))

    # ---- Stats ----
    stats = data.get("stats", {})
    b1, b2, b3 = st.columns(3)
    b1.metric("Total Patches",  stats.get("total_patches", 0))
    b2.metric("🔒 Security Fixes", stats.get("security_fixes", 0))
    b3.metric("✨ Code Fixes",   stats.get("code_quality_fixes", 0))

    patches = data.get("patches", [])
    if not patches:
        st.success("✅ No patches generated. Either no issues were found or files were not accessible.")
        return

    st.markdown("---")

    # ---- Security fixes first ----
    sec_patches  = [p for p in patches if p.get("type") == "Security Fix"]
    code_patches = [p for p in patches if p.get("type") == "Code Quality Fix"]

    if sec_patches:
        st.markdown(f"### 🔒 Security Patches ({len(sec_patches)})")
        st.caption("These patches fix vulnerabilities found by the Security Agent.")

        for i, patch in enumerate(sec_patches, 1):
            sev   = patch.get("severity", "HIGH")
            color = {"CRITICAL":"#f85149","HIGH":"#e3b341","MEDIUM":"#d29922"}.get(sev,"#8b949e")
            badge = {"CRITICAL":"🚨","HIGH":"🔴","MEDIUM":"🟡"}.get(sev,"⚠️")
            cwe   = patch.get("cwe","")

            with st.expander(
                f"{badge} Patch #{i}: {patch.get('vulnerability','Security Fix')} "
                f"— {patch.get('file','')} line {patch.get('line','?')}",
                expanded=(sev == "CRITICAL")
            ):
                # Header info
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**📁 File:** `{patch.get('file','')}`")
                col2.markdown(f"**📍 Line:** `{patch.get('line','?')}`")
                col3.markdown(
                    f"**Severity:** <span style='color:{color};font-weight:700;'>{sev}</span>"
                    + (f"  `{cwe}`" if cwe else ""),
                    unsafe_allow_html=True
                )

                st.markdown(f"**🐛 Issue:** {patch.get('vulnerability','')}")
                st.markdown(f"**💡 Explanation:** {patch.get('explanation','')}")

                # Steps
                steps = patch.get("steps", [])
                if steps:
                    st.markdown("**📋 What was changed:**")
                    for step in steps:
                        st.markdown(f"  - {step}")

                st.markdown("---")

                # Side-by-side code comparison
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(
                        "<div style='background:#3d1a1a;border:1px solid #f85149;"
                        "border-radius:6px;padding:8px 12px;margin-bottom:6px;'>"
                        "❌ <b>Vulnerable Code</b></div>",
                        unsafe_allow_html=True
                    )
                    lang = _patch_language(patch.get("file",""))
                    st.code(patch.get("original_code",""), language=lang)

                with col2:
                    st.markdown(
                        "<div style='background:#1a3d1a;border:1px solid #3fb950;"
                        "border-radius:6px;padding:8px 12px;margin-bottom:6px;'>"
                        "✅ <b>Fixed Code</b></div>",
                        unsafe_allow_html=True
                    )
                    st.code(patch.get("fixed_code",""), language=lang)

                st.info(
                    "💡 **How to apply:** Copy the Fixed Code above and replace "
                    f"lines around line {patch.get('line','?')} in `{patch.get('file','')}`"
                )

    # ---- Code quality fixes ----
    if code_patches:
        st.markdown("---")
        st.markdown(f"### ✨ Code Quality Patches ({len(code_patches)})")
        st.caption("These patches fix high-severity code quality issues.")

        for i, patch in enumerate(code_patches, 1):
            with st.expander(
                f"✨ Patch #{i}: {patch.get('issue', 'Code Fix')} "
                f"— {patch.get('file','')} line {patch.get('line','?')}",
                expanded=False
            ):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**📁 File:** `{patch.get('file','')}`")
                col2.markdown(f"**📍 Line:** `{patch.get('line','?')}`")
                col3.markdown(f"**Severity:** `HIGH`")

                st.markdown(f"**🐛 Issue:** {patch.get('issue','')}")
                st.markdown(f"**💡 Explanation:** {patch.get('explanation','')}")

                st.markdown("---")

                lang = _patch_language(patch.get("file",""))
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(
                        "<div style='background:#3d1a1a;border:1px solid #f85149;"
                        "border-radius:6px;padding:8px 12px;margin-bottom:6px;'>"
                        "❌ <b>Before</b></div>",
                        unsafe_allow_html=True
                    )
                    st.code(patch.get("original_code",""), language=lang)
                with col2:
                    st.markdown(
                        "<div style='background:#1a3d1a;border:1px solid #3fb950;"
                        "border-radius:6px;padding:8px 12px;margin-bottom:6px;'>"
                        "✅ <b>After</b></div>",
                        unsafe_allow_html=True
                    )
                    st.code(patch.get("fixed_code",""), language=lang)

                st.info(
                    f"💡 **How to apply:** Replace the code around line "
                    f"{patch.get('line','?')} in `{patch.get('file','')}`"
                )


def _patch_language(filepath: str) -> str:
    """Detect language for syntax highlighting."""
    ext_map = {
        ".py":"python", ".js":"javascript", ".ts":"typescript",
        ".cs":"csharp", ".java":"java", ".go":"go",
        ".cpp":"cpp", ".c":"c", ".rb":"ruby", ".php":"php",
    }
    for ext, lang in ext_map.items():
        if filepath.endswith(ext):
            return lang
    return "python"

def _show_risk_heatmap(data: dict):
    """Display Risk Heatmap Agent results."""
    if not data:
        st.info("Risk Heatmap Agent was not run.")
        return

    _render_agent_guide("risk_heatmap")

    st.markdown("### 🗺️ Repository Risk Heatmap")

    overall_score = data.get("overall_risk_score", 0)
    st.markdown(f"**Overall Repository Risk Score:** `{overall_score}/100` (higher = more risky)")
    st.caption(f"Files profiled: {data.get('total_files', 0)}")

    # Module risk visualization
    module_risks = data.get("module_risks", [])
    if module_risks:
        st.markdown("#### 📁 Risk by Module")

        for module in module_risks:
            score = module["max_score"]
            color = {
                "CRITICAL": "#f85149",
                "HIGH":     "#e3b341",
                "MEDIUM":   "#d29922",
                "LOW":      "#3fb950",
            }.get(module["level"], "#8b949e")

            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                st.markdown(f"{module['emoji']} **{module['module']}/**")
            with col2:
                st.progress(score / 100)
            with col3:
                st.markdown(f"<span style='color:{color};'>**{score}/100**</span>", unsafe_allow_html=True)

    # Top risky files
    top_files = data.get("top_risky_files", [])
    if top_files:
        st.markdown("#### 🔴 Most Dangerous Files")
        for file in top_files:
            st.markdown(
                f"{file['emoji']} `{file['file']}` — Risk: **{file['score']}/100** "
                f"(Security issues: {file['breakdown']['security_issues']}, "
                f"Complexity: {file['breakdown']['complexity']:.0f})"
            )

    # Distribution chart
    distribution = data.get("risk_distribution", {})
    if distribution:
        fig = px.pie(
            values=list(distribution.values()),
            names=list(distribution.keys()),
            title="File Risk Distribution",
            color=list(distribution.keys()),
            color_discrete_map={
                "CRITICAL": "#f85149",
                "HIGH":     "#e3b341",
                "MEDIUM":   "#d29922",
                "LOW":      "#3fb950",
            },
        )
        fig.update_layout(
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            font={"color": "#e6edf3"},
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# REPLACE YOUR _show_architecture FUNCTION WITH THIS
# ============================================================

# ============================================================
# REPLACE YOUR _show_architecture FUNCTION WITH THIS
# Uses HTML + JavaScript to render the Mermaid diagram
# This works in Streamlit without any extra packages
# ============================================================

# ============================================================
# REPLACE YOUR _show_architecture FUNCTION WITH THIS
# Uses Plotly to draw the architecture diagram
# No external CDN needed — works 100% in Streamlit
# ============================================================

# ============================================================
# REPLACE YOUR _show_architecture FUNCTION WITH THIS
# Fixed: Colors, connections, structured layout
# No API keys needed - uses only Plotly (already installed)
# ============================================================

# ============================================================
# REPLACE YOUR _show_architecture FUNCTION WITH THIS
# FINAL FIX: Forces colors to work for ANY repository
# ============================================================

# ============================================================
# REPLACE YOUR _show_architecture FUNCTION WITH THIS
# Generates a proper architecture diagram like the sample image:
# - Boxes with labels (not just circles)
# - Arrows showing data flow
# - Grouped containers
# - Color coded by layer
# ============================================================

def _show_architecture(data: dict):
    """Display Architecture Agent results."""
    if not data:
        st.info("Architecture Agent was not run.")
        return

    _render_agent_guide("architecture")

    st.markdown("### 🏗️ Repository Architecture")

    # ---- Top metrics ----
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Components",     len(data.get("components", [])))
    a2.metric("Edges",          len(data.get("edges", [])))
    a3.metric("Tech Stack",     len(data.get("tech_stack", [])))
    a4.metric("Files Analyzed", len(data.get("module_stats", [])))

    # ---- AI description ----
    ai_desc = data.get("ai_description", {})
    if ai_desc:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if ai_desc.get("architecture_pattern"):
                st.markdown(
                    f"<div style='background:#161b22;border:1px solid #30363d;"
                    f"border-radius:8px;padding:12px;margin-bottom:8px;'>"
                    f"<b>🏛️ Architecture Pattern</b><br>"
                    f"<span style='color:#58a6ff;font-size:1.1rem;'>"
                    f"{ai_desc['architecture_pattern']}</span></div>",
                    unsafe_allow_html=True
                )
            if ai_desc.get("layer_breakdown"):
                st.markdown(f"**📊 Layers:** {ai_desc['layer_breakdown']}")
        with col2:
            if ai_desc.get("data_flow"):
                st.markdown(f"**🔄 Data Flow:** {ai_desc['data_flow']}")

    # ---- Tech stack ----
    tech_stack = data.get("tech_stack", [])
    if tech_stack:
        st.markdown("---")
        st.markdown("**🛠️ Tech Stack:** " + " ".join([f"`{t}`" for t in tech_stack]))

    # ---- Architecture Box Diagram ----
    components = data.get("components", [])
    edges      = data.get("edges", [])

    if components:
        st.markdown("---")
        st.markdown("#### 📊 Architecture Diagram")
        st.caption("Box diagram showing modules, layers and data flow")
        fig = _build_box_diagram(components, edges, data)
        st.plotly_chart(fig, use_container_width=True)

    # ---- Components list ----
    if components:
        st.markdown("---")
        st.markdown("#### 🧩 Components")
        cols = st.columns(2)
        for i, comp in enumerate(components):
            file_count = comp.get("file_count", len(comp.get("files", [])))
            color      = _PALETTE[i % len(_PALETTE)]
            with cols[i % 2]:
                st.markdown(
                    f"<div style='background:#161b22;border-left:4px solid {color};"
                    f"border-radius:6px;padding:10px 14px;margin:4px 0;'>"
                    f"<b>{comp.get('icon','📁')} {comp.get('name','?')}</b>"
                    f"<span style='color:#8b949e;float:right;'>{file_count} files</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

    # ---- Module stats ----
    module_stats = data.get("module_stats", [])
    if module_stats:
        st.markdown("---")
        st.markdown("#### 📊 Module Analysis")
        import pandas as pd
        rows = [{
            "File":      m["file"].split("/")[-1],
            "Full Path": m["file"],
            "LOC":       m["loc"],
            "Functions": m["functions"],
            "Classes":   m["classes"],
            "Imports":   m["imports"],
        } for m in module_stats[:15]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ---- Folder structure ----
    if data.get("folder_structure"):
        with st.expander("📁 Folder Structure"):
            st.code(data["folder_structure"])

    # ---- Recommendations ----
    if ai_desc.get("recommendations"):
        st.markdown("---")
        with st.expander("💡 Recommendations"):
            st.markdown(ai_desc["recommendations"])


_PALETTE = [
    "#1f77b4","#2ca02c","#d62728","#ff7f0e","#9467bd",
    "#8c564b","#e377c2","#17becf","#bcbd22","#7f7f7f",
    "#aec7e8","#98df8a",
]


def _build_box_diagram(components, edges, data):
    """
    Build a proper box-and-arrow architecture diagram like the sample image.
    Uses Plotly shapes (rectangles) + annotations (text) + scatter (arrows).
    """
    import plotly.graph_objects as go
    import math

    comps = components[:12]
    n     = len(comps)
    if n == 0:
        return go.Figure()

    # ── Assign layers based on folder names ──────────────────────────
    # Layer 0 = Entry/Client, Layer 1 = API/Web, Layer 2 = Core/Services
    # Layer 3 = Data/DB, Layer 4 = External/Config
    LAYER_KEYWORDS = {
        0: ["client","cli","web","frontend","ui","static","templates"],
        1: ["api","routes","handlers","views","controllers","gateway"],
        2: ["services","core","auth","business","logic","agents","sqli"],
        3: ["models","database","db","migrations","storage","cache","redis"],
        4: ["config","utils","helpers","tests","root","scripts"],
    }

    def get_layer(comp_name, folder):
        name_lower = (comp_name + " " + folder).lower()
        for layer, keywords in LAYER_KEYWORDS.items():
            if any(k in name_lower for k in keywords):
                return layer
        return 2  # default to core layer

    # Group components by layer
    layer_groups = {}
    for comp in comps:
        layer = get_layer(comp["name"], comp.get("folder",""))
        layer_groups.setdefault(layer, []).append(comp)

    # Sort layers
    sorted_layers = sorted(layer_groups.keys())

    # ── Calculate box positions ───────────────────────────────────────
    # Each layer is a column (left to right)
    # Within a layer, boxes are stacked vertically

    CANVAS_W   = 10.0   # total canvas width
    CANVAS_H   = 8.0    # total canvas height
    BOX_W      = 1.6    # box width
    BOX_H      = 0.7    # box height
    H_PADDING  = 0.3    # horizontal padding between layers
    V_PADDING  = 0.2    # vertical padding between boxes in same layer

    num_layers = len(sorted_layers)
    layer_width = (CANVAS_W - H_PADDING * (num_layers + 1)) / num_layers

    # Assign x center per layer
    layer_x = {}
    for i, layer in enumerate(sorted_layers):
        layer_x[layer] = H_PADDING + layer_width * i + layer_width / 2

    # Assign y center per box in each layer
    box_positions = {}   # comp_name → (cx, cy)
    for layer in sorted_layers:
        layer_comps = layer_groups[layer]
        total_h = len(layer_comps) * BOX_H + (len(layer_comps)-1) * V_PADDING
        start_y = CANVAS_H/2 + total_h/2 - BOX_H/2

        for j, comp in enumerate(layer_comps):
            cx = layer_x[layer]
            cy = start_y - j * (BOX_H + V_PADDING)
            box_positions[comp["name"]] = (cx, cy)

    # ── Layer background rectangles ───────────────────────────────────
    LAYER_COLORS = {
        0: "rgba(33,150,243,0.08)",   # blue  - client
        1: "rgba(156,39,176,0.08)",   # purple - api
        2: "rgba(76,175,80,0.08)",    # green  - core
        3: "rgba(255,152,0,0.08)",    # orange - data
        4: "rgba(96,125,139,0.08)",   # gray   - config
    }
    LAYER_LABELS = {
        0: "Client / UI",
        1: "API / Routes",
        2: "Core / Services",
        3: "Data / Storage",
        4: "Config / Utils",
    }
    LAYER_BORDER = {
        0: "rgba(33,150,243,0.4)",
        1: "rgba(156,39,176,0.4)",
        2: "rgba(76,175,80,0.4)",
        3: "rgba(255,152,0,0.4)",
        4: "rgba(96,125,139,0.4)",
    }

    shapes    = []
    annots    = []

    # Draw layer backgrounds
    for layer in sorted_layers:
        layer_comps = layer_groups[layer]
        lx = layer_x[layer]
        min_y = min(box_positions[c["name"]][1] for c in layer_comps) - BOX_H/2 - 0.25
        max_y = max(box_positions[c["name"]][1] for c in layer_comps) + BOX_H/2 + 0.45

        shapes.append(dict(
            type      = "rect",
            x0        = lx - layer_width/2 + 0.05,
            x1        = lx + layer_width/2 - 0.05,
            y0        = min_y,
            y1        = max_y,
            fillcolor = LAYER_COLORS.get(layer, "rgba(100,100,100,0.05)"),
            line      = dict(color=LAYER_BORDER.get(layer,"rgba(100,100,100,0.3)"), width=1, dash="dot"),
        ))

        # Layer label at top
        annots.append(dict(
            x         = lx,
            y         = max_y - 0.05,
            text      = f"<b>{LAYER_LABELS.get(layer,'Layer')}</b>",
            showarrow = False,
            font      = dict(size=9, color=LAYER_BORDER.get(layer,"#8b949e")),
            xanchor   = "center",
            yanchor   = "top",
        ))

    # ── Draw component boxes ──────────────────────────────────────────
    for idx, comp in enumerate(comps):
        name = comp["name"]
        if name not in box_positions:
            continue
        cx, cy     = box_positions[name]
        color      = _PALETTE[idx % len(_PALETTE)]
        file_count = comp.get("file_count", len(comp.get("files",[])))
        icon       = comp.get("icon","📁")

        # Box shadow (slightly offset darker rect)
        shapes.append(dict(
            type      = "rect",
            x0        = cx - BOX_W/2 + 0.03,
            x1        = cx + BOX_W/2 + 0.03,
            y0        = cy - BOX_H/2 - 0.03,
            y1        = cy + BOX_H/2 - 0.03,
            fillcolor = "rgba(0,0,0,0.3)",
            line      = dict(width=0),
        ))

        # Main box
        shapes.append(dict(
            type      = "rect",
            x0        = cx - BOX_W/2,
            x1        = cx + BOX_W/2,
            y0        = cy - BOX_H/2,
            y1        = cy + BOX_H/2,
            fillcolor = color,
            line      = dict(color="white", width=1.5),
        ))

        # Box label
        annots.append(dict(
            x         = cx,
            y         = cy + 0.08,
            text      = f"<b>{icon} {name}</b>",
            showarrow = False,
            font      = dict(size=10, color="white", family="Arial"),
            xanchor   = "center",
            yanchor   = "middle",
        ))

        # File count sub-label
        annots.append(dict(
            x         = cx,
            y         = cy - 0.18,
            text      = f"{file_count} files",
            showarrow = False,
            font      = dict(size=8, color="rgba(255,255,255,0.7)"),
            xanchor   = "center",
            yanchor   = "middle",
        ))

    # ── Draw arrows between boxes ─────────────────────────────────────
    arrow_x = []
    arrow_y = []

    # Build folder → comp name map
    folder_map = {}
    for comp in comps:
        folder_map[comp.get("folder","").lower()] = comp["name"]
        folder_map[comp["name"].lower()]           = comp["name"]

    drawn_arrows = set()

    # Real edges from dependency parsing
    for edge in edges:
        if edge.get("type") != "local":
            continue
        sf  = edge["from"].split("/")[0].lower() if "/" in edge["from"] else "root"
        df  = edge["to"].split("/")[0].lower()   if "/" in edge["to"]   else "root"
        src = folder_map.get(sf)
        dst = folder_map.get(df)
        if not src or not dst or src == dst:
            continue
        key = f"{src}→{dst}"
        if key in drawn_arrows:
            continue
        if src not in box_positions or dst not in box_positions:
            continue
        drawn_arrows.add(key)

        x0, y0 = box_positions[src]
        x1, y1 = box_positions[dst]

        # Draw arrow from right edge of src to left edge of dst
        arrow_x += [x0 + BOX_W/2, x1 - BOX_W/2, None]
        arrow_y += [y0, y1, None]

    # Fallback: connect layers sequentially
    if not drawn_arrows:
        prev_comps = None
        for layer in sorted_layers:
            cur_comps = layer_groups[layer]
            if prev_comps:
                # Connect last of prev layer to first of cur layer
                src = prev_comps[-1]["name"]
                dst = cur_comps[0]["name"]
                if src in box_positions and dst in box_positions:
                    x0,y0 = box_positions[src]
                    x1,y1 = box_positions[dst]
                    arrow_x += [x0+BOX_W/2, x1-BOX_W/2, None]
                    arrow_y += [y0, y1, None]
            prev_comps = cur_comps

    # Arrow trace
    arrow_trace = go.Scatter(
        x          = arrow_x,
        y          = arrow_y,
        mode       = "lines",
        line       = dict(color="rgba(255,255,255,0.6)", width=1.5),
        hoverinfo  = "none",
        showlegend = False,
    )

    # Arrowhead dots at destination
    arrowhead_x = [arrow_x[i] for i in range(1, len(arrow_x), 3) if arrow_x[i] is not None]
    arrowhead_y = [arrow_y[i] for i in range(1, len(arrow_y), 3) if arrow_y[i] is not None]

    arrowhead_trace = go.Scatter(
        x          = arrowhead_x,
        y          = arrowhead_y,
        mode       = "markers",
        marker     = dict(symbol="arrow-right", size=10, color="rgba(255,255,255,0.8)"),
        hoverinfo  = "none",
        showlegend = False,
    )

    # Title annotation
    repo_name = data.get("repo_name","Repository")
    annots.append(dict(
        x=CANVAS_W/2, y=CANVAS_H+0.1,
        text=f"<b>🏗️ {repo_name} — System Architecture</b>",
        showarrow=False,
        font=dict(size=14, color="#e6edf3"),
        xanchor="center", yanchor="bottom",
    ))

    # ── Build figure ──────────────────────────────────────────────────
    fig = go.Figure(data=[arrow_trace, arrowhead_trace])

    fig.update_layout(
        shapes      = shapes,
        annotations = annots,
        paper_bgcolor = "#0d1117",
        plot_bgcolor  = "#0d1117",
        height        = 550,
        margin        = dict(t=50, b=40, l=20, r=20),
        xaxis = dict(
            range=[0, CANVAS_W], showgrid=False,
            zeroline=False, showticklabels=False,
        ),
        yaxis = dict(
            range=[0, CANVAS_H+0.5], showgrid=False,
            zeroline=False, showticklabels=False,
            scaleanchor="x", scaleratio=1,
        ),
        hovermode = "closest",
    )

    return fig

def _draw_architecture_plotly_v2(components: list, edges: list):
    """
    Draw architecture using ONE trace per node.
    This is the ONLY reliable way to show different colors in Plotly.
    Uses Streamlit columns to arrange nodes in a proper grid.
    """
    import math
    import plotly.graph_objects as go

    comps = components[:12]
    n     = len(comps)
    if n == 0:
        return

    # ── Grid positions ─────────────────────────────────────────────────
    cols_per_row = min(4, math.ceil(math.sqrt(n)))
    positions    = {}

    for i, comp in enumerate(comps):
        row       = i // cols_per_row
        col       = i %  cols_per_row
        row_count = min(cols_per_row, n - row * cols_per_row)
        x_offset  = (cols_per_row - row_count) / 2.0
        positions[comp["name"]] = (
            (col + x_offset) * 3.5,
            -(row * 3.0)
        )

    # ── Edge lines ─────────────────────────────────────────────────────
    edge_traces = []
    drawn       = set()

    folder_to_comp = {}
    for comp in comps:
        folder_to_comp[comp.get("folder","").lower()] = comp["name"]
        folder_to_comp[comp["name"].lower()]           = comp["name"]

    for edge in edges:
        if edge.get("type") != "local":
            continue
        sf = edge["from"].split("/")[0].lower() if "/" in edge["from"] else "root"
        df = edge["to"].split("/")[0].lower()   if "/" in edge["to"]   else "root"
        sc = folder_to_comp.get(sf)
        dc = folder_to_comp.get(df)
        if not sc or not dc or sc == dc:
            continue
        key = f"{sc}→{dc}"
        if key in drawn or sc not in positions or dc not in positions:
            continue
        drawn.add(key)
        x0, y0 = positions[sc]
        x1, y1 = positions[dc]
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(width=2, color="rgba(88,166,255,0.7)"),
            hoverinfo="none",
            showlegend=False,
        ))

    # Fallback sequential edges if none found
    if not drawn and n > 1:
        for i in range(min(n-1, 6)):
            c1, c2 = comps[i]["name"], comps[i+1]["name"]
            if c1 in positions and c2 in positions:
                x0,y0 = positions[c1]; x1,y1 = positions[c2]
                edge_traces.append(go.Scatter(
                    x=[x0,x1,None], y=[y0,y1,None],
                    mode="lines",
                    line=dict(width=1, color="rgba(88,166,255,0.3)", dash="dot"),
                    hoverinfo="none", showlegend=False,
                ))

    # ── ONE scatter trace per node ─────────────────────────────────────
    # This is the ONLY way to guarantee different colors per node in Plotly
    node_traces = []
    for idx, comp in enumerate(comps):
        name       = comp["name"]
        x, y       = positions[name]
        file_count = comp.get("file_count", len(comp.get("files", [])))
        color      = _get_color(idx)        # always a valid hex color
        size       = max(40, min(75, 28 + file_count * 5))
        icon       = comp.get("icon", "📁")

        node_traces.append(go.Scatter(
            x          = [x],
            y          = [y],
            mode       = "markers+text",
            marker     = dict(
                size    = size,
                color   = color,            # single string — Plotly always respects this
                opacity = 1.0,
                line    = dict(width=2, color="#ffffff"),
            ),
            text          = [f"{icon} {name}"],
            textposition  = "bottom center",
            textfont      = dict(size=11, color="#e6edf3", family="Arial"),
            name          = name,
            showlegend    = False,
            hovertemplate = (
                f"<b>{icon} {name}</b><br>"
                f"Files: {file_count}<br>"
                f"<extra></extra>"
            ),
        ))

    # ── Axis ranges ────────────────────────────────────────────────────
    all_x = [p[0] for p in positions.values()]
    all_y = [p[1] for p in positions.values()]
    xr    = [min(all_x)-1.5, max(all_x)+1.5]
    yr    = [min(all_y)-2.0, max(all_y)+2.0]
    rows  = math.ceil(n / cols_per_row)

    fig = go.Figure(data=edge_traces + node_traces)
    fig.update_layout(
        title       = dict(text=f"Module Architecture ({n} components)",
                           font=dict(size=14, color="#e6edf3"), x=0.5),
        paper_bgcolor = "#0d1117",
        plot_bgcolor  = "#161b22",
        height        = max(420, rows * 170 + 160),
        margin        = dict(t=60, b=70, l=20, r=20),
        xaxis         = dict(showgrid=False, zeroline=False,
                             showticklabels=False, range=xr),
        yaxis         = dict(showgrid=False, zeroline=False,
                             showticklabels=False, range=yr),
        hovermode     = "closest",
        font          = dict(color="#e6edf3"),
    )
    fig.add_annotation(
        text      = "⬤ Node size = file count  |  Lines = import relationships  |  Hover for details",
        xref="paper", yref="paper", x=0.5, y=-0.1,
        showarrow = False,
        font      = dict(size=10, color="#8b949e"),
        align     = "center",
    )
    st.plotly_chart(fig, use_container_width=True)


def _draw_architecture_plotly(components: list, edges: list):
    """
    Draw a structured architecture diagram using Plotly.
    - Nodes arranged in a GRID layout (not circle) for clarity
    - Each node colored by component type
    - Arrows show dependencies
    - No external APIs needed
    """
    import math
    import plotly.graph_objects as go

    # Limit to 12 components max
    comps = components[:12]
    n     = len(comps)

    if n == 0:
        return go.Figure()

    # ---- GRID layout ----
    # Arrange nodes in rows of 3-4 for a structured look
    cols_per_row = min(4, math.ceil(math.sqrt(n)))
    rows         = math.ceil(n / cols_per_row)

    positions = {}
    for i, comp in enumerate(comps):
        row = i // cols_per_row
        col = i %  cols_per_row
        # Center each row
        row_count = min(cols_per_row, n - row * cols_per_row)
        x_offset  = (cols_per_row - row_count) / 2
        x = (col + x_offset) * 3.0
        y = -row * 2.5  # negative so top row is highest
        positions[comp["name"]] = (x, y)

    # ---- Color palette — ensure valid colors ----
    DEFAULT_COLORS = [
        "#2196F3", "#4CAF50", "#F44336", "#FF9800", "#9C27B0",
        "#00BCD4", "#E91E63", "#607D8B", "#795548", "#8BC34A",
        "#FF5722", "#3F51B5"
    ]

    def safe_color(comp, idx):
        c = comp.get("color", "")
        if c and c.startswith("#") and len(c) in (4, 7):
            return c
        return DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]

    # ---- Build edge lines ----
    edge_traces = []

    # Map folder names to component names for edge lookup
    folder_to_comp = {}
    for comp in comps:
        folder_to_comp[comp.get("folder", "").lower()] = comp["name"]
        folder_to_comp[comp["name"].lower()]            = comp["name"]

    # Draw edges from dependency data
    drawn_edges = set()
    for edge in edges:
        if edge.get("type") != "local":
            continue
        src_folder = edge["from"].split("/")[0].lower() if "/" in edge["from"] else "root"
        dst_folder = edge["to"].split("/")[0].lower()   if "/" in edge["to"]   else "root"

        src_comp = folder_to_comp.get(src_folder)
        dst_comp = folder_to_comp.get(dst_folder)

        if not src_comp or not dst_comp or src_comp == dst_comp:
            continue

        edge_key = f"{src_comp}→{dst_comp}"
        if edge_key in drawn_edges:
            continue
        drawn_edges.add(edge_key)

        if src_comp in positions and dst_comp in positions:
            x0, y0 = positions[src_comp]
            x1, y1 = positions[dst_comp]
            edge_traces.append(go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(width=2, color="rgba(88,166,255,0.6)"),
                hoverinfo="none",
                showlegend=False,
            ))

    # If no real edges detected, connect sequential components
    if not drawn_edges and n > 1:
        for i in range(min(n - 1, 5)):
            c1 = comps[i]["name"]
            c2 = comps[i + 1]["name"]
            if c1 in positions and c2 in positions:
                x0, y0 = positions[c1]
                x1, y1 = positions[c2]
                edge_traces.append(go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode="lines",
                    line=dict(width=1, color="rgba(88,166,255,0.3)", dash="dot"),
                    hoverinfo="none",
                    showlegend=False,
                ))

    # ---- Build one scatter trace per node (fixes color issue) ----
    # Plotly colors work correctly when each node is its own trace
    node_traces = []
    for idx, comp in enumerate(comps):
        x, y       = positions[comp["name"]]
        file_count = comp.get("file_count", len(comp.get("files", [])))
        color      = safe_color(comp, idx)
        size       = max(35, min(70, 25 + file_count * 4))
        label      = comp["name"]
        icon       = comp.get("icon", "📁")

        node_traces.append(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            marker=dict(
                size=size,
                color=color,           # single color string per trace — always works
                line=dict(width=2, color="white"),
                opacity=1.0,
            ),
            text=[f"{icon} {label}"],
            textposition="bottom center",
            textfont=dict(size=11, color="#e6edf3"),
            hovertemplate=(
                f"<b>{icon} {comp['name']}</b><br>"
                f"Files: {file_count}<br>"
                f"Folder: {comp.get('folder', '?')}<br>"
                f"<extra></extra>"
            ),
            name=comp["name"],
            showlegend=False,
        ))

    # ---- Assemble figure ----
    all_traces = edge_traces + node_traces

    # Calculate axis ranges
    all_x = [p[0] for p in positions.values()]
    all_y = [p[1] for p in positions.values()]
    x_pad = 1.5
    y_pad = 1.5
    x_range = [min(all_x) - x_pad, max(all_x) + x_pad]
    y_range = [min(all_y) - y_pad, max(all_y) + y_pad + 1]

    fig = go.Figure(data=all_traces)

    fig.update_layout(
        title=dict(
            text=f"Module Architecture  ({n} components)",
            font=dict(size=14, color="#e6edf3"),
            x=0.5,
        ),
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        height=max(400, rows * 150 + 150),
        margin=dict(t=60, b=60, l=20, r=20),
        xaxis=dict(
            showgrid=False, zeroline=False,
            showticklabels=False,
            range=x_range,
        ),
        yaxis=dict(
            showgrid=False, zeroline=False,
            showticklabels=False,
            range=y_range,
        ),
        hovermode="closest",
        font=dict(color="#e6edf3"),
        dragmode="pan",
    )

    fig.add_annotation(
        text="⬤ Node size = number of files  |  Lines = import relationships  |  Hover for details",
        xref="paper", yref="paper",
        x=0.5, y=-0.08,
        showarrow=False,
        font=dict(size=10, color="#8b949e"),
        align="center",
    )

    return fig 

def _draw_architecture_plotly(components: list, edges: list) -> "go.Figure":
    """
    Draw architecture diagram using Plotly scatter plot.
    Nodes = components, Edges = dependency arrows.
    No external libraries needed beyond plotly (already installed).
    """
    import math
    import plotly.graph_objects as go

    # ---- Layout: arrange nodes in a circle ----
    n     = min(len(components), 12)
    comps = components[:n]

    # Position nodes in a circle
    positions = {}
    for i, comp in enumerate(comps):
        angle        = (2 * math.pi * i) / n - math.pi / 2
        radius       = 2.5
        x            = radius * math.cos(angle)
        y            = radius * math.sin(angle)
        positions[comp["name"]] = (x, y)

    # ---- Build edge traces ----
    edge_traces = []

    # Get folder-level edges from edges list
    folder_edges = {}
    for edge in edges:
        if edge.get("type") == "local":
            src_folder = edge["from"].split("/")[0].title() if "/" in edge["from"] else "Root"
            dst_folder = edge["to"].split("/")[0].title()   if "/" in edge["to"]   else "Root"
            if src_folder != dst_folder and src_folder in positions and dst_folder in positions:
                key = f"{src_folder}->{dst_folder}"
                folder_edges[key] = folder_edges.get(key, 0) + 1

    for edge_key, count in folder_edges.items():
        src_name, dst_name = edge_key.split("->")
        if src_name in positions and dst_name in positions:
            x0, y0 = positions[src_name]
            x1, y1 = positions[dst_name]
            # Draw arrow line
            edge_traces.append(go.Scatter(
                x=[x0, x1, None], y=[y0, y1, None],
                mode="lines",
                line=dict(width=max(1, min(count, 4)), color="#58a6ff", dash="solid"),
                hoverinfo="none",
                showlegend=False,
            ))
            # Arrow label (midpoint)
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            edge_traces.append(go.Scatter(
                x=[mx], y=[my],
                mode="text",
                text=[f"{count}"],
                textfont=dict(size=9, color="#8b949e"),
                hoverinfo="none",
                showlegend=False,
            ))

    # ---- Build node trace ----
    node_x, node_y       = [], []
    node_text            = []
    node_hover           = []
    node_colors          = []
    node_sizes           = []

    for comp in comps:
        x, y       = positions[comp["name"]]
        file_count = comp.get("file_count", len(comp.get("files", [])))

        node_x.append(x)
        node_y.append(y)
        node_text.append(f"{comp.get('icon','📁')} {comp['name']}")
        node_hover.append(
            f"<b>{comp['name']}</b><br>"
            f"Files: {file_count}<br>"
            f"Folder: {comp.get('folder','?')}"
        )
        node_colors.append(comp.get("color", "#607D8B"))
        node_sizes.append(max(40, min(80, 30 + file_count * 3)))

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        hoverinfo="text",
        hovertext=node_hover,
        text=node_text,
        textposition="bottom center",
        textfont=dict(size=11, color="#e6edf3"),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color="#30363d"),
            opacity=0.9,
        ),
        showlegend=False,
    )

    # ---- Assemble figure ----
    fig = go.Figure(data=edge_traces + [node_trace])

    fig.update_layout(
        title=dict(
            text="Module Architecture",
            font=dict(size=14, color="#e6edf3"),
            x=0.5,
        ),
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        height=500,
        margin=dict(t=50, b=20, l=20, r=20),
        xaxis=dict(
            showgrid=False, zeroline=False,
            showticklabels=False, range=[-4, 4]
        ),
        yaxis=dict(
            showgrid=False, zeroline=False,
            showticklabels=False, range=[-4, 4]
        ),
        hovermode="closest",
        font=dict(color="#e6edf3"),
    )

    # Add a legend / key
    fig.add_annotation(
        text="⬤ Node size = number of files  |  Lines = import relationships",
        xref="paper", yref="paper",
        x=0.5, y=-0.02,
        showarrow=False,
        font=dict(size=10, color="#8b949e"),
        align="center",
    )

    return fig
# ============================================================
# PASTE THIS ENTIRE FUNCTION INTO app.py
# Replace the existing _show_chatbot() function with this one
# ============================================================

def _show_chatbot():
    """Display the enhanced Repository Chatbot with Time Machine RAG."""
    st.markdown("### 🤖 Repository Knowledge Chatbot")

    chatbot = st.session_state.chatbot

    if not chatbot or not chatbot.is_indexed:
        st.warning("⚠️ Chatbot not initialized. Please run the analysis first.")
        return

    # ── Feed time machine data into chatbot if available ──────────────────
    tm_result = st.session_state.get("time_machine_result")
    if tm_result and not chatbot.time_machine:
        chatbot.time_machine  = tm_result
        chatbot.repo_summary  = chatbot._create_repo_summary()

    # ── Description ───────────────────────────────────────────────────────
    st.markdown(
        "<div style='background:#162032;border:1px solid #1f6feb;border-radius:10px;"
        "padding:14px;margin-bottom:16px;'>"
        "🧠 Ask me anything about this repository in natural language. "
        "I know the <b>code files</b>, <b>security issues</b>, <b>commit history</b>, "
        "<b>risk timeline</b>, <b>architecture</b>, and <b>predicted future risks</b>."
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Suggested questions — grouped by category ─────────────────────────
    st.markdown("**💡 Try asking:**")

    tab_code, tab_security, tab_timeline, tab_predict = st.tabs([
        "📦 Code & Architecture",
        "🔒 Security & Risk",
        "⏳ Timeline & History",
        "🔮 Predictions",
    ])

    def _quick_ask(suggestion: str, key: str):
        if st.button(suggestion, key=key, use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": suggestion})
            with st.spinner("🤔 Thinking..."):
                response = chatbot.ask(suggestion)
            st.session_state.chat_history.append({
                "role":    "assistant",
                "content": response["answer"],
                "files":   response.get("relevant_files", []),
                "commits": response.get("relevant_commits", []),
            })
            st.rerun()

    with tab_code:
        c1, c2 = st.columns(2)
        with c1:
            _quick_ask("Explain the overall architecture", "q_arch")
            _quick_ask("What frameworks are being used?", "q_fw")
        with c2:
            _quick_ask("Which file has the most issues?", "q_issues")
            _quick_ask("How is the codebase structured?", "q_struct")

    with tab_security:
        c1, c2 = st.columns(2)
        with c1:
            _quick_ask("What are the biggest security risks?", "q_sec")
            _quick_ask("Which files are most dangerous?", "q_danger")
        with c2:
            _quick_ask("Are there any vulnerable dependencies?", "q_dep")
            _quick_ask("What is the overall risk level?", "q_risk")

    with tab_timeline:
        c1, c2 = st.columns(2)
        with c1:
            _quick_ask("Show me the commit history", "q_commits")
            _quick_ask("Which files caused most issues in recent commits?", "q_recent")
        with c2:
            _quick_ask("How has the risk changed over time?", "q_risktrend")
            _quick_ask("Who made the most changes?", "q_authors")

    with tab_predict:
        c1, c2 = st.columns(2)
        with c1:
            _quick_ask("Predict risky files for next month", "q_pred")
            _quick_ask("Which files will likely have bugs?", "q_bugs")
        with c2:
            _quick_ask("What should we fix first?", "q_fix")
            _quick_ask("Show high churn files", "q_churn")

    st.markdown("---")

    # ── Chat history ──────────────────────────────────────────────────────
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(
                f"<div class='chat-user'>👤 <strong>You</strong><br>{message['content']}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='chat-bot'>🧠 <strong>RepoMind</strong><br>{message['content']}</div>",
                unsafe_allow_html=True,
            )
            # Show source references
            refs = []
            if message.get("files"):
                refs.append(f"📂 Files: {', '.join(message['files'][:3])}")
            if message.get("commits"):
                refs.append(f"🔖 Commits: {', '.join(message['commits'][:3])}")
            if refs:
                st.markdown(f"<small style='color:#8b949e;'>{' &nbsp;|&nbsp; '.join(refs)}</small>", unsafe_allow_html=True)

    # ── Input ─────────────────────────────────────────────────────────────
    st.markdown("---")
    user_input = st.text_input(
        "Ask anything...",
        placeholder='e.g. "Which files caused most bugs last 3 commits?" or "Show architecture before latest commit"',
        key="chat_input",
        label_visibility="collapsed",
    )

    col_send, col_clear = st.columns([1, 5])
    with col_send:
        send_clicked = st.button("Send 💬", use_container_width=True)
    with col_clear:
        if st.button("🗑️ Clear chat", use_container_width=False):
            st.session_state.chat_history = []
            st.rerun()

    if send_clicked and user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("🤔 Thinking..."):
            response = chatbot.ask(user_input)
        st.session_state.chat_history.append({
            "role":    "assistant",
            "content": response["answer"],
            "files":   response.get("relevant_files", []),
            "commits": response.get("relevant_commits", []),
        })
        st.rerun()


# ============================================
# DASHBOARD - Show results after analysis
# Defined after display functions so helpers exist when called.
# ============================================
if st.session_state.analysis_complete:

    results   = st.session_state.results
    repo_info = st.session_state.repo_info

    if st.session_state.get("dashboard_open_fx", False):
        st.markdown(
            """
            <style>
            .main .block-container > div[data-testid="stVerticalBlock"] > div {
                animation: agentPanelReveal 0.62s cubic-bezier(0.16, 1, 0.3, 1);
                animation-fill-mode: both;
                will-change: transform, opacity;
            }
            .main .block-container > div[data-testid="stVerticalBlock"] > div:nth-child(1) { animation-delay: 0.02s; }
            .main .block-container > div[data-testid="stVerticalBlock"] > div:nth-child(2) { animation-delay: 0.05s; }
            .main .block-container > div[data-testid="stVerticalBlock"] > div:nth-child(3) { animation-delay: 0.08s; }
            .main .block-container > div[data-testid="stVerticalBlock"] > div:nth-child(4) { animation-delay: 0.11s; }
            .main .block-container > div[data-testid="stVerticalBlock"] > div:nth-child(5) { animation-delay: 0.14s; }
            .main .block-container > div[data-testid="stVerticalBlock"] > div:nth-child(6) { animation-delay: 0.17s; }
            .main .block-container > div[data-testid="stVerticalBlock"] > div:nth-child(7) { animation-delay: 0.20s; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.session_state.dashboard_open_fx = False

    # ---- Repo Header ----
    analyzed_url = st.session_state.get("analyzed_url", "")
    if analyzed_url:
        st.caption(f"Analyzed URL: {analyzed_url}")

    st.markdown(f"""
    <div style="background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <h2 style="margin:0; color: #58a6ff;">📦 {repo_info.get('name', 'Repository')}</h2>
        <p style="color: #8b949e; margin: 4px 0;">{repo_info.get('description', '')}</p>
        <p style="color: #8b949e; font-size: 0.85rem; margin: 0;">
            ⭐ {repo_info.get('stars', 0)} stars  |  
            🍴 {repo_info.get('forks', 0)} forks  |  
            ⚠️ {repo_info.get('open_issues', 0)} open issues  |  
            🔤 {repo_info.get('language', 'Unknown')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ---- RepoScore (the "wow" single number) ----
    _display_repo_score(results)

    # ---- Agent Result Tabs ----
    tabs = st.tabs([
        "🔍 Code Review",
        "🔒 Security",
        "📄 Docs",
        "📦 Dependencies",
        "🔧 Auto-Fix",
        "🗺️ Risk Heatmap",
        "🏗️ Architecture",
        "🤖 Chatbot",
        "⏳ Time Machine",
    ])

    # TAB 1: Code Review
    with tabs[0]:
        _show_code_review(results.get("code_review", {}))

    # TAB 2: Security
    with tabs[1]:
        _show_security(results.get("security", {}))

    # TAB 3: Documentation
    with tabs[2]:
        _show_documentation(results.get("documentation", {}))

    # TAB 4: Dependencies
    with tabs[3]:
        _show_dependencies(results.get("dependency", {}))

    # TAB 5: Bug Fix
    with tabs[4]:
        _show_bug_fixes(results.get("bug_fix", {}))

    # TAB 6: Risk Heatmap
    with tabs[5]:
        _show_risk_heatmap(results.get("risk_heatmap", {}))

    # TAB 7: Architecture
    with tabs[6]:
        _show_architecture(results.get("architecture", {}))

    # TAB 8: Chatbot
    with tabs[7]:
        _show_chatbot()
    with tabs[8]:
        show_time_machine(st.session_state.get("time_machine_result") or {})

    # ---- PDF Download ----
    st.markdown("---")
    st.markdown("### 📥 Download Report")
    col_pdf1, col_pdf2, col_pdf3 = st.columns([1, 1, 2])
    with col_pdf1:
        if st.button("📄 Generate PDF Report", use_container_width=True, key="generate_pdf_active"):
            with st.spinner("📄 Generating PDF..."):
                try:
                    pdf_bytes = generate_repomind_report(
                        st.session_state.results,
                        st.session_state.repo_info,
                    )
                    repo_name = st.session_state.repo_info.get("name", "repo")
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"repomind_{repo_name}_report.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="download_pdf_active",
                    )
                    st.success("✅ PDF ready! Click Download PDF above.")
                except Exception as e:
                    st.error(f"❌ PDF error: {str(e)}")

    # ---- Final Full PDF (All Agents + Time Machine) ----
    st.markdown("### ✅ Final Full Analysis PDF")
    st.caption("This final report includes all agent outputs including Time Machine analysis.")
    with st.container():
        if st.button("🧾 Generate Final Full PDF", use_container_width=True, key="generate_full_pdf_end"):
            with st.spinner("🧾 Building final full analysis PDF..."):
                try:
                    full_results = dict(st.session_state.results)
                    full_results["time_machine"] = st.session_state.get("time_machine_result") or {}

                    full_pdf_bytes = generate_repomind_report(
                        full_results,
                        st.session_state.repo_info,
                    )
                    repo_name = st.session_state.repo_info.get("name", "repo")
                    st.download_button(
                        label="⬇️ Download Final Full PDF",
                        data=full_pdf_bytes,
                        file_name=f"repomind_{repo_name}_full_analysis_report.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="download_full_pdf_end",
                    )
                    st.success("✅ Final full PDF is ready. Click Download Final Full PDF.")
                except Exception as e:
                    st.error(f"❌ Final PDF error: {str(e)}")


    # ---- Reset Button ----
    st.markdown("---")
    if st.button("🔄 Analyze Another Repository"):
        st.session_state.analysis_complete = False
        st.session_state.results           = {}
        st.session_state.chatbot           = None
        st.session_state.chat_history      = []
        st.session_state.repo_files        = {}
        st.session_state.repo_info         = {}
        st.rerun()
def _patch_language(filepath: str) -> str:
    ext_map = {".py":"python",".js":"javascript",".ts":"typescript",
               ".cs":"csharp",".java":"java",".go":"go"}
    for ext, lang in ext_map.items():
        if filepath.endswith(ext): return lang
    return "python"
# ============================================================
# RepoMind - Hackathon Winning Features
# Add these to your app.py to impress judges
# ============================================================

# ============================================================
# FEATURE 1: ANIMATED HERO WITH TYPING EFFECT
# Replace your hero banner st.markdown with this function
# ============================================================

def _render_animated_hero():
    """Hero section with typing animation and particle effect."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');

    .hero-wrapper {
        background: linear-gradient(135deg, #0d1117 0%, #1a1f3c 50%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 20px;
        padding: 50px 40px;
        text-align: center;
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
    }

    /* Animated gradient border */
    .hero-wrapper::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: 20px;
        padding: 2px;
        background: linear-gradient(90deg, #58a6ff, #bc8cff, #79c0ff, #58a6ff);
        background-size: 300% 100%;
        -webkit-mask: linear-gradient(#fff 0 0) content-box,
                      linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        animation: borderMove 3s linear infinite;
    }

    @keyframes borderMove {
        0%   { background-position: 0% 50%; }
        100% { background-position: 300% 50%; }
    }

    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #58a6ff, #bc8cff, #79c0ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-size: 200% auto;
        animation: textShine 3s linear infinite;
        margin: 0;
    }

    @keyframes textShine {
        0%   { background-position: 0% center; }
        100% { background-position: 200% center; }
    }

    .hero-subtitle {
        color: #8b949e;
        font-size: 1.15rem;
        margin-top: 10px;
        font-family: 'Space Grotesk', sans-serif;
    }

    /* Typing cursor */
    .typing-text {
        color: #58a6ff;
        font-size: 1rem;
        font-family: monospace;
        margin-top: 8px;
    }
    .cursor {
        display: inline-block;
        width: 2px;
        height: 1em;
        background: #58a6ff;
        animation: blink 0.7s infinite;
        vertical-align: middle;
        margin-left: 2px;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0; }
    }

    /* Badge row */
    .badge-row {
        display: flex;
        gap: 8px;
        justify-content: center;
        flex-wrap: wrap;
        margin-top: 20px;
    }
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        animation: fadeInUp 0.5s ease forwards;
        opacity: 0;
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(10px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .b1 { background:rgba(88,166,255,0.15);  color:#58a6ff;  border:1px solid #58a6ff;  animation-delay:0.1s; }
    .b2 { background:rgba(248,81,73,0.15);   color:#f85149;  border:1px solid #f85149;  animation-delay:0.2s; }
    .b3 { background:rgba(210,153,34,0.15);  color:#d29922;  border:1px solid #d29922;  animation-delay:0.3s; }
    .b4 { background:rgba(227,179,65,0.15);  color:#e3b341;  border:1px solid #e3b341;  animation-delay:0.4s; }
    .b5 { background:rgba(63,185,80,0.15);   color:#3fb950;  border:1px solid #3fb950;  animation-delay:0.5s; }
    .b6 { background:rgba(188,140,255,0.15); color:#bc8cff;  border:1px solid #bc8cff;  animation-delay:0.6s; }
    .b7 { background:rgba(121,192,255,0.15); color:#79c0ff;  border:1px solid #79c0ff;  animation-delay:0.7s; }
    .b8 { background:rgba(63,185,80,0.15);   color:#3fb950;  border:1px solid #3fb950;  animation-delay:0.8s; }

    /* Floating dots background */
    .dot {
        position: absolute;
        border-radius: 50%;
        opacity: 0.15;
        animation: float linear infinite;
    }
    @keyframes float {
        0%   { transform: translateY(100px); opacity: 0; }
        10%  { opacity: 0.15; }
        90%  { opacity: 0.15; }
        100% { transform: translateY(-100px); opacity: 0; }
    }
    </style>

    <div class="hero-wrapper">
        <!-- Floating dots -->
        <div class="dot" style="width:6px;height:6px;background:#58a6ff;left:10%;animation-duration:4s;animation-delay:0s;"></div>
        <div class="dot" style="width:4px;height:4px;background:#bc8cff;left:25%;animation-duration:6s;animation-delay:1s;"></div>
        <div class="dot" style="width:8px;height:8px;background:#79c0ff;left:75%;animation-duration:5s;animation-delay:2s;"></div>
        <div class="dot" style="width:5px;height:5px;background:#3fb950;left:90%;animation-duration:7s;animation-delay:0.5s;"></div>

        <p class="hero-title">🧠 RepoMind</p>
        <p class="hero-subtitle">AI-Powered Repository Intelligence Platform</p>
        <p class="typing-text" id="typing-demo">
            &gt; Analyzing your codebase...<span class="cursor"></span>
        </p>

        <div class="badge-row">
            <span class="badge b1">🔍 Code Review</span>
            <span class="badge b2">🔒 Security</span>
            <span class="badge b3">📄 Documentation</span>
            <span class="badge b4">📦 Dependencies</span>
            <span class="badge b5">🔧 Auto-Fix</span>
            <span class="badge b6">🗺️ Risk Heatmap</span>
            <span class="badge b7">🏗️ Architecture</span>
            <span class="badge b8">🤖 AI Chatbot</span>
        </div>
    </div>

    <script>
    // Typing animation for the subtitle
    const texts = [
        "Analyzing your codebase...",
        "Detecting vulnerabilities...",
        "Generating auto-patches...",
        "Building architecture diagrams...",
        "Powered by Gemini AI...",
    ];
    let textIndex = 0;
    let charIndex  = 0;
    let isDeleting = false;
    const el = document.getElementById("typing-demo");

    function type() {
        if (!el) return;
        const current = texts[textIndex];
        if (isDeleting) {
            charIndex--;
        } else {
            charIndex++;
        }
        el.innerHTML = "&gt; " + current.substring(0, charIndex) +
                       '<span class="cursor"></span>';
        let delay = isDeleting ? 40 : 80;
        if (!isDeleting && charIndex === current.length) {
            delay = 1500;
            isDeleting = true;
        } else if (isDeleting && charIndex === 0) {
            isDeleting = false;
            textIndex = (textIndex + 1) % texts.length;
            delay = 300;
        }
        setTimeout(type, delay);
    }
    setTimeout(type, 500);
    </script>
    """, unsafe_allow_html=True)


# ============================================================
# FEATURE 2: ANIMATED COUNTER METRICS
# Replace your st.metric() calls in _display_repo_score with this
# ============================================================

def _animated_metric(label: str, value, delta=None, color="#58a6ff"):
    """
    Display a metric with an animated count-up effect.
    Use instead of st.metric() for dramatic effect.
    """
    delta_html = ""
    if delta:
        delta_color = "#3fb950" if str(delta).startswith("+") else "#f85149"
        delta_html  = f"<div style='color:{delta_color};font-size:0.85rem;'>{delta}</div>"

    st.markdown(f"""
    <div style='background:#161b22;border:1px solid #30363d;border-radius:10px;
    padding:16px;text-align:center;transition:all 0.3s;' 
    onmouseover="this.style.borderColor='{color}';this.style.transform='translateY(-2px)'"
    onmouseout="this.style.borderColor='#30363d';this.style.transform='translateY(0)'">
        <div style='color:#8b949e;font-size:0.8rem;margin-bottom:4px;'>{label}</div>
        <div class="counter" data-target="{value}"
        style='color:{color};font-size:2rem;font-weight:700;font-family:Space Grotesk,sans-serif;'>
            0
        </div>
        {delta_html}
    </div>

    <script>
    (function() {{
        const counters = document.querySelectorAll('.counter');
        counters.forEach(counter => {{
            const target = parseInt(counter.getAttribute('data-target')) || 0;
            const duration = 1200;
            const step = target / (duration / 16);
            let current = 0;
            const timer = setInterval(() => {{
                current += step;
                if (current >= target) {{
                    counter.textContent = target;
                    clearInterval(timer);
                }} else {{
                    counter.textContent = Math.floor(current);
                }}
            }}, 16);
        }});
    }})();
    </script>
    """, unsafe_allow_html=True)


# ============================================================
# FEATURE 3: CONFETTI ON GOOD SCORE
# Call this after _display_repo_score() if score >= 80
# ============================================================

def _show_confetti_if_good(score: int):
    """Show confetti animation if repo score is excellent."""
    if score < 80:
        return

    st.markdown(f"""
    <div style='text-align:center;padding:10px;'>
        <span style='font-size:1.5rem;'>🎉</span>
        <span style='color:#3fb950;font-weight:700;font-size:1.1rem;'> 
            Excellent repository! Score: {score}/100
        </span>
        <span style='font-size:1.5rem;'>🎉</span>
    </div>

    <style>
    @keyframes confetti-fall {{
        0%   {{ transform: translateY(-100px) rotate(0deg);   opacity: 1; }}
        100% {{ transform: translateY(600px)  rotate(720deg); opacity: 0; }}
    }}
    .confetti-piece {{
        position: fixed;
        width: 10px;
        height: 10px;
        top: 0;
        animation: confetti-fall linear forwards;
        z-index: 9999;
    }}
    </style>

    <script>
    (function() {{
        const colors = ['#58a6ff','#3fb950','#f85149','#e3b341','#bc8cff','#79c0ff'];
        const container = document.body;
        for (let i = 0; i < 80; i++) {{
            const piece = document.createElement('div');
            piece.className = 'confetti-piece';
            piece.style.left       = Math.random() * 100 + 'vw';
            piece.style.background = colors[Math.floor(Math.random() * colors.length)];
            piece.style.width      = (Math.random() * 8 + 5) + 'px';
            piece.style.height     = (Math.random() * 8 + 5) + 'px';
            piece.style.borderRadius = Math.random() > 0.5 ? '50%' : '0';
            piece.style.animationDuration = (Math.random() * 2 + 1.5) + 's';
            piece.style.animationDelay    = (Math.random() * 2)         + 's';
            container.appendChild(piece);
            setTimeout(() => piece.remove(), 4000);
        }}
    }})();
    </script>
    """, unsafe_allow_html=True)


# ============================================================
# FEATURE 4: SMOOTH PAGE TRANSITION
# Add this once at the top of app.py after st.set_page_config
# ============================================================

def _add_page_transitions():
    """Add smooth fade-in animation when page loads."""
    st.markdown("""
    <style>
    /* Fade in entire page on load */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0);   }
    }
    .main .block-container {
        animation: fadeIn 0.4s ease-out;
    }

    /* Smooth tab transitions */
    [data-baseweb="tab-panel"] {
        animation: fadeIn 0.3s ease-out;
    }

    /* Hover effect on expanders */
    .streamlit-expanderHeader:hover {
        background: rgba(88,166,255,0.05) !important;
        border-radius: 8px !important;
    }

    /* Smooth metric hover */
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        transition: transform 0.2s ease;
        border-color: #58a6ff !important;
    }

    /* Progress bar glow */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #58a6ff, #bc8cff) !important;
        box-shadow: 0 0 10px rgba(88,166,255,0.5) !important;
        border-radius: 10px !important;
    }

    /* Button hover glow */
    .stButton > button:hover {
        box-shadow: 0 0 20px rgba(46,160,67,0.5) !important;
        transform: translateY(-2px) !important;
    }

    /* Scrollbar styling */
    ::-webkit-scrollbar       { width: 6px; }
    ::-webkit-scrollbar-track { background: #0d1117; }
    ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #58a6ff; }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# FEATURE 5: SCORE IMPROVEMENT TIPS
# Add this below the RepoScore gauge for instant wow factor
# ============================================================

def post_github_pr_comment(repo_url, pr_number, results, repo_info, github_token):
    """Posts analysis summary as a GitHub PR comment."""
    import requests

    parts  = repo_url.rstrip("/").split("/")
    owner  = parts[-2]
    repo   = parts[-1].replace(".git","")

    sec    = results.get("security",{})
    cr     = results.get("code_review",{})
    dep    = results.get("dependency",{})
    bf     = results.get("bug_fix",{})
    doc    = results.get("documentation",{})

    scores  = [results.get(k,{}).get("score") for k in
               ["code_review","security","documentation","dependency"]]
    scores  = [s for s in scores if s is not None]
    overall = int(sum(scores)/len(scores)) if scores else 0

    grade_emoji = ("🟢" if overall>=80 else "🟡" if overall>=60
                   else "🟠" if overall>=40 else "🔴")
    risk_level  = sec.get("risk_level","UNKNOWN")
    risk_emoji  = {"CRITICAL":"🚨","HIGH":"🔴","MEDIUM":"🟡",
                   "LOW":"🟢","SAFE":"✅"}.get(risk_level,"⚠️")

    total_patches = bf.get("stats",{}).get("total_patches",0)
    vuln_count    = sec.get("total_found",0)
    issue_count   = len(cr.get("issues",[]))
    vuln_pkgs     = len(dep.get("vulnerabilities",[]))
    doc_coverage  = doc.get("doc_coverage",0)

    comment = f"""## 🧠 RepoMind AI Analysis Report

> Automated analysis by RepoMind — AI-Powered Repository Intelligence

---

### {grade_emoji} RepoScore™: **{overall}/100**

| Agent | Score | Findings |
|-------|-------|----------|
| 🔍 Code Review | {cr.get('score','N/A')}/100 | {issue_count} issues |
| 🔒 Security | {sec.get('score','N/A')}/100 | {risk_emoji} {risk_level} — {vuln_count} vulnerabilities |
| 📄 Documentation | {doc.get('score','N/A')}/100 | {doc_coverage}% coverage |
| 📦 Dependencies | {dep.get('score','N/A')}/100 | {vuln_pkgs} vulnerable packages |

---

### 🔒 Security Findings ({vuln_count} total)
"""
    vulns = sec.get("vulnerabilities", [])
    if vulns:
        for v in vulns[:5]:
            sev_e = {"CRITICAL":"🚨","HIGH":"🔴","MEDIUM":"🟡",
                     "LOW":"🟢"}.get(v.get("severity","LOW"),"⚠️")
            comment += (f"- {sev_e} **{v.get('type','')}** "
                       f"in `{v.get('file','')}` line {v.get('line','?')}\n")
        if len(vulns) > 5:
            comment += f"\n_...and {len(vulns)-5} more_\n"
    else:
        comment += "_No vulnerabilities detected_ ✅\n"

    comment += f"\n---\n\n### 🔧 Auto-Patches Generated ({total_patches})\n"
    if total_patches > 0:
        for p in bf.get("patches",[])[:3]:
            comment += (f"- ✅ **{p.get('vulnerability',p.get('issue','Fix'))}** "
                       f"in `{p.get('file','')}` — {p.get('explanation','')[:60]}\n")
    else:
        comment += "_No auto-patches needed_\n"

    if vuln_pkgs > 0:
        comment += f"\n---\n\n### 📦 Vulnerable Packages ({vuln_pkgs})\n"
        for pkg in dep.get("vulnerabilities",[])[:3]:
            comment += (f"- 🔴 **{pkg.get('name','')}** "
                       f"v{pkg.get('version','')} → v{pkg.get('latest_version','latest')}\n")

    comment += f"\n---\n> 🤖 Generated by **RepoMind AI** | Powered by Google Gemini\n"

    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept":        "application/vnd.github.v3+json",
    }
    try:
        response = requests.post(api_url, json={"body": comment},
                                 headers=headers, timeout=15)
        if response.status_code == 201:
            return {"success": True, "url": response.json().get("html_url",""),
                    "message": "Comment posted!"}
        else:
            return {"success": False, "url": "",
                    "message": f"GitHub error {response.status_code}: {response.text[:100]}"}
    except Exception as e:
        return {"success": False, "url": "", "message": str(e)}


def _show_pr_comment_section(results: dict, repo_info: dict):
    """UI section to post results as a GitHub PR comment."""
    import os

    st.markdown("---")
    st.markdown("### 💬 Post to GitHub Pull Request")
    st.caption("Post this analysis as a comment on any GitHub PR")

    col1, col2 = st.columns([2, 1])
    with col1:
        pr_repo = st.text_input(
            "Repository URL",
            value=st.session_state.get("analyzed_url",""),
            placeholder="https://github.com/owner/repo",
            key="pr_repo_url",
        )
        pr_num = st.number_input(
            "Pull Request Number",
            min_value=1, value=1, step=1,
            key="pr_number",
            help="Find PR number in GitHub URL: /pull/42 → enter 42"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        github_token = os.getenv("GITHUB_TOKEN","")
        if not github_token:
            github_token = st.text_input(
                "GitHub Token", type="password",
                key="pr_gh_token",
                help="Token needs repo permission"
            )
        post_clicked = st.button(
            "💬 Post PR Comment",
            use_container_width=True,
            type="primary",
        )

    if post_clicked:
        if not pr_repo or "github.com" not in pr_repo:
            st.error("⚠️ Enter a valid GitHub URL")
            return
        if not github_token:
            st.error("⚠️ GitHub token required")
            return
        with st.spinner("📤 Posting to GitHub..."):
            result = post_github_pr_comment(
                pr_repo, int(pr_num),
                results, repo_info, github_token
            )
        if result["success"]:
            st.success("✅ Comment posted!")
            if result.get("url"):
                st.markdown(f"[🔗 View on GitHub]({result['url']})")
        else:
            st.error(f"❌ Failed: {result['message']}")
def _show_improvement_tips(results: dict):
    """Show 3 quick wins to improve the repo score."""
    tips = []

    sec  = results.get("security",      {})
    cr   = results.get("code_review",   {})
    doc  = results.get("documentation", {})
    dep  = results.get("dependency",    {})

    if sec.get("total_found", 0) > 0:
        tips.append({
            "icon":  "🔒",
            "title": "Fix Security Vulnerabilities",
            "desc":  f"Found {sec['total_found']} vulnerabilities. Check the Auto-Fix tab for patches.",
            "color": "#f85149",
            "impact": "HIGH",
        })

    if len(cr.get("issues", [])) > 5:
        tips.append({
            "icon":  "🔍",
            "title": "Improve Code Quality",
            "desc":  f"{len(cr['issues'])} code issues found. Review the Code Review tab.",
            "color": "#e3b341",
            "impact": "MEDIUM",
        })

    if doc.get("doc_coverage", 100) < 50:
        tips.append({
            "icon":  "📄",
            "title": "Add Missing Documentation",
            "desc":  f"Only {doc.get('doc_coverage',0)}% documented. Check the Docs tab for suggestions.",
            "color": "#d29922",
            "impact": "MEDIUM",
        })

    if len(dep.get("vulnerabilities", [])) > 0:
        tips.append({
            "icon":  "📦",
            "title": "Update Vulnerable Packages",
            "desc":  f"{len(dep['vulnerabilities'])} packages have known CVEs. Run the upgrade commands.",
            "color": "#f85149",
            "impact": "HIGH",
        })

    if not tips:
        tips.append({
            "icon":  "✅",
            "title": "Repository looks healthy!",
            "desc":  "No major issues found. Keep up the good work!",
            "color": "#3fb950",
            "impact": "NONE",
        })

    st.markdown("#### 💡 Quick Wins to Improve Score")
    cols = st.columns(len(tips[:3]))

    for i, (col, tip) in enumerate(zip(cols, tips[:3])):
        with col:
            impact_badge = {
                "HIGH":   "<span style='background:rgba(248,81,73,0.2);color:#f85149;padding:2px 8px;border-radius:10px;font-size:0.7rem;'>HIGH IMPACT</span>",
                "MEDIUM": "<span style='background:rgba(210,153,34,0.2);color:#d29922;padding:2px 8px;border-radius:10px;font-size:0.7rem;'>MED IMPACT</span>",
                "NONE":   "",
            }.get(tip["impact"], "")

            st.markdown(f"""
            <div style='background:#161b22;border:1px solid #30363d;border-top:3px solid {tip["color"]};
            border-radius:10px;padding:16px;height:140px;'>
                <div style='font-size:1.5rem;'>{tip["icon"]}</div>
                <div style='font-weight:700;color:#e6edf3;font-size:0.9rem;margin:6px 0 4px;'>
                    {tip["title"]}
                </div>
                {impact_badge}
                <div style='color:#8b949e;font-size:0.8rem;margin-top:6px;line-height:1.4;'>
                    {tip["desc"]}
                </div>
            </div>
            """, unsafe_allow_html=True)