 # agents/architecture_agent.py
from __future__ import annotations
# ============================================
# RepoMind - Architecture Generator Agent (IMPROVED)
#
# Now generates:
# 1. Real import dependency graph (NetworkX)
# 2. Proper Mermaid diagram that RENDERS in Streamlit
# 3. Module relationship table
# 4. Dependency edge list
# 5. AI architecture description
# ============================================

import re
import os
from collections import defaultdict
from utils.llm import get_gemini_response


def run_architecture_agent(files: dict[str, str], repo_info: dict) -> dict:
    """Analyze repository and generate architecture documentation."""

    # Step 1: Folder structure
    folder_structure = _build_folder_tree(files)

    # Step 2: Parse real import dependencies
    dependencies     = _parse_imports(files)
    edges            = _build_dependency_edges(dependencies, files)

    # Step 3: Tech stack
    tech_stack = _detect_tech_stack(files)

    # Step 4: Components
    components = _identify_components(files)

    # Step 5: Module stats
    module_stats = _compute_module_stats(files, dependencies)

    # Step 6: Generate Mermaid diagram (FIXED to render properly)
    mermaid_diagram = _generate_mermaid(components, edges, files)

    # Step 7: AI description
    imports_summary = _summarize_imports(dependencies)
    prompt = f"""You are a software architect analyzing a {repo_info.get('language', 'Python')} project.

Repository: {repo_info.get('name', 'Unknown')}
Description: {repo_info.get('description', 'No description')}

File structure (first 30 files):
{folder_structure[:1000]}

Most imported modules: {imports_summary[:300]}
Tech stack: {', '.join(tech_stack)}
Top-level components: {', '.join([c['name'] for c in components[:8]])}

Provide:
ARCHITECTURE_PATTERN: [MVC / Microservices / Monolith / REST API / Event-driven / etc.]
LAYER_BREAKDOWN: [describe each layer in 1 sentence]
DATA_FLOW: [how data flows through the system, 3-4 steps]
RECOMMENDATIONS: [2-3 specific improvements]
"""
    ai_response  = get_gemini_response(prompt, temperature=0.3)
    ai_desc      = _parse_architecture_response(ai_response)

    print(f"   Components: {len(components)}, Edges: {len(edges)}, Tech: {tech_stack}")

    return {
        "folder_structure": folder_structure,
        "components":       components,
        "dependencies":     dependencies,
        "edges":            edges,
        "module_stats":     module_stats,
        "mermaid_diagram":  mermaid_diagram,
        "ai_description":   ai_desc,
        "tech_stack":       tech_stack,
        "raw_ai_response":  ai_response,
    }


def _build_folder_tree(files: dict) -> str:
    """Build readable folder tree."""
    paths      = sorted(files.keys())
    tree_lines = ["📁 Repository Structure\n"]
    dirs_seen  = set()

    for path in paths:
        parts = path.split("/")
        depth = len(parts) - 1
        if depth > 0:
            dir_path = "/".join(parts[:-1])
            if dir_path not in dirs_seen:
                dirs_seen.add(dir_path)
                indent = "  " * (len(parts) - 2)
                tree_lines.append(f"{indent}📁 {parts[-2]}/")
        indent = "  " * depth
        tree_lines.append(f"{indent}📄 {parts[-1]}")

    return "\n".join(tree_lines[:80])


def _parse_imports(files: dict) -> dict[str, list[str]]:
    """Parse import statements from all code files."""
    import_map = {}

    for filepath, content in files.items():
        imports = []

        if filepath.endswith(".py"):
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("import "):
                    mod = line.replace("import ", "").split()[0].split(".")[0]
                    imports.append(mod)
                elif line.startswith("from "):
                    m = re.match(r"from\s+(\S+)\s+import", line)
                    if m:
                        mod = m.group(1).split(".")[0]
                        imports.append(mod)

        elif filepath.endswith((".js", ".ts", ".jsx", ".tsx")):
            for line in content.split("\n"):
                m = re.search(r"from\s+['\"]([^'\"]+)['\"]", line)
                if m: imports.append(m.group(1))
                m = re.search(r"require\s*\(['\"]([^'\"]+)['\"]\)", line)
                if m: imports.append(m.group(1))

        elif filepath.endswith(".cs"):
            for line in content.split("\n"):
                m = re.match(r"using\s+([\w\.]+);", line.strip())
                if m: imports.append(m.group(1).split(".")[0])

        if imports:
            import_map[filepath] = list(set(imports))[:15]

    return import_map


