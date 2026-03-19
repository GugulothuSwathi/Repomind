 # utils/github_helper.py
# ============================================
# RepoMind - GitHub Repository Helper (FIXED)
#
# Fix: README files were being filtered out
# because _is_code_file() didn't include them.
# Now README is ALWAYS fetched regardless.
# ============================================

import os
from github import Github
from utils.config import GITHUB_TOKEN


def _to_content_list(content_obj):
    """Normalize PyGithub get_contents return value to a list."""
    return content_obj if isinstance(content_obj, list) else [content_obj]


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL."""
    url   = url.rstrip("/")
    parts = url.split("/")
    owner = parts[-2]
    repo  = parts[-1].replace(".git", "")
    return owner, repo


def get_repo_files(
    github_url: str,
    max_files: int = 50,
    max_dirs: int = 120,
    progress_callback=None,
) -> dict[str, str]:
    """
    Download all code files from a GitHub repository.
    README files are ALWAYS included regardless of other filters.
    """
    files = {}

    try:
        owner, repo_name = parse_github_url(github_url)
        g    = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{owner}/{repo_name}")

        contents      = _to_content_list(repo.get_contents(""))
        file_count    = 0
        dirs_scanned  = 0
        api_calls     = 1

        if callable(progress_callback):
            progress_callback(file_count=file_count, dirs_scanned=dirs_scanned, api_calls=api_calls)

        while contents and file_count < max_files and dirs_scanned < max_dirs:
            item = contents.pop(0)

            if item.type == "dir":
                # Add folder contents to queue
                dirs_scanned += 1
                try:
                    if dirs_scanned <= max_dirs:
                        contents.extend(_to_content_list(repo.get_contents(item.path)))
                        api_calls += 1
                except Exception:
                    pass

                if callable(progress_callback) and (dirs_scanned % 5 == 0):
                    progress_callback(file_count=file_count, dirs_scanned=dirs_scanned, api_calls=api_calls)

            elif item.type == "file":
                # ALWAYS include README files — never skip them
                is_readme = item.name.lower().startswith("readme")

                # Include code files under 100KB
                is_code = _is_code_file(item.name) and item.size < 100_000

                if (is_readme or is_code):
                    try:
                        content = item.decoded_content.decode("utf-8", errors="ignore")
                        files[item.path] = content
                        file_count += 1

                        if is_readme:
                            print(f"   ✅ README captured: {item.path}")

                        if callable(progress_callback) and (file_count % 5 == 0):
                            progress_callback(file_count=file_count, dirs_scanned=dirs_scanned, api_calls=api_calls)

                    except Exception:
                        pass

        if callable(progress_callback):
            progress_callback(file_count=file_count, dirs_scanned=dirs_scanned, api_calls=api_calls)

        print(f"   Total files fetched: {len(files)}")
        readme_files = [f for f in files.keys() if f.lower().split("/")[-1].startswith("readme")]
        print(f"   README files in fetched set: {readme_files}")

        return files

    except Exception as e:
        return {"ERROR": f"Could not fetch repository: {str(e)}"}


def get_repo_info(github_url: str) -> dict:
    """Get basic information about a repository."""
    try:
        owner, repo_name = parse_github_url(github_url)
        g    = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{owner}/{repo_name}")

        return {
            "name":           repo.name,
            "full_name":      repo.full_name,
            "description":    repo.description or "No description",
            "language":       repo.language or "Unknown",
            "stars":          repo.stargazers_count,
            "forks":          repo.forks_count,
            "open_issues":    repo.open_issues_count,
            "default_branch": repo.default_branch,
            "url":            repo.html_url,
        }

    except Exception as e:
        return {"error": str(e)}


def get_requirements_txt(github_url: str) -> str:
    """Fetch requirements.txt or similar dependency files."""
    try:
        owner, repo_name = parse_github_url(github_url)
        g    = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{owner}/{repo_name}")

        for filename in [
            "requirements.txt",
            "requirements/base.txt",
            "requirements/prod.txt",
            "Pipfile",
        ]:
            try:
                file = repo.get_contents(filename)
                if isinstance(file, list):
                    continue
                return file.decoded_content.decode("utf-8")
            except Exception:
                continue

        return ""

    except Exception:
        return ""


def _is_code_file(filename: str) -> bool:
    """Check if a file is a source code file worth analyzing."""
    CODE_EXTENSIONS = {
        # Python, JS, TS
        ".py", ".js", ".ts", ".jsx", ".tsx",
        # JVM
        ".java", ".kt", ".scala",
        # Systems
        ".go", ".rs", ".cpp", ".c", ".h",
        # Other languages
        ".rb", ".php", ".swift", ".cs",
        # Web
        ".html", ".css", ".scss",
        # Config
        ".yaml", ".yml", ".toml", ".json",
        # Docs — IMPORTANT: .md is here so README.md is included
        ".md", ".txt", ".rst",
        # Shell
        ".sh", ".bash",
        # Database
        ".sql",
        # Docker
        ".dockerfile",
    }

    # Special filenames without extensions
    SPECIAL_FILES = {
        "dockerfile", "makefile", "jenkinsfile",
        "readme", "license", "changelog",
    }

    _, ext = os.path.splitext(filename.lower())
    name_lower = filename.lower()

    return ext in CODE_EXTENSIONS or name_lower in SPECIAL_FILES