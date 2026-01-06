# Unreal Project Analyzer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MCP Server for analyzing Unreal Engine 5 projects - Blueprint, Asset, and C++ source code.

> **Goal**: Let AI understand the complete picture of an Unreal project by tracing reference chains across Blueprint ↔ C++ ↔ Asset boundaries.

**[中文文档](README_CN.md)**

## Features

- **Blueprint Analysis**: Hierarchy, dependencies, graph inspection, variables, components
- **Asset Reference Tracking**: Find what uses what, and what is used by what
- **C++ Source Analysis**: Class structure, UPROPERTY/UFUNCTION detection (tree-sitter based)
- **Cross-Domain Queries**: Trace complete reference chains across all domains
- **Editor Integration**: Start/Stop MCP Server directly from Unreal Editor menu
- **Scope Control (v0.2.0)**: Search project-only, engine-only, or both
- **Unified Search (v0.2.0)**: grep-like interface across all domains

## What's New in v0.3.1

- **Further Simplified**: Reduced to **8 tools** (4 unified + 4 specialized)
- **Minimal Parameters**: Removed redundant parameters for lower cognitive load
- **Soft Reference Tracking**: Blueprint CDO variable defaults now included in reference chains
- **Mermaid Output**: `get_blueprint_graph` defaults to Mermaid format for easy visualization
- **C++ Reference Aggregation**: Groups results by file, distinguishes definition vs usage

### v0.3.0 Changes
- **Minimal Tool Set**: Reduced from 22 to 9 tools
- **Unified Interface**: `search`, `get_hierarchy`, `get_references`, `get_details`
- **Three-Layer Search**: `scope` parameter supports `project`/`engine`/`all`

## Quick Start (Recommended)

### Prerequisites