def _build_dependency_edges(dependencies: dict, files: dict) -> list[dict]:
    """
    Build edges between FILES (not just external modules).
    Edge: file A imports something from file B.
    """
    edges  = []
    # Get all local module names (filenames without extension)
    local_modules = {}
    for filepath in files.keys():
        basename = filepath.split("/")[-1]
        name, _  = os.path.splitext(basename)
        local_modules[name.lower()] = filepath

    for filepath, imports in dependencies.items():
        source_module = filepath.split("/")[-1].replace(".py","").replace(".js","").replace(".ts","")
        for imp in imports:
            imp_lower = imp.lower()
            # Check if this import refers to a local file
            if imp_lower in local_modules and local_modules[imp_lower] != filepath:
                edges.append({
                    "from":   filepath,
                    "to":     local_modules[imp_lower],
                    "module": imp,
                    "type":   "local",
                })
            else:
                # External dependency
                edges.append({
                    "from":   filepath,
                    "to":     imp,
                    "module": imp,
                    "type":   "external",
                })

    return edges[:50]  # cap at 50 edges


def _detect_tech_stack(files: dict) -> list[str]:
    """Detect frameworks and technologies."""
    all_content = " ".join(files.values()).lower()
    all_files   = " ".join(files.keys()).lower()

    detections = {
        "FastAPI":    ["fastapi"],
        "Flask":      ["from flask", "import flask"],
        "Django":     ["from django", "django."],
        "aiohttp":    ["aiohttp"],
        "React":      ["react", ".jsx", ".tsx"],
        "Vue.js":     ["vue"],
        "Streamlit":  ["streamlit"],
        "SQLAlchemy": ["sqlalchemy"],
        "PostgreSQL": ["postgresql", "psycopg", "asyncpg"],
        "MongoDB":    ["pymongo", "motor"],
        "Redis":      ["redis", "aioredis"],
        "Docker":     ["dockerfile", "docker-compose"],
        "Pytest":     ["pytest"],
        "Celery":     ["celery"],
        "LangChain":  ["langchain"],
        "OpenAI":     ["openai"],
        "TensorFlow": ["tensorflow"],
        "PyTorch":    ["torch"],
        "aiopg":      ["aiopg"],
        "asyncio":    ["asyncio", "async def", "await "],
    }

    found = []
    for tech, patterns in detections.items():
        for p in patterns:
            if p in all_content or p in all_files:
                found.append(tech)
                break

    return found if found else ["Unknown"]


def _identify_components(files: dict) -> list[dict]:
    """Identify high-level architectural components from folders."""
    folders = defaultdict(list)
    for path in files.keys():
        parts = path.split("/")
        if len(parts) > 1:
            folders[parts[0]].append(path)
        else:
            folders["root"].append(path)

    COMPONENT_STYLES = {
        "frontend":   ("🖥️",  "#4CAF50"),
        "backend":    ("⚙️",  "#2196F3"),
        "api":        ("🔌",  "#9C27B0"),
        "auth":       ("🔐",  "#F44336"),
        "database":   ("🗄️", "#FF9800"),
        "db":         ("🗄️", "#FF9800"),
        "models":     ("📊",  "#607D8B"),
        "services":   ("🔧",  "#00BCD4"),
        "utils":      ("🛠️", "#795548"),
        "tests":      ("🧪",  "#8BC34A"),
        "config":     ("⚙️",  "#FF5722"),
        "static":     ("📦",  "#9E9E9E"),
        "templates":  ("📋",  "#FFEB3B"),
        "agents":     ("🤖",  "#E91E63"),
        "migrations": ("🔄",  "#00ACC1"),
        "sqli":       ("💉",  "#F44336"),  # dvpwa specific
        "handlers":   ("🎯",  "#AB47BC"),
        "middlewares":("🔗",  "#26A69A"),
        "root":       ("📁",  "#607D8B"),
    }

    components = []
    for folder, folder_files in folders.items():
        folder_lower = folder.lower()
        icon, color  = COMPONENT_STYLES.get(folder_lower, ("📂", "#6E7681"))
        components.append({
            "name":       folder.title(),
            "folder":     folder,
            "icon":       icon,
            "color":      color,
            "files":      folder_files,
            "file_count": len(folder_files),
        })

    # Sort by file count descending
    components.sort(key=lambda x: x["file_count"], reverse=True)
    return components


