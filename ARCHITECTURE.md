# UnrealCopilot - 架构说明

## 概述

UnrealCopilot 使用 **UE 内置 Python 环境** 运行 MCP Server，类似于 UnrealRemoteMCP 的架构。这提供了更好的集成和更简化的环境管理。

## 架构特点

- MCP Server 在 UE 内置 Python 环境中运行
- 所有 Python 代码统一放在 `Content/Python/` 目录下
- 依赖通过 `uv sync` 自动管理到 `Content/Python/.venv`（启动时自动加入 `sys.path`）
- 通过 `AnalyzerSubsystem` 管理 MCP Server 生命周期
- 更简洁的导入路径，无需修改 sys.path

## 组件说明

### Python 组件

#### `Content/Python/init_analyzer.py`
- MCP Server 初始化脚本
- 在 UE 进程内启动 MCP Server
- 提供启动/停止/状态查询接口

#### `Content/Python/uv_sync.py`
- 自动依赖管理脚本
- 检查并安装缺失的依赖
- 在启动时自动运行

#### `Content/Python/unreal_copilot/`
- MCP Server 核心代码
- `server.py`: MCP Server 入口点
- `config.py`: 配置管理
- `tools/`: MCP 工具实现（blueprint, cpp, unified, cross_domain, skills）
- `cpp_analyzer/`: C++ 代码分析器（基于 tree-sitter）
- `ue_client/`: UE 插件 HTTP 客户端
- `skills/`: SkillRunner（发现/阅读/执行技能脚本）

#### `skills/`
- 技能包目录（`SKILL.md` + `scripts/` + 可选 `docs/`）

### C++ 组件

#### 目录结构（模块内分区）
- `Source/UnrealCopilot/Private/Bridge`: UE Python 桥接与 Subsystem 生命周期
- `Source/UnrealCopilot/Private/Skill`: CppSkillApiSubsystem 原语实现
- `Source/UnrealCopilot/Private/Http`: HTTP 路由与工具
- `Source/UnrealCopilot/Private/`: 模块入口与编辑器集成（UnrealCopilot.cpp）
- `Source/UnrealCopilot/Public/Bridge`: 对外暴露的 Bridge 头文件
- `Source/UnrealCopilot/Public/Skill`: 对外暴露的 Skill 头文件
- `Source/UnrealCopilot/Public/Settings`: 插件设置相关头文件
- `Source/UnrealCopilot/Public/`: 模块入口头文件（UnrealCopilot.h）

#### `AnalyzerSubsystem`
- 管理 MCP Server 生命周期
- 提供 Blueprint 函数和编辑器命令
- 自动处理 Python 初始化

#### `UnrealCopilotModule`
- 主模块，负责：
  - HTTP API 服务器（端口 8080）
  - 编辑器集成（菜单、设置）
  - Subsystem 生命周期管理

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

### 自动同步

首次启动时，`uv_sync.py` 会自动：
1. 检查依赖是否已安装
2. 如果缺失，自动运行 `uv sync`
3. 将依赖安装到 `.venv`（并在运行时加入 `sys.path`）

## 使用方法

### 通过编辑器菜单

1. 打开 Unreal Editor
2. 菜单：**Tools → Unreal Copilot → Start MCP Server**
3. 查看 Output Log 确认启动成功
4. 复制 MCP URL 用于配置 AI 工具

### 通过蓝图

```cpp
// 获取 Subsystem
UAnalyzerSubsystem* Subsystem = UAnalyzerSubsystem::Get();

// 启动 MCP Server
Subsystem->StartAnalyzer();

// 检查运行状态
if (Subsystem->IsAnalyzerRunning())
{
    // Server is running
}

// 停止 MCP Server
Subsystem->StopAnalyzer();
```

### 通过 Python

```python
import init_analyzer

# 启动服务器
init_analyzer.start_analyzer_server(
    transport="http",
    host="127.0.0.1",
    port=8000,
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

## MCP 工具

UnrealCopilot 提供以下 MCP 工具：

### 核心工具（4个）
- `search`: 统一搜索（C++/Blueprint/Asset）
- `get_hierarchy`: 获取继承层次结构
- `get_references`: 获取引用关系（incoming/outgoing/both）
- `get_details`: 获取详细信息（C++/Blueprint/Asset）

### 特殊工具（3个，需要 UE 插件支持）
- `get_blueprint_graph`: 获取蓝图节点图
- `trace_reference_chain`: 追踪完整引用链
- `find_cpp_class_usage`: 查找 C++ 类使用情况

### C++ 特殊工具
- `detect_ue_patterns`: 检测 UE 宏（UPROPERTY/UFUNCTION/UCLASS）

## 与 UnrealRemoteMCP 的对比

| 特性 | UnrealRemoteMCP | UnrealCopilot |
|------|-----------------|----------------------|
| 用途 | 通用 UE 操作和自动化 | 项目分析和代码理解 |
| Python 环境 | UE 内置 | UE 内置 |
| 依赖管理 | uv pip install + env.bat | uv sync（自动） |
| 工具类型 | 通用编辑器工具 | 分析专用工具 |
| HTTP API | 用于外部 AI 控制 | 用于蓝图/资产查询 |

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

## 故障排除

### MCP Server 无法启动

1. 检查 Python 插件是否已启用
2. 检查依赖是否正确安装
3. 查看 Output Log 中的错误信息

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