- **Unreal Engine 5.3+**
- **[uv](https://docs.astral.sh/uv/)** - Python package manager (required)

### 1. Install the Plugin

Copy the `UnrealProjectAnalyzer` folder to your Unreal project's `Plugins/` directory:

```
YourProject/
├── Plugins/
│   └── UnrealProjectAnalyzer/    ← this folder
│       ├── Source/
│       ├── Mcp/
│       └── UnrealProjectAnalyzer.uplugin
```

### 2. Configure uv Path

1. Open Unreal Editor
2. Go to **Edit → Project Settings → Plugins → Unreal Project Analyzer**
3. Set **Uv Executable** to your uv installation path, e.g.:
   - Windows: `C:\Users\YourName\.local\bin\uv.exe` or `C:\Users\YourName\anaconda3\Scripts\uv.exe`
   - macOS/Linux: `/usr/local/bin/uv` or `~/.local/bin/uv`

### 3. Start MCP Server

1. In Unreal Editor menu: **Tools → Unreal Project Analyzer → Start MCP Server**
2. Check Output Log for: `LogMcpServer: MCP Server process started`
3. Copy MCP URL via: **Tools → Unreal Project Analyzer → Copy MCP URL**

### 4. Connect from Cursor

Add to your Cursor MCP settings (use the copied URL):

```json
{
  "mcpServers": {
    "unreal-project-analyzer": {
      "url": "http://127.0.0.1:19840/mcp"
    }
  }
}
```

## Alternative: Run MCP Server Manually

If you prefer running the MCP Server outside of Unreal Editor:

```bash
cd /path/to/UnrealProjectAnalyzer

# Install dependencies
uv sync

# Run with stdio (for Cursor MCP integration)
uv run unreal-analyzer -- \
  --cpp-source-path "/path/to/YourProject/Source" \
  --unreal-engine-path "/path/to/UE_5.3/Engine/Source" \
  --ue-plugin-host "localhost" \
  --ue-plugin-port 8080 \
  --default-scope project

# Or run as HTTP server (for quick connect)
uv run unreal-analyzer -- \
  --transport http \
  --mcp-host 127.0.0.1 \
  --mcp-port 19840 \
  --cpp-source-path "/path/to/YourProject/Source"
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         AI Agent (Cursor)                        │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ MCP Protocol
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MCP Server (Python/FastMCP)                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              C++ Source Analyzer (tree-sitter)             │  │
│  │              Supports: project / engine / all              │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│              UnrealProjectAnalyzer Plugin (Editor)               │
│  ┌─────────────────────────┐  ┌────────────────────────────────┐ │
│  │   HTTP Server (:8080)   │  │   MCP Launcher (uv process)    │ │
│  │   Blueprint/Asset API   │  │   Auto-start from Editor       │ │
│  │   /health endpoint      │  │                                │ │
│  └─────────────────────────┘  └────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Search Scope (v0.2.0)

All C++ analysis tools support a `scope` parameter:

| Scope | Description | Use Case |
|-------|-------------|----------|
| `project` | Project source only (default) | Fast, focused searches |
| `engine` | Engine source only | Understanding UE internals |
| `all` | Both project and engine | Comprehensive analysis |

Example:
```python
# Only search project code (fast)
await search_cpp_code("Health", scope="project")

# Only search engine code  
await analyze_cpp_class("ACharacter", scope="engine")

# Search everywhere (slower but complete)
await find_cpp_references("UAbilitySystemComponent", scope="all")
```

## Available Tools (8 total)

### Core Tools (4)

| Tool | Parameters | Description |
|------|------------|-------------|
| `search` | `query`, `domain`, `scope`, `type_filter`, `max_results` | Unified search across C++/Blueprint/Asset |
| `get_hierarchy` | `name`, `domain`, `scope` | Get inheritance hierarchy (C++ or Blueprint) |
| `get_references` | `path`, `domain`, `scope`, `direction` | Get references (outgoing/incoming/both) |
| `get_details` | `path`, `domain`, `scope` | Get detailed information (C++/Blueprint/Asset) |

### Specialized Tools (4)

| Tool | Parameters | Description |
|------|------------|-------------|
| `get_blueprint_graph` | `bp_path`, `graph_name`, `format` | Blueprint node graph (Mermaid/summary/JSON) |
| `detect_ue_patterns` | `file_path`, `format` | UE macro detection (detailed/summary) |
| `trace_reference_chain` | `start_asset`, `max_depth`, `direction` | Cross-domain reference chain |
| `find_cpp_class_usage` | `cpp_class`, `scope`, `max_results` | C++ class usage in Blueprint + C++ |

## Plugin Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `Auto Start MCP Server` | Start MCP when Editor launches | `false` |
| `Uv Executable` | Path to uv binary | `uv` |
| `Capture Server Output` | Print MCP output to UE Log | `true` |
| `Transport` | MCP transport mode | `http` |
| `MCP Port` | HTTP/SSE listen port | `19840` |
| `Cpp Source Path` | Project C++ source root | Auto-detect |
| `Unreal Engine Source Path` | Engine source for analysis | Auto-detect |

## Example Usage

### Using Unified Search

```python
# Search for "Health" across all domains
result = await search(query="Health")  # domain="all", scope="project" by default

# Search only Blueprints with parent class filter
result = await search(query="GA_*", domain="blueprint", type_filter="GameplayAbility")

# Get hierarchy for a C++ class
hierarchy = await get_hierarchy(name="ACharacter", domain="cpp", scope="engine")

# Get Blueprint graph as Mermaid (default format)
graph = await get_blueprint_graph(bp_path="/Game/BP_Player")
# graph["mermaid"] can be pasted to https://mermaid.live
```

### Trace a GAS Ability

```
User: 帮我追踪 GA_Hero_Dash 这个能力是怎么触发和执行的

Agent:
[Uses search, get_hierarchy, get_blueprint_graph...]

GA_Hero_Dash 完整流程：

触发路径：
玩家按下 Shift → IA_Dash → IC_Default_KBM 
  → ULyraHeroComponent::Input_AbilityInputTagPressed()
  → ULyraAbilitySystemComponent::TryActivateAbility(Ability.Dash)

执行逻辑 (EventGraph):
1. ActivateAbility → IsLocallyControlled?
2. SelectDirectionalMontage → Set Direction
3. CommitAbility → PlayMontageAndWait
4. ApplyRootMotionConstantForce
5. Delay → EndAbility

关联资产：
- GE_HeroDash_Cooldown (GameplayEffect)
- Dash_Fwd/Bwd/Left/Right Montages
```

## Health Check

Verify UE plugin is running:

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "ok": true,
  "status": "running",
  "plugin": "UnrealProjectAnalyzer",
  "version": "0.3.1",
  "ue_version": "5.3.2-xxx",
  "project_name": "LyraStarterGame"
}
```

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Print config (debug)
uv run unreal-analyzer --print-config
```

## Acknowledgements

This project was inspired by and references implementations from:

- **[unreal-analyzer-mcp](https://github.com/ayeletstudioindia/unreal-analyzer-mcp)** - C++ source code analysis approach using tree-sitter
- **[ue5-mcp](https://github.com/cutehusky/ue5-mcp)** - Unreal Editor HTTP API exposure pattern

## License

MIT
