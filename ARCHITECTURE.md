# UnrealCopilot - 架构说明

## 概述

UnrealCopilot 使用 **UE 内置 Python 环境** 运行 MCP Server。这提供了更好的集成和更简化的环境管理。

**v0.4.0 新增**：Skill 技能系统，支持 AI Agent 发现、阅读和执行编辑器操作。

## 架构特点

- MCP Server 在 UE 内置 Python 环境中运行
- 所有 Python 代码统一放在 `Content/Python/` 目录下
- 依赖通过 `uv sync` 自动管理到 `Content/Python/.venv`（启动时自动加入 `sys.path`）
- 通过 `McpServerSubsystem` 管理 MCP Server 生命周期（事件驱动，Python 主动通知 C++）
- Skill 系统提供可发现、可执行的编辑器能力

## 组件说明

### Python 组件

#### `Content/Python/init_analyzer.py`
- MCP Server 初始化脚本
- 在 UE 进程内启动 MCP Server
- 提供启动/停止/状态查询接口
- **事件驱动**：主动通知 C++ 状态变化（starting/running/stopped/failed）

#### `Content/Python/uv_sync.py`
- 自动依赖管理脚本
- 检查并安装缺失的依赖
- 在启动时自动运行

#### `Content/Python/unreal_copilot/`
- MCP Server 核心代码
- `server.py`: MCP Server 入口点
- `config.py`: 配置管理
- `tools/`: MCP 工具实现
  - `unified.py`: 统一搜索工具
  - `blueprint.py`: 蓝图分析工具
  - `cpp.py`: C++ 分析工具
  - `asset.py`: 资产分析工具
  - `cross_domain.py`: 跨域分析工具
  - `skills.py`: Skill 工具（list/read/run）
- `cpp_analyzer/`: C++ 代码分析器（基于 tree-sitter）
- `ue_client/`: UE 插件 HTTP 客户端
- `skills/`: SkillRunner（发现/阅读/执行技能脚本）

#### `skills/`（插件根目录）
- 技能包目录
- 每个技能包含：
  - `SKILL.md`: 技能说明（YAML 题头 + Markdown 正文）
  - `scripts/`: 可执行 Python 脚本
  - `docs/`: 详细文档（可选）

### C++ 组件

#### 目录结构（模块内分区）
- `Source/UnrealCopilot/Private/Bridge/`: MCP Server 生命周期管理
  - `McpServerSubsystem.cpp`: MCP Server 子系统（事件驱动状态管理）
- `Source/UnrealCopilot/Private/Skill/`: CppSkillApiSubsystem 原语实现
  - `CppSkillApiSubsystem.cpp`: 子系统入口
  - `CppSkillApiSubsystem.Asset.cpp`: 资产操作
  - `CppSkillApiSubsystem.Blueprint.cpp`: 蓝图操作
  - `CppSkillApiSubsystem.World.cpp`: 世界/Actor 操作
  - `CppSkillApiSubsystem.Editor.cpp`: 编辑器操作（保存/撤销）
  - `CppSkillApiSubsystem.Validation.cpp`: 验证操作
  - `CppSkillApiSubsystem.Helpers.cpp`: 辅助函数
- `Source/UnrealCopilot/Private/Http/`: HTTP API 路由与工具
- `Source/UnrealCopilot/Private/`: 模块入口与编辑器集成
- `Source/UnrealCopilot/Public/`: 对外暴露的头文件

#### `McpServerSubsystem`（原 AnalyzerSubsystem）
- 管理 MCP Server 生命周期
- **事件驱动**：不再使用端口探测，而是接收 Python 的状态通知
- 提供 Blueprint 函数和编辑器命令
- 自动处理 Python 初始化

#### `CppSkillApiSubsystem`
- 提供可被 UE Python/Skill 脚本调用的编辑原语
- 分为 5 个域：Asset、Blueprint、World、Editor、Validation
- 所有方法都是 BlueprintCallable，可从 Python 调用

#### `UnrealCopilotModule`
- 主模块，负责：
  - 内部插件 HTTP API 服务器（默认端口 8080）
  - 编辑器集成（菜单、设置）
  - Subsystem 生命周期管理

> 端口说明：
> - `McpPort` 默认 `19840`，供外部 MCP 客户端连接。
> - `UePluginPort` 默认 `8080`，供 UE 内 Python MCP 服务回调插件内部 HTTP API。
> - 两者职责不同，默认不应配置成同一个端口。

## Skill 技能系统

### 设计理念

Skill 是可发现、有文档、可执行的编辑器能力：
- **可发现**：AI Agent 通过 `list_unreal_skill` 发现可用技能
- **有文档**：每个技能都有 `SKILL.md` 说明用途和用法
- **可执行**：通过 `run_unreal_skill` 执行脚本或内联 Python

### 技能包结构

```
skills/<skill_name>/
├── SKILL.md              # 技能说明（必需）
├── scripts/              # 可执行脚本（可选）
│   └── *.py
└── docs/                 # 详细文档（可选）
    └── *.md
```

### SKILL.md 格式

```yaml
---
name: skill_name
description: 技能简短描述
tags: [tag1, tag2]
---

# 技能标题

详细说明...
```

### MCP 工具

| 工具 | 参数 | 描述 |
|------|------|------|
| `list_unreal_skill` | `query?`, `include_hidden?` | 列出可用技能 |
| `read_unreal_skill` | `skill_name`, `path?` | 读取技能文件 |
| `run_unreal_skill` | `skill_name?`, `script?`, `args?`, `python?` | 执行技能 |

### 执行模式

1. **脚本模式**：指定 `skill_name` + `script`，执行技能包中的脚本
2. **内联模式**：指定 `python`，直接执行内联 Python 代码

### CppSkillApiSubsystem 原语

| 分类 | 操作 |
|------|------|
| **Asset** | RenameAsset, DuplicateAsset, DeleteAsset, SaveAsset |
| **Blueprint** | CreateBlueprint, CompileBlueprint, SaveBlueprint, SetBlueprintCDOPropertyByString, AddBlueprintComponent, RemoveBlueprintComponent |
| **World** | LoadMap, SpawnActorByClassPath, FindActorByName, DestroyActorByName, SetActorPropertyByString, SetActorTransformByName |
| **Editor** | ListDirtyPackages, SaveDirtyPackages, UndoLastTransaction, RedoLastTransaction |
| **Validation** | CompileAllBlueprintsSummary |

## 依赖管理

### 安装依赖

依赖通过 `uv` 和 `pyproject.toml` 管理：

```bash
# 在 Content/Python 目录执行
cd UnrealCopilot/Content/Python
uv sync
```

或使用自动安装（推荐）：
- 启动 UE Editor 时自动检查并安装依赖
- 无需手动操作

### 依赖声明

所有依赖在 `Content/Python/pyproject.toml` 中声明：
- `fastmcp>=2.0.0`: MCP 框架
- `httpx>=0.27.0`: HTTP 客户端
- `tree-sitter>=0.23.0`: C++ 代码解析
- `tree-sitter-cpp>=0.23.0`: C++ 语言支持

## 使用方法

### 通过编辑器菜单

1. 打开 Unreal Editor
2. 菜单：**Tools → Unreal Copilot → Start MCP Server**
3. 查看 Output Log 确认启动成功
4. 复制 MCP URL 用于配置 AI 工具

### 通过蓝图/C++

```cpp
// 获取 Subsystem
UMcpServerSubsystem* Subsystem = UMcpServerSubsystem::Get();

// 启动 MCP Server
Subsystem->StartMcpServer();

// 检查运行状态
if (Subsystem->IsMcpServerRunning())
{
    // Server is running
}

// 停止 MCP Server
Subsystem->StopMcpServer();
```

### 通过 Python

