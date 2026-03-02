# Unreal Copilot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MCP Server for analyzing **and editing** Unreal Engine 5 projects - Blueprint, Asset, C++ source code, and executable Skills.

> **Goal**: Let AI understand the complete picture of an Unreal project by tracing reference chains across Blueprint ↔ C++ ↔ Asset boundaries, **and execute editor operations via Skills**.

**[中文文档](README_CN.md)**

## Features

- **Blueprint Analysis**: Hierarchy, dependencies, graph inspection, variables, components
- **Asset Reference Tracking**: Find what uses what, and what is used by what
- **C++ Source Analysis**: Class structure, UPROPERTY/UFUNCTION detection (tree-sitter based)
- **Cross-Domain Queries**: Trace complete reference chains across all domains
- **Editor Integration**: Start/Stop MCP Server directly from Unreal Editor menu
- **Scope Control**: Search project-only, engine-only, or both
- **Unified Search**: grep-like interface across all domains
- **🆕 Skill System (v0.4.0)**: Discoverable, readable, executable editor capabilities

## What's New in v0.4.0

- **Skill System**: 3 new MCP tools for discovering and executing editor capabilities
  - `list_unreal_skill` - Discover available skills
  - `read_unreal_skill` - Read skill documentation and scripts
  - `run_unreal_skill` - Execute skill scripts or inline Python
- **CppSkillApiSubsystem**: C++ editor primitives (Asset/Blueprint/World/Editor/Validation)
- **Event-Driven MCP Lifecycle**: Python→C++ notifications replace unreliable port probing
- **Renamed**: `UAnalyzerSubsystem` → `UMcpServerSubsystem` (reflects actual purpose)

## Blueprint Editing Plan

- [Blueprint Write Capability Plan](Docs/BLUEPRINT_EDITING_PLAN.md)

### Previous Changes

<details>
<summary>v0.3.x</summary>

- **Further Simplified**: Reduced to **8 tools** (4 unified + 4 specialized)
- **Minimal Parameters**: Removed redundant parameters for lower cognitive load
- **Soft Reference Tracking**: Blueprint CDO variable defaults now included in reference chains
- **Mermaid Output**: `get_blueprint_graph` defaults to Mermaid format for easy visualization
- **C++ Reference Aggregation**: Groups results by file, distinguishes definition vs usage

</details>

## Quick Start (Recommended)

### Prerequisites

- **Unreal Engine 5.3+**
- **[uv](https://docs.astral.sh/uv/)** - Python package manager (required)

### 0. One-time dependency sync (recommended)

Auto-install is supported, but for the **first run** we strongly recommend syncing the Python dependencies manually
before opening the editor (more reliable, easier to debug):

```powershell
cd <PluginRoot>\Content\Python
uv sync
```

Then open Unreal Editor and start the MCP server.

### 1. Install the Plugin

Copy the `UnrealCopilot` folder to your Unreal project's `Plugins/` directory:

```
YourProject/
├── Plugins/
│   └── UnrealCopilot/    ← this folder
│       ├── Source/
│       ├── Content/
│       ├── skills/       ← skill definitions
│       └── UnrealCopilot.uplugin
```

### 2. Configure uv Path

1. Open Unreal Editor
2. Go to **Edit → Project Settings → Plugins → Unreal Copilot**
3. Set **Uv Executable** to your uv installation path, e.g.:
   - Windows: `C:\Users\YourName\.local\bin\uv.exe` or `C:\Users\YourName\anaconda3\Scripts\uv.exe`
   - macOS/Linux: `/usr/local/bin/uv` or `~/.local/bin/uv`

### 3. Start MCP Server

1. In Unreal Editor menu: **Tools → Unreal Copilot → Start MCP Server**
2. Check Output Log / notifications for: `MCP Server is running`
3. Copy MCP URL via: **Tools → Unreal Copilot → Copy MCP URL**

### 4. Connect from Cursor

Add to your Cursor MCP settings (use the copied URL):

```json
{
  "mcpServers": {
    "unreal-copilot": {
      "url": "http://127.0.0.1:19840/mcp"
    }
  }
}
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
│  │  Analysis Tools     │  Skill Tools                         │  │
│  │  (search, refs...)  │  (list/read/run_unreal_skill)        │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  C++ Analyzer (tree-sitter)  │  SkillRunner (Python)       │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP / import unreal
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│              UnrealCopilot Plugin (Editor)                       │
│  ┌─────────────────────────┐  ┌────────────────────────────────┐ │
│  │   HTTP Server (:8080)   │  │   CppSkillApiSubsystem         │ │
│  │   Blueprint/Asset API   │  │   (Asset/BP/World/Editor ops)  │ │
│  └─────────────────────────┘  └────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │   MCP Server (UE Python) - Managed by McpServerSubsystem    │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Available Tools (11 total)

### Analysis Tools (8)

| Tool | Description |
|------|-------------|
| `search` | Unified search across C++/Blueprint/Asset |
| `get_hierarchy` | Get inheritance hierarchy (C++ or Blueprint) |
| `get_references` | Get references (outgoing/incoming/both) |
| `get_details` | Get detailed information (C++/Blueprint/Asset) |
| `get_blueprint_graph` | Blueprint node graph (Mermaid/summary/JSON) |
| `detect_ue_patterns` | UE macro detection (UPROPERTY/UFUNCTION/UCLASS) |
| `trace_reference_chain` | Cross-domain reference chain |
| `find_cpp_class_usage` | C++ class usage in Blueprint + C++ |

### Skill Tools (3)

| Tool | Parameters | Description |
|------|------------|-------------|
| `list_unreal_skill` | `query?` | List available skills (name, description, tags) |
| `read_unreal_skill` | `skill_name`, `path?` | Read skill files (default: SKILL.md + tree) |
| `run_unreal_skill` | `skill_name?`, `script?`, `args?`, `python?` | Execute skill script or inline Python |

## Skill System

Skills are discoverable, documented editor capabilities that AI agents can find, understand, and execute.

### Skill Directory Structure

```
UnrealCopilot/skills/
├── cpp_asset_api/           # Asset primitives documentation
│   ├── SKILL.md
│   └── docs/overview.md
├── cpp_blueprint_api/       # Blueprint primitives documentation
│   ├── SKILL.md
│   └── docs/overview.md
├── cpp_blueprint_write_api/ # Blueprint write operations (variables/graphs/nodes/batch)
│   ├── SKILL.md
│   ├── docs/overview.md
│   └── scripts/
│       ├── create_blueprint_with_components.py
│       ├── patch_graph_nodes.py
│       └── batch_refactor_blueprints.py
├── cpp_world_api/           # World/Level primitives documentation
│   ├── SKILL.md
│   └── docs/overview.md
├── cpp_editor_api/          # Editor operations documentation
│   ├── SKILL.md
│   └── docs/overview.md
├── cpp_validation_api/      # Validation primitives documentation
│   ├── SKILL.md
│   └── docs/overview.md
└── skill_script/            # Example executable skill
    ├── SKILL.md
    └── scripts/echo_args.py
```

### SKILL.md Format

```yaml
---
name: cpp_asset_api
description: CppSkillApiSubsystem asset primitives (rename/duplicate/delete/save)
tags: [cpp, asset]
---

# CppSkillApiSubsystem - AssetOps

Documentation content...
```

### Using Skills (Agent Workflow)

```python
# 1. Discover available skills
skills = await list_unreal_skill()
# Returns: [{name, description, tags, skill_root}, ...]

# 2. Read skill documentation
doc = await read_unreal_skill(skill_name="cpp_asset_api")
# Returns: {content: "...", tree: ["SKILL.md", "docs/overview.md"]}

# 3. Read detailed API docs
api_doc = await read_unreal_skill(skill_name="cpp_asset_api", path="docs/overview.md")

# 4. Execute inline Python using the API
result = await run_unreal_skill(python="""
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
success, error = api.rename_asset("/Game/OldName", "/Game/NewName")
RESULT = {"success": success, "error": error}
""")
```

### CppSkillApiSubsystem Primitives

| Category | Operations |
|----------|------------|
| **Asset** | `RenameAsset`, `DuplicateAsset`, `DeleteAsset`, `SaveAsset` |
| **Blueprint** | `CreateBlueprint`, `CompileBlueprint`, `SaveBlueprint`, `SetBlueprintCDOPropertyByString`, `AddBlueprintComponent`, `RemoveBlueprintComponent`, `Add/Remove/RenameBlueprintVariable`, `SetBlueprintVariableDefault`, `Add/Remove/RenameBlueprintGraph`, `Add/RemoveBlueprintNode`, `ConnectBlueprintPins`, `SetBlueprintPinDefault`, `ExecuteBlueprintCommands` |
| **World** | `LoadMap`, `SpawnActorByClassPath`, `FindActorByName`, `DestroyActorByName`, `SetActorPropertyByString`, `SetActorTransformByName` |
| **Editor** | `ListDirtyPackages`, `SaveDirtyPackages`, `UndoLastTransaction`, `RedoLastTransaction` |
| **Validation** | `CompileAllBlueprintsSummary` |

## Plugin Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `Auto Start MCP Server` | Start MCP when Editor launches | `false` |
| `Uv Executable` | Path to uv binary | `uv` |
| `Transport` | MCP transport mode | `http` |
| `MCP Port` | HTTP/SSE listen port | `19840` |
| `Cpp Source Path` | Project C++ source root | Auto-detect |
| `Unreal Engine Source Path` | Engine source for analysis | Auto-detect |

## Example Usage

### Analysis: Trace a GAS Ability

```
User: Help me trace how GA_Hero_Dash is triggered and executed

Agent:
[Uses search, get_hierarchy, get_blueprint_graph...]

GA_Hero_Dash complete flow:

Trigger path:
Player presses Shift → IA_Dash → IC_Default_KBM 
  → ULyraHeroComponent::Input_AbilityInputTagPressed()
  → ULyraAbilitySystemComponent::TryActivateAbility(Ability.Dash)

Execution logic (EventGraph):
1. ActivateAbility → IsLocallyControlled?
2. SelectDirectionalMontage → Set Direction
3. CommitAbility → PlayMontageAndWait
4. ApplyRootMotionConstantForce
5. Delay → EndAbility
```

### Skill: Batch Rename Assets

```
User: Rename all blueprints in /Game/Characters/ that start with "Old_" to "New_"

Agent:
[Uses list_unreal_skill to find cpp_asset_api, read_unreal_skill to understand API]

result = await run_unreal_skill(python="""
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
registry = unreal.AssetRegistryHelpers.get_asset_registry()

# Find matching assets
filter = unreal.ARFilter()
filter.package_paths = ["/Game/Characters"]
assets = registry.get_assets(filter)

renamed = []
for asset in assets:
    name = str(asset.asset_name)
    if name.startswith("Old_"):
        old_path = str(asset.package_name)
        new_path = old_path.replace("Old_", "New_")
        success, error = api.rename_asset(old_path, new_path)
        renamed.append({"old": old_path, "new": new_path, "success": success})

RESULT = {"renamed": renamed}
""")
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
  "plugin": "UnrealCopilot",
  "version": "0.4.0",
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