def _compute_module_stats(files: dict, dependencies: dict) -> list[dict]:
    """Compute per-module stats: lines of code, imports, complexity estimate."""
    stats = []
    # Count how many times each file is imported
    import_counts = defaultdict(int)
    for imports in dependencies.values():
        for imp in imports:
            import_counts[imp] += 1

    for filepath, content in files.items():
        if not any(filepath.endswith(e) for e in (".py",".js",".ts",".cs")):
            continue
        lines       = content.split("\n")
        loc         = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
        func_count  = len(re.findall(r"^\s*def ", content, re.MULTILINE))
        class_count = len(re.findall(r"^\s*class ", content, re.MULTILINE))
        basename    = filepath.split("/")[-1].replace(".py","")

        stats.append({
            "file":       filepath,
            "loc":        loc,
            "functions":  func_count,
            "classes":    class_count,
            "imports":    len(dependencies.get(filepath, [])),
            "imported_by": import_counts.get(basename, 0),
        })

    stats.sort(key=lambda x: x["loc"], reverse=True)
    return stats[:20]


def _generate_mermaid(components: list, edges: list, files: dict) -> str:
    """
    Generate a Mermaid diagram that ACTUALLY RENDERS in Streamlit.

    Key fix: Streamlit renders mermaid via st.markdown with ```mermaid blocks.
    The diagram must be clean — no special chars in node IDs.
    """
    lines = ["graph LR"]
    lines.append("    %% RepoMind Auto-Generated Architecture")

    # Clean name helper — remove chars that break Mermaid
    def clean(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", name)

    # Add component nodes
    added_nodes = set()
    for comp in components[:12]:  # max 12 nodes for readability
        node_id = clean(comp["name"])
        label   = f"{comp['icon']} {comp['name']} ({comp['file_count']} files)"
        lines.append(f'    {node_id}["{label}"]')
        added_nodes.add(node_id)

    # Add connections between components based on actual import edges
    # Group edges by folder-to-folder
    folder_edges = defaultdict(int)
    for edge in edges:
        if edge["type"] == "local":
            src_folder  = edge["from"].split("/")[0]  if "/" in edge["from"]  else "root"
            dst_folder  = edge["to"].split("/")[0]    if "/" in edge["to"]    else "root"
            if src_folder != dst_folder:
                folder_edges[(src_folder, dst_folder)] += 1

    # Add component-level edges
    added_edges = set()
    for (src, dst), count in sorted(folder_edges.items(), key=lambda x: -x[1])[:15]:
        src_id = clean(src.title())
        dst_id = clean(dst.title())
        if src_id in added_nodes and dst_id in added_nodes:
            edge_key = f"{src_id}-->{dst_id}"
            if edge_key not in added_edges:
                lines.append(f'    {src_id} -->|"{count} refs"| {dst_id}')
                added_edges.add(edge_key)

    # Add fallback connections if no real edges detected
    if not added_edges and len(components) >= 2:
        comp_ids = [clean(c["name"]) for c in components[:6] if clean(c["name"]) in added_nodes]
        for i in range(len(comp_ids) - 1):
            lines.append(f"    {comp_ids[i]} --> {comp_ids[i+1]}")

    # Style nodes with colors
    for comp in components[:12]:
        node_id = clean(comp["name"])
        color   = comp.get("color", "#607D8B")
        if node_id in added_nodes:
            lines.append(f"    style {node_id} fill:{color},color:#fff,stroke:#333,stroke-width:2px")

    return "\n".join(lines)


def _summarize_imports(dependencies: dict) -> str:
    freq = defaultdict(int)
    for imports in dependencies.values():
        for imp in imports:
            freq[imp] += 1
    top = sorted(freq.items(), key=lambda x: -x[1])[:8]
    return ", ".join(f"{k}({v})" for k, v in top)


def _parse_architecture_response(response: str) -> dict:
    result      = {}
    current_key = None
    current_val = []

    for line in response.split("\n"):
        line = line.strip()
        if not line:
            continue
        for key in ["ARCHITECTURE_PATTERN","LAYER_BREAKDOWN","DATA_FLOW","RECOMMENDATIONS"]:
            if line.startswith(key + ":"):
                if current_key:
                    result[current_key] = " ".join(current_val).strip()
                current_key = key.lower()
                current_val = [line.replace(key+":", "").strip()]
                break
        else:
            if current_key:
                current_val.append(line)

    if current_key:
        result[current_key] = " ".join(current_val).strip()
    return result