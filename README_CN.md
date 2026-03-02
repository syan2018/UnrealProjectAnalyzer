# Unreal Copilot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

用于**分析和编辑** Unreal Engine 5 项目的 MCP 服务器 - 支持蓝图、资产、C++ 源码分析，以及可执行的 Skill 技能系统。

> **目标**：让 AI 能够完整理解 Unreal 项目，跨越 Blueprint ↔ C++ ↔ Asset 边界追踪引用链，**并通过 Skill 系统执行编辑器操作**。

**[English](README.md)**

## 特性

- **蓝图分析**：继承层次、依赖关系、节点图、变量、组件
- **资产引用追踪**：查找资产的依赖和被引用关系
- **C++ 源码分析**：类结构、UPROPERTY/UFUNCTION 检测（基于 tree-sitter）
- **跨域查询**：跨所有领域追踪完整引用链
- **编辑器集成**：直接从 Unreal Editor 菜单启动/停止 MCP 服务器
- **搜索范围控制**：支持只搜索项目代码、引擎代码或全部
- **统一搜索**：类似 grep 的跨域统一搜索接口
- **🆕 Skill 技能系统 (v0.4.0)**：可发现、可阅读、可执行的编辑器能力

## v0.4.0 新特性

- **Skill 技能系统**：3 个新 MCP 工具，用于发现和执行编辑器能力
  - `list_unreal_skill` - 发现可用技能
  - `read_unreal_skill` - 阅读技能文档和脚本
  - `run_unreal_skill` - 执行技能脚本或内联 Python
- **CppSkillApiSubsystem**：C++ 编辑器原语（资产/蓝图/世界/编辑器/验证）
- **事件驱动 MCP 生命周期**：Python→C++ 通知替代不可靠的端口探测
- **重命名**：`UAnalyzerSubsystem` → `UMcpServerSubsystem`（反映实际用途）

## Blueprint 编辑能力规划

- [Blueprint 增删改能力实施规划](Docs/BLUEPRINT_EDITING_PLAN.md)

### 历史版本

<details>
<summary>v0.3.x</summary>

- **进一步精简**：精简到 **8 个工具**（4 核心 + 4 特殊）
- **最小参数**：删除冗余参数，降低认知负担
- **软引用追踪**：Blueprint CDO 变量默认值现在包含在引用链中
- **Mermaid 输出**：`get_blueprint_graph` 默认输出 Mermaid 格式，便于可视化
- **C++ 引用聚合**：按文件分组结果，区分定义和使用

</details>

## 快速开始（推荐方式）

### 前置要求

- **Unreal Engine 5.3+**
- **[uv](https://docs.astral.sh/uv/)** - Python 包管理器（必需）

### 0. 首次使用：建议先手动同步依赖（强烈推荐）

插件支持在 Editor 内自动安装依赖，但**第一次使用**强烈建议你先在 Editor 外手动跑一次（更稳定，也更容易排错）：

```powershell
cd <PluginRoot>\Content\Python
uv sync
```

执行完成后再打开 Unreal Editor，并点击 Start MCP Server。

### 1. 安装插件

将 `UnrealCopilot` 文件夹复制到你的 Unreal 项目的 `Plugins/` 目录：

```
YourProject/
├── Plugins/
│   └── UnrealCopilot/    ← 这个文件夹
│       ├── Source/
│       ├── Content/
│       ├── skills/       ← 技能定义
│       └── UnrealCopilot.uplugin
```

### 2. 配置 uv 路径

1. 打开 Unreal Editor
2. 进入 **Edit → Project Settings → Plugins → Unreal Copilot**
3. 设置 **Uv Executable** 为你的 uv 安装路径，例如：
   - Windows: `C:\Users\你的用户名\.local\bin\uv.exe` 或 `C:\Users\你的用户名\anaconda3\Scripts\uv.exe`
   - macOS/Linux: `/usr/local/bin/uv` 或 `~/.local/bin/uv`

**如何找到 uv 路径？**
```powershell
# Windows PowerShell
Get-Command uv | Select-Object -ExpandProperty Source

# macOS/Linux
which uv
```

### 3. 启动 MCP 服务器

1. 在 Unreal Editor 菜单：**Tools → Unreal Copilot → Start MCP Server**
2. 检查 Output Log / 通知是否显示：`MCP Server is running`
3. 通过 **Tools → Unreal Copilot → Copy MCP URL** 复制 MCP 地址

### 4. 连接 Cursor

在 Cursor 的 MCP 设置中添加（使用复制的 URL）：

```json
{
  "mcpServers": {
    "unreal-copilot": {
      "url": "http://127.0.0.1:19840/mcp"
    }
  }
}
```

## 架构

```
┌──────────────────────────────────────────────────────────────────┐
│                       AI Agent (Cursor)                          │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ MCP Protocol
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                  MCP Server (Python/FastMCP)                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  分析工具              │  技能工具                          │  │
│  │  (search, refs...)    │  (list/read/run_unreal_skill)      │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  C++ 分析器 (tree-sitter)  │  SkillRunner (Python)         │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP / import unreal
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│              UnrealCopilot 插件 (Editor 内运行)                   │
│  ┌─────────────────────────┐  ┌────────────────────────────────┐ │
│  │   HTTP Server (:8080)   │  │   CppSkillApiSubsystem         │ │
│  │   蓝图/资产 API          │  │   (资产/蓝图/世界/编辑器操作)    │ │
│  └─────────────────────────┘  └────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │   MCP Server (UE Python) - 由 McpServerSubsystem 管理        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## 可用工具（共 11 个）

### 分析工具（8 个）

| 工具 | 描述 |
|------|------|
| `search` | 统一搜索 C++/蓝图/资产 |
| `get_hierarchy` | 获取继承层次（C++ 或蓝图） |
| `get_references` | 获取引用关系（出/入/双向） |
| `get_details` | 获取详细信息（C++/蓝图/资产） |
| `get_blueprint_graph` | 蓝图节点图（Mermaid/摘要/JSON） |
| `detect_ue_patterns` | UE 宏检测（UPROPERTY/UFUNCTION/UCLASS） |
| `trace_reference_chain` | 跨域引用链追踪 |
| `find_cpp_class_usage` | C++ 类在蓝图和 C++ 中的使用 |

### 技能工具（3 个）

| 工具 | 参数 | 描述 |
|------|------|------|
| `list_unreal_skill` | `query?` | 列出可用技能（名称、描述、标签） |
| `read_unreal_skill` | `skill_name`, `path?` | 读取技能文件（默认：SKILL.md + 目录树） |
| `run_unreal_skill` | `skill_name?`, `script?`, `args?`, `python?` | 执行技能脚本或内联 Python |

## Skill 技能系统

技能是可发现、有文档、可执行的编辑器能力，AI Agent 可以查找、理解并执行它们。

### 技能目录结构

```
UnrealCopilot/skills/
├── cpp_asset_api/           # 资产原语文档
│   ├── SKILL.md
│   └── docs/overview.md
├── cpp_blueprint_api/       # 蓝图原语文档
│   ├── SKILL.md
│   └── docs/overview.md
├── cpp_blueprint_write_api/ # 蓝图写入能力（变量/图/节点/批处理）
│   ├── SKILL.md
│   ├── docs/overview.md
│   └── scripts/
│       ├── create_blueprint_with_components.py
│       ├── patch_graph_nodes.py
│       └── batch_refactor_blueprints.py
├── cpp_world_api/           # 世界/关卡原语文档
│   ├── SKILL.md
│   └── docs/overview.md
├── cpp_editor_api/          # 编辑器操作文档
│   ├── SKILL.md
│   └── docs/overview.md
├── cpp_validation_api/      # 验证原语文档
│   ├── SKILL.md
│   └── docs/overview.md
└── skill_script/            # 示例可执行技能
    ├── SKILL.md
    └── scripts/echo_args.py
```

### SKILL.md 格式

```yaml
---
name: cpp_asset_api
description: CppSkillApiSubsystem 资产原语（重命名/复制/删除/保存）
tags: [cpp, asset]
---

# CppSkillApiSubsystem - AssetOps

文档内容...
```

### 使用技能（Agent 工作流）

```python
# 1. 发现可用技能
skills = await list_unreal_skill()
# 返回: [{name, description, tags, skill_root}, ...]

# 2. 阅读技能文档
doc = await read_unreal_skill(skill_name="cpp_asset_api")
# 返回: {content: "...", tree: ["SKILL.md", "docs/overview.md"]}

# 3. 阅读详细 API 文档
api_doc = await read_unreal_skill(skill_name="cpp_asset_api", path="docs/overview.md")

# 4. 使用 API 执行内联 Python
result = await run_unreal_skill(python="""
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
success, error = api.rename_asset("/Game/OldName", "/Game/NewName")
RESULT = {"success": success, "error": error}
""")
```

### CppSkillApiSubsystem 原语

| 分类 | 操作 |
|------|------|
| **资产** | `RenameAsset`, `DuplicateAsset`, `DeleteAsset`, `SaveAsset` |
| **蓝图** | `CreateBlueprint`, `CompileBlueprint`, `SaveBlueprint`, `SetBlueprintCDOPropertyByString`, `AddBlueprintComponent`, `RemoveBlueprintComponent`, `Add/Remove/RenameBlueprintVariable`, `SetBlueprintVariableDefault`, `Add/Remove/RenameBlueprintGraph`, `Add/RemoveBlueprintNode`, `ConnectBlueprintPins`, `SetBlueprintPinDefault`, `ExecuteBlueprintCommands` |
| **世界** | `LoadMap`, `SpawnActorByClassPath`, `FindActorByName`, `DestroyActorByName`, `SetActorPropertyByString`, `SetActorTransformByName` |
| **编辑器** | `ListDirtyPackages`, `SaveDirtyPackages`, `UndoLastTransaction`, `RedoLastTransaction` |
| **验证** | `CompileAllBlueprintsSummary` |

## 插件设置

| 设置 | 描述 | 默认值 |
|------|------|--------|
| `Auto Start MCP Server` | Editor 启动时自动启动 MCP | `false` |
| `Uv Executable` | uv 可执行文件路径 | `uv` |
| `Transport` | MCP 传输模式 | `http` |
| `MCP Port` | HTTP/SSE 监听端口 | `19840` |
| `Cpp Source Path` | 项目 C++ 源码根目录 | 自动检测 |
| `Unreal Engine Source Path` | 引擎源码路径（用于分析引擎类） | 自动检测 |

## 使用示例

### 分析：追踪 GAS 能力

```
用户: 帮我追踪 GA_Hero_Dash 这个能力是怎么触发和执行的

AI Agent:
[使用 search, get_hierarchy, get_blueprint_graph...]

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
```

### 技能：批量重命名资产

```
用户: 把 /Game/Characters/ 下所有以 "Old_" 开头的蓝图重命名为 "New_" 开头

AI Agent:
[使用 list_unreal_skill 发现 cpp_asset_api，read_unreal_skill 理解 API]

result = await run_unreal_skill(python="""
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
registry = unreal.AssetRegistryHelpers.get_asset_registry()

# 查找匹配的资产
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

## 健康检查

验证 UE 插件是否运行：

```bash
curl http://localhost:8080/health
```

返回：
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

## 常见问题

### MCP 服务器启动失败

1. **检查 uv 路径**：确保在设置中填写了正确的 uv 完整路径
2. **检查端口冲突**：默认端口 19840，如有冲突可在设置中修改
3. **查看日志**：Output Log 中搜索 `LogMcpServerSubsystem` 查看详细错误

### 连接 Cursor 失败

1. **确认 MCP 服务器已启动**：检查 Output Log 中的启动日志
2. **检查 URL**：使用 Copy MCP URL 功能获取正确地址
3. **防火墙**：确保本地端口未被防火墙阻止

## 开发

```bash
# 安装开发依赖
uv sync --all-extras

# 运行测试
uv run pytest

# 代码检查
uv run ruff check .

# 打印配置（调试用）
uv run unreal-analyzer --print-config
```

## 致谢

本项目参考了以下优秀项目的实现方案：

- **[unreal-analyzer-mcp](https://github.com/ayeletstudioindia/unreal-analyzer-mcp)** - C++ 源码分析方案（tree-sitter）
- **[ue5-mcp](https://github.com/cutehusky/ue5-mcp)** - Unreal Editor HTTP API 暴露方案

## 许可证

MIT
