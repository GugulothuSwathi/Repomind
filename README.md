# RepoMind

RepoMind is a Streamlit app that analyzes GitHub repositories using multiple AI-powered agents.

It provides:
- Code quality review
- Security checks
- Documentation quality insights
- Dependency risk checks
- Bug-fix recommendations
- Risk heatmap and architecture analysis
- Repository time-machine timeline
- PDF report export

## Tech Stack

- Python
- Streamlit
- Google Gemini API
- GitHub API (PyGithub)
- Plotly + Pandas
- ReportLab

## Prerequisites

- Python 3.10+
- Git installed and available in PATH (required for Time Machine agent)
- A GitHub personal access token
- A Gemini API key

## Setup

1. Clone the repository and open it in VS Code.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Create your env file from the example.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Configure environment variables

Copy `.env.example` to `.env` and fill in real values.

```powershell
Copy-Item .env.example .env
```

## Run the app

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL shown by Streamlit in your browser.

## Environment Variables

- `GEMINI_API_KEY`: Google Gemini API key used by AI agents.
- `GITHUB_TOKEN`: GitHub token used to read repositories and post PR comments.

## Screenshots

### Splash Screen
![RepoMind Splash Screen](screenshots/splash-screen.png)

### Configuration & Agent Selection
![Configuration Dashboard](screenshots/configuration.png)

### Analysis Results - RepoScore & Agent Scores
![Results Dashboard](screenshots/results-dashboard.png)


