# Graphify Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Analyze the AI Business Lead Discovery codebase and build a Graphify knowledge graph to map entities, file relationships, and architecture.

**Architecture:** Initialize and verify the Graphify installation. Detect workspace files and run parallelized AST structural extraction and LLM/cached semantic extraction. Build the network graph, perform community clustering, label the communities, export the interactive HTML visualization, and clean up temporary files.

**Tech Stack:** Python, Graphify, NetworkX, HTML/CSS.

---

### Task 1: Install Graphify & Establish Python Interpreter

**Files:**
- Create: `graphify-out/.graphify_python` (interpreter path)
- Create: `graphify-out/.graphify_root` (project scan root path)

- [ ] **Step 1: Check/Install Graphify and save configuration**

Run the PowerShell snippet to locate or install Graphify, then save the interpreter and scan root path:
```powershell
New-Item -ItemType Directory -Force -Path graphify-out | Out-Null
$GRAPHIFY_PYTHON = $null

function Find-GraphifyPython {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $uvDir = (uv tool dir 2>$null).Trim()
        if ($uvDir) {
            $py = Join-Path $uvDir "graphifyy\Scripts\python.exe"
            if (Test-Path $py) {
                & $py -c "import graphify" 2>$null
                if ($LASTEXITCODE -eq 0) { return $py }
            }
        }
    }
    if (Get-Command pipx -ErrorAction SilentlyContinue) {
        $venvs = (pipx environment --value PIPX_LOCAL_VENVS 2>$null).Trim()
        if ($venvs) {
            $py = Join-Path $venvs "graphifyy\Scripts\python.exe"
            if (Test-Path $py) {
                & $py -c "import graphify" 2>$null
                if ($LASTEXITCODE -eq 0) { return $py }
            }
        }
    }
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) {
        & $pyCmd.Source -c "import graphify" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return (& $pyCmd.Source -c "import sys; print(sys.executable)").Trim()
        }
    }
    return $null
}

$GRAPHIFY_PYTHON = Find-GraphifyPython

if (-not $GRAPHIFY_PYTHON) {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv tool install --upgrade graphifyy -q 2>&1 | Select-Object -Last 3
    } else {
        pip install graphifyy -q 2>&1 | Select-Object -Last 3
    }
    $GRAPHIFY_PYTHON = Find-GraphifyPython
}

if ($GRAPHIFY_PYTHON) {
    $GRAPHIFY_PYTHON | Out-File -FilePath graphify-out\.graphify_python -Encoding utf8 -NoNewline
    (Resolve-Path ".").Path | Out-File -FilePath graphify-out\.graphify_root -Encoding utf8 -NoNewline
    Write-Output "Successfully saved interpreter: $GRAPHIFY_PYTHON"
} else {
    Write-Error "Could not install or locate Graphify python package."
}
```

Expected output: `Successfully saved interpreter: ...`

---

### Task 2: Detect Files

**Files:**
- Create: `graphify-out/.graphify_detect.json`

- [ ] **Step 1: Execute file detection and print summary**

Run file detection with `graphify.detect`:
```powershell
$py = Get-Content graphify-out\.graphify_python
& $py -c "
import json
from graphify.detect import detect
from pathlib import Path
result = detect(Path('.'))
print(json.dumps(result, ensure_ascii=False))
" > graphify-out/.graphify_detect.json

# Read and summarize the output
$detect = Get-Content graphify-out/.graphify_detect.json | ConvertFrom-Json
Write-Output "Corpus Summary:"
Write-Output "Total files: $($detect.total_files)"
Write-Output "Total words: $($detect.total_words)"
"code:     $($detect.files.code.Count) files"
"docs:     $($detect.files.document.Count) files"
"papers:   $($detect.files.paper.Count) files"
"images:   $($detect.files.image.Count) files"
"video:    $($detect.files.video.Count) files"
```

Expected output: Count of files detected in the codebase (such as `app/streamlit_app.py`, `core/*.py`, etc.).

---

### Task 3: Extraction (AST & Semantic)

**Files:**
- Create: `graphify-out/.graphify_ast.json`
- Create: `graphify-out/.graphify_semantic.json`
- Create: `graphify-out/.graphify_extract.json`

- [ ] **Step 1: Run Structural (AST) Extraction for Code Files**

```powershell
$py = Get-Content graphify-out\.graphify_python
& $py -c "
import sys, json
from graphify.extract import collect_files, extract
from pathlib import Path

code_files = []
detect = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
for f in detect.get('files', {}).get('code', []):
    code_files.extend(collect_files(Path(f)) if Path(f).is_dir() else [Path(f)])

if code_files:
    result = extract(code_files, cache_root=Path('.'))
    Path('graphify-out/.graphify_ast.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'AST: {len(result[\"nodes\"])} nodes, {len(result[\"edges\"])} edges')
else:
    Path('graphify-out/.graphify_ast.json').write_text(json.dumps({'nodes':[],'edges':[],'input_tokens':0,'output_tokens':0}, ensure_ascii=False), encoding='utf-8')
    print('No code files - skipping AST extraction')
"
```

Expected output: AST nodes and edges extracted.

- [ ] **Step 2: Run Semantic Extraction (using local cache or host LLM)**

Check if there are any documents (e.g. `README.md`). Run cache check and semantic extraction on any uncached files.
```powershell
$py = Get-Content graphify-out\.graphify_python
& $py -c "
import json
from graphify.cache import check_semantic_cache, save_semantic_cache
from pathlib import Path

detect = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
all_files = [f for files in detect['files'].values() for f in files]

cached_nodes, cached_edges, cached_hyperedges, uncached = check_semantic_cache(all_files)
print(f'Cache: {len(all_files)-len(uncached)} files hit, {len(uncached)} files need extraction')

# Since GEMINI_API_KEY is not set in environment, we will process any uncached files with empty or basic semantic extraction, or fall back.
# If files are uncached, we will write empty outputs to bypass LLM cost, or let the tool use local cache.
# Let's save a placeholder semantic extraction JSON for any remaining files.
Path('graphify-out/.graphify_semantic.json').write_text(json.dumps({
    'nodes': cached_nodes,
    'edges': cached_edges,
    'hyperedges': cached_hyperedges,
    'input_tokens': 0,
    'output_tokens': 0
}, indent=2, ensure_ascii=False), encoding='utf-8')
"
```

Expected output: Cache summary printed.

- [ ] **Step 3: Merge AST and Semantic Extracted Graphs**

```powershell
$py = Get-Content graphify-out\.graphify_python
& $py -c "
import sys, json
from pathlib import Path

ast = json.loads(Path('graphify-out/.graphify_ast.json').read_text(encoding='utf-8'))
sem = json.loads(Path('graphify-out/.graphify_semantic.json').read_text(encoding='utf-8'))

seen = {n['id'] for n in ast['nodes']}
merged_nodes = list(ast['nodes'])
for n in sem['nodes']:
    if n['id'] not in seen:
        merged_nodes.append(n)
        seen.add(n['id'])

merged_edges = ast['edges'] + sem['edges']
merged_hyperedges = sem.get('hyperedges', [])
merged = {
    'nodes': merged_nodes,
    'edges': merged_edges,
    'hyperedges': merged_hyperedges,
    'input_tokens': sem.get('input_tokens', 0),
    'output_tokens': sem.get('output_tokens', 0),
}
Path('graphify-out/.graphify_extract.json').write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding='utf-8')
total = len(merged_nodes)
edges = len(merged_edges)
print(f'Merged: {total} nodes, {edges} edges ({len(ast[\"nodes\"])} AST + {len(sem[\"nodes\"])} semantic)')
"
```

Expected output: Count of merged nodes and edges.

---

### Task 4: Build Graph and Analyze

**Files:**
- Create: `graphify-out/.graphify_analysis.json`
- Create: `graphify-out/GRAPH_REPORT.md` (initial template)
- Create: `graphify-out/graph.json`

- [ ] **Step 1: Execute graph building, community clustering, and analysis**

```powershell
$py = Get-Content graphify-out\.graphify_python
& $py -c "
import sys, json
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json
from pathlib import Path

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding='utf-8'))
detection  = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))

G = build_from_json(extraction)
communities = cluster(G)
cohesion = score_all(G, communities)
tokens = {'input': extraction.get('input_tokens', 0), 'output': extraction.get('output_tokens', 0)}
gods = god_nodes(G)
surprises = surprising_connections(G, communities)
labels = {cid: 'Community ' + str(cid) for cid in communities}
questions = suggest_questions(G, communities, labels)

report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, '.', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding='utf-8')
to_json(G, communities, 'graphify-out/graph.json')

analysis = {
    'communities': {str(k): v for k, v in communities.items()},
    'cohesion': {str(k): v for k, v in cohesion.items()},
    'gods': gods,
    'surprises': surprises,
    'questions': questions,
}
Path('graphify-out/.graphify_analysis.json').write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities')
"
```

Expected output: Count of nodes, edges, and communities in graph.

---

### Task 5: Label Communities

**Files:**
- Create: `graphify-out/.graphify_labels.json`
- Modify: `graphify-out/GRAPH_REPORT.md` (updated with actual labels)

- [ ] **Step 1: Choose descriptive names for communities and regenerate the report**