```python
import init_analyzer

# 启动服务器
init_analyzer.start_analyzer_server(
    transport="http",
    host="127.0.0.1",
    port=19840,
    path="/mcp",
    cpp_source_path="D:/MyProject/Source",
    unreal_engine_path="D:/UE_5.3/Engine/Source"
)

# 检查状态
status = init_analyzer.get_server_status()
print(f"Running: {status['running']}")

# 停止服务器
init_analyzer.stop_analyzer_server()
```

## 配置选项

在 **Edit → Project Settings → Plugins → Unreal Copilot** 中配置：

### Launcher 设置
- **Auto Start MCP Server**: 是否在 Editor 启动时自动启动 MCP Server

### Transport 设置
- **Transport**: 传输协议（stdio/http/sse）
- **Host**: HTTP/SSE 监听地址（默认：127.0.0.1）
- **Port**: HTTP/SSE 监听端口（默认：19840）
- **Path**: HTTP MCP path（默认：/mcp）

### Analyzer 设置
- **C++ Source Path**: 项目 C++ 源码路径（默认：<Project>/Source）
- **Unreal Engine Source Path**: 引擎源码路径（可选）
- **UE Plugin Host**: 内部插件 HTTP API host（默认：127.0.0.1）
- **UE Plugin Port**: 内部插件 HTTP API 端口（默认：8080）

## MCP 工具

UnrealCopilot 提供以下 MCP 工具：

### 分析工具（8个）
- `search`: 统一搜索（C++/Blueprint/Asset）
- `get_hierarchy`: 获取继承层次结构
- `get_references`: 获取引用关系（incoming/outgoing/both）
- `get_details`: 获取详细信息（C++/Blueprint/Asset）
- `get_blueprint_graph`: 获取蓝图节点图
- `detect_ue_patterns`: 检测 UE 宏（UPROPERTY/UFUNCTION/UCLASS）
- `trace_reference_chain`: 追踪完整引用链
- `find_cpp_class_usage`: 查找 C++ 类使用情况

### 技能工具（3个）
- `list_unreal_skill`: 列出可用技能
- `read_unreal_skill`: 读取技能文档/脚本
- `run_unreal_skill`: 执行技能脚本或内联 Python

## 开发工作流

### 修改 Python 代码

1. 编辑 `Content/Python/` 下的 Python 文件
2. 在 UE Editor 中重新启动 MCP Server
3. 无需重启 Editor

### 修改 MCP Server 代码

1. 编辑 `Content/Python/unreal_copilot/` 下的代码
2. 无需重新安装（代码直接在 Content/Python 下）
3. 在 UE Editor 中重新启动 MCP Server（Tools → Unreal Copilot → Stop/Start）

### 修改 C++ 代码

1. 编辑 C++ 源文件
2. 编译插件
3. 重启 UE Editor

### 添加新技能

1. 在 `skills/` 下创建新目录
2. 创建 `SKILL.md`（包含 YAML 题头）
3. 可选：添加 `scripts/` 和 `docs/`
4. 重启 MCP Server 即可发现新技能

## 故障排除

### MCP Server 无法启动

1. 检查 Python 插件是否已启用
2. 检查依赖是否正确安装
3. 查看 Output Log 中的错误信息（搜索 `LogMcpServerSubsystem`）

### 依赖缺失

手动执行依赖安装：
```bash
cd <PluginRoot>/Content/Python
uv sync
```

### 添加新依赖

编辑 `Content/Python/pyproject.toml`，添加依赖到 `dependencies` 数组：
```toml
dependencies = [
    "fastmcp>=2.0.0",
    "httpx>=0.27.0",
    "tree-sitter>=0.23.0",
    "tree-sitter-cpp>=0.23.0",
    "your-new-package>=1.0.0",  # 添加新依赖
]
```

然后重新同步：
```bash
cd Content/Python
uv sync
```

### HTTP API 无响应

1. 检查端口是否被占用
2. 确认 MCP Server 已启动
3. 查看防火墙设置

## 未来改进

- [ ] 添加热重载支持
- [ ] 改进错误处理和日志
- [ ] 添加性能监控
- [ ] 支持多实例
- [ ] 添加单元测试
- [ ] 更多 CppSkillApiSubsystem 原语
