# UE5 Project Analyzer

MCP Server for analyzing Unreal Engine 5 projects - Blueprint, Asset, and C++ source code.

> **Goal**: Let AI understand the complete picture of a UE5 project by tracing reference chains across Blueprint ↔ C++ ↔ Asset boundaries.

## Features

- **Blueprint Analysis**: Hierarchy, dependencies, graph inspection
- **Asset Reference Tracking**: Find what uses what, and what is used by what
- **C++ Source Analysis**: Class structure, UPROPERTY/UFUNCTION detection (tree-sitter based)
- **Cross-Domain Queries**: Trace complete reference chains across all domains

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         AI Agent (Cursor)                         │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ MCP Protocol
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MCP Server (Python/FastMCP)                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              C++ Source Analyzer (tree-sitter)              │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                  UE5ProjectAnalyzer Plugin                        │
│  ┌─────────────────────────┐  ┌────────────────────────────────┐ │
│  │   C++ HTTP Server       │  │   Python Bridge (auto-start)   │ │
│  │   :8080                 │  │   (Unreal Python API)          │ │
│  └─────────────────────────┘  └────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Unreal Engine 5.3+

### MCP Server Setup

```bash
cd ue5-project-analyzer

# Install dependencies
uv sync

# Run the MCP server
uv run ue5-analyzer
```

### UE5 Plugin Setup

1. Copy `unreal-plugin/` folder to your UE5 project's `Plugins/` directory
2. Rename to `UE5ProjectAnalyzer/`
3. Enable the plugin in UE5 Editor (Edit → Plugins → UE5 Project Analyzer)
4. Restart the Editor

## Configuration

### Environment Variables

```bash
# UE5 Plugin API location
UE_PLUGIN_HOST=localhost
UE_PLUGIN_PORT=8080
```

### MCP Client Configuration (Cursor)

Add to your MCP settings:

```json
{
  "mcpServers": {
    "ue5-project-analyzer": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/ue5-project-analyzer", "ue5-analyzer"]
    }
  }
}
```

## Usage

### Example: Trace a GAS Ability

```
User: 帮我追踪 GA_Hero_Dash 这个能力是怎么触发和执行的

Agent:
[Uses search_blueprints, get_blueprint_details, get_blueprint_dependencies...]

GA_Hero_Dash 的完整流程：

触发路径：
玩家按下 Shift → IA_Dash → IC_Default_KBM 
  → ULyraHeroComponent::Input_AbilityInputTagPressed()
  → ULyraAbilitySystemComponent::TryActivateAbility(Ability.Dash)

执行逻辑 (EventGraph):
1. ActivateAbility
2. Apply Root Motion
3. Play Montage
4. EndAbility

关联资产：
- GE_Dash_Cost, GE_Dash_Cooldown
- AM_Hero_Dash, S_Dash_Whoosh
```

### Example: Find Asset References

```
User: SK_Mannequin 被哪些地方用到了？

Agent:
[Uses get_asset_referencers, trace_reference_chain...]

SK_Mannequin 引用情况：

直接引用:
├─ SKM_Mannequin (SkeletalMesh)
├─ ABP_Mannequin (AnimBlueprint)
└─ Phys_Mannequin (PhysicsAsset)

间接引用 (通过 SKM_Mannequin):
├─ B_Hero_ShooterMannequin
├─ B_Hero_Default
└─ ... (共 12 个蓝图)
```

## Available Tools

### Blueprint Tools
- `search_blueprints` - Search blueprints by name/class
- `get_blueprint_hierarchy` - Get class inheritance chain
- `get_blueprint_dependencies` - Get all dependencies
- `get_blueprint_referencers` - Get all referencers
- `get_blueprint_graph` - Get node graph
- `get_blueprint_details` - Get comprehensive details

### Asset Tools
- `search_assets` - Search assets by name/type
- `get_asset_references` - Get referenced assets
- `get_asset_referencers` - Get referencing assets
- `get_asset_metadata` - Get asset metadata

### C++ Analysis Tools
- `analyze_cpp_class` - Analyze class structure
- `get_cpp_class_hierarchy` - Get inheritance hierarchy
- `search_cpp_code` - Search source code
- `find_cpp_references` - Find code references
- `detect_ue_patterns` - Detect UPROPERTY/UFUNCTION
- `get_cpp_blueprint_exposure` - Get Blueprint-exposed API

### Cross-Domain Tools
- `trace_reference_chain` - Trace complete reference chain
- `find_cpp_class_usage` - Find C++ class usage in Blueprints

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint
uv run ruff check .
```

## License

MIT