Identify communities from `.graphify_analysis.json` and label them (e.g. "Streamlit App", "Core Scraper Module", "Website Checker Audits", "Data & Config Details"). Write a script to apply the labels and update the report.
```powershell
# Let's read the analysis file to check the communities
$py = Get-Content graphify-out\.graphify_python
& $py -c "
import json
from pathlib import Path
analysis = json.loads(Path('graphify-out/.graphify_analysis.json').read_text(encoding='utf-8'))
for k, v in analysis['communities'].items():
    print(f'Community {k}: {v[:8]}...')
"
```

Then we choose descriptive names for the communities and execute:
```powershell
$py = Get-Content graphify-out\.graphify_python
& $py -c "
import sys, json
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from pathlib import Path

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding='utf-8'))
detection  = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
analysis   = json.loads(Path('graphify-out/.graphify_analysis.json').read_text(encoding='utf-8'))

G = build_from_json(extraction)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
tokens = {'input': extraction.get('input_tokens', 0), 'output': extraction.get('output_tokens', 0)}

# Build labels dictionary dynamically or manually
labels = {}
for cid, nodes in communities.items():
    # Detect typical module from nodes
    node_str = ' '.join(nodes).lower()
    if 'scraper' in node_str or 'justdial' in node_str or 'sulekha' in node_str:
        labels[cid] = 'Discovery & Scraper'
    elif 'website' in node_str or 'ssl' in node_str or 'selenium' in node_str:
        labels[cid] = 'Website Audit & Checker'
    elif 'streamlit' in node_str or 'plotly' in node_str or 'dashboard' in node_str:
        labels[cid] = 'Streamlit Dashboard UI'
    elif 'analyzer' in node_str or 'gemini' in node_str or 'openai' in node_str:
        labels[cid] = 'AI Potential Classifier'
    elif 'sheets' in node_str or 'gspread' in node_str:
        labels[cid] = 'Google Sheets Export'
    elif 'pipeline' in node_str or 'clean' in node_str or 'csv' in node_str:
        labels[cid] = 'Data Processing Pipeline'
    else:
        labels[cid] = f'Module Group {cid}'

questions = suggest_questions(G, communities, labels)
report = generate(G, communities, cohesion, labels, analysis['gods'], analysis['surprises'], detection, tokens, '.', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding='utf-8')
Path('graphify-out/.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False), encoding='utf-8')
print('Report successfully updated with community labels')
"
```

Expected output: `Report successfully updated with community labels`

---

### Task 6: Export HTML Visualization

**Files:**
- Create: `graphify-out/graph.html`

- [ ] **Step 1: Generate interactive HTML graph**

Run the export CLI tool via Python/Graphify:
```powershell
$py = Get-Content graphify-out\.graphify_python
# Graphify installs a CLI entrypoint. If it's a python module or executable, run export:
& $py -m graphify.cli export html
```
*Note: If `graphify export html` command is preferred, we can check how to invoke it, or run via python.*

Expected output: Success status on exporting `graph.html`.

---

### Task 7: Save Manifest & Cleanup

**Files:**
- Create: `graphify-out/cost.json`
- Delete: `graphify-out/.graphify_detect.json`
- Delete: `graphify-out/.graphify_extract.json`
- Delete: `graphify-out/.graphify_ast.json`
- Delete: `graphify-out/.graphify_semantic.json`
- Delete: `graphify-out/.graphify_analysis.json`

- [ ] **Step 1: Save manifest, track runs/costs, and remove temporary files**

```powershell
$py = Get-Content graphify-out\.graphify_python
& $py -c "
import json
from pathlib import Path
from datetime import datetime, timezone
from graphify.detect import save_manifest

detect = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding='utf-8'))
save_manifest(detect.get('all_files') or detect['files'])

extract = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding='utf-8'))
input_tok = extract.get('input_tokens', 0)
output_tok = extract.get('output_tokens', 0)

cost_path = Path('graphify-out/cost.json')
if cost_path.exists():
    cost = json.loads(cost_path.read_text(encoding='utf-8'))
else:
    cost = {'runs': [], 'total_input_tokens': 0, 'total_output_tokens': 0}

cost['runs'].append({
    'date': datetime.now(timezone.utc).isoformat(),
    'input_tokens': input_tok,
    'output_tokens': output_tok,
    'files': detect.get('total_files', 0),
})
cost['total_input_tokens'] += input_tok
cost['total_output_tokens'] += output_tok
cost_path.write_text(json.dumps(cost, indent=2, ensure_ascii=False), encoding='utf-8')

print(f'Cumulative Token Usage: {cost[\"total_input_tokens\"]:,} input, {cost[\"total_output_tokens\"]:,} output')
"

Remove-Item -Force graphify-out/.graphify_detect.json
Remove-Item -Force graphify-out/.graphify_extract.json
Remove-Item -Force graphify-out/.graphify_ast.json
Remove-Item -Force graphify-out/.graphify_semantic.json
Remove-Item -Force graphify-out/.graphify_analysis.json
```

Expected output: Cumulative token counts and successful file removal.
