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
  --ue-plugin-host "localhost" \
  --ue-plugin-port 8080

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
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│              UnrealProjectAnalyzer Plugin (Editor)               │
│  ┌─────────────────────────┐  ┌────────────────────────────────┐ │
│  │   HTTP Server (:8080)   │  │   MCP Launcher (uv process)    │ │
│  │   Blueprint/Asset API   │  │   Auto-start from Editor       │ │
│  └─────────────────────────┘  └────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Available Tools

### Blueprint Tools
| Tool | Description |
|------|-------------|
| `search_blueprints` | Search blueprints by name pattern and class filter |
| `get_blueprint_hierarchy` | Get class inheritance chain |
| `get_blueprint_dependencies` | Get all dependencies |
| `get_blueprint_referencers` | Get all referencers |
| `get_blueprint_graph` | Get node graph (EventGraph, functions) |
| `get_blueprint_details` | Get variables, functions, components |

### Asset Tools
| Tool | Description |
|------|-------------|
| `search_assets` | Search assets by name/type |
| `get_asset_references` | Get referenced assets |
| `get_asset_referencers` | Get referencing assets |
| `get_asset_metadata` | Get asset metadata |

### C++ Analysis Tools
| Tool | Description |
|------|-------------|
| `analyze_cpp_class` | Analyze class structure (methods, properties) |
| `get_cpp_class_hierarchy` | Get inheritance hierarchy |
| `search_cpp_code` | Search source code with regex |
| `find_cpp_references` | Find identifier references |
| `detect_ue_patterns` | Detect UPROPERTY/UFUNCTION patterns |
| `get_cpp_blueprint_exposure` | Get Blueprint-exposed API |

### Cross-Domain Tools
| Tool | Description |
|------|-------------|
| `trace_reference_chain` | Trace complete reference chain across domains |
| `find_cpp_class_usage` | Find C++ class usage in Blueprints |

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

### Trace a GAS Ability

```
User: 帮我追踪 GA_Hero_Dash 这个能力是怎么触发和执行的

Agent:
[Uses search_blueprints, get_blueprint_details, get_blueprint_graph...]

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

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint
uv run ruff check .
```

## Acknowledgements

This project was inspired by and references implementations from:

- **[unreal-analyzer-mcp](https://github.com/ayeletstudioindia/unreal-analyzer-mcp)** - C++ source code analysis approach using tree-sitter
- **[ue5-mcp](https://github.com/cutehusky/ue5-mcp)** - Unreal Editor HTTP API exposure pattern

## License

MIT
