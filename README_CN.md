# Unreal Project Analyzer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

用于分析 Unreal Engine 5 项目的 MCP 服务器 - 支持蓝图、资产和 C++ 源码分析。

> **目标**：让 AI 能够完整理解 Unreal 项目，跨越 Blueprint ↔ C++ ↔ Asset 边界追踪引用链。

**[English](README.md)**

## 特性

- **蓝图分析**：继承层次、依赖关系、节点图、变量、组件
- **资产引用追踪**：查找资产的依赖和被引用关系
- **C++ 源码分析**：类结构、UPROPERTY/UFUNCTION 检测（基于 tree-sitter）
- **跨域查询**：跨所有领域追踪完整引用链
- **编辑器集成**：直接从 Unreal Editor 菜单启动/停止 MCP 服务器

## 快速开始（推荐方式）

### 前置要求

- **Unreal Engine 5.3+**
- **[uv](https://docs.astral.sh/uv/)** - Python 包管理器（必需）

### 1. 安装插件

将 `UnrealProjectAnalyzer` 文件夹复制到你的 Unreal 项目的 `Plugins/` 目录：

```
YourProject/
├── Plugins/
│   └── UnrealProjectAnalyzer/    ← 这个文件夹
│       ├── Source/
│       ├── Mcp/
│       └── UnrealProjectAnalyzer.uplugin
```

### 2. 配置 uv 路径

1. 打开 Unreal Editor
2. 进入 **Edit → Project Settings → Plugins → Unreal Project Analyzer**
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

1. 在 Unreal Editor 菜单：**Tools → Unreal Project Analyzer → Start MCP Server**
2. 检查 Output Log 是否显示：`LogMcpServer: MCP Server process started`
3. 通过 **Tools → Unreal Project Analyzer → Copy MCP URL** 复制 MCP 地址

### 4. 连接 Cursor

在 Cursor 的 MCP 设置中添加（使用复制的 URL）：

```json
{
  "mcpServers": {
    "unreal-project-analyzer": {
      "url": "http://127.0.0.1:19840/mcp"
    }
  }
}
```

## 替代方案：手动运行 MCP 服务器

如果你更喜欢在 Unreal Editor 外部运行 MCP 服务器：

```bash
cd /path/to/UnrealProjectAnalyzer

# 安装依赖
uv sync

# 以 stdio 方式运行（用于 Cursor MCP 集成）
uv run unreal-analyzer -- \
  --cpp-source-path "/path/to/YourProject/Source" \
  --ue-plugin-host "localhost" \
  --ue-plugin-port 8080

# 或以 HTTP 服务器方式运行（便于快速连接）
uv run unreal-analyzer -- \
  --transport http \
  --mcp-host 127.0.0.1 \
  --mcp-port 19840 \
  --cpp-source-path "/path/to/YourProject/Source"
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
│  │            C++ 源码分析器 (tree-sitter)                     │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│            UnrealProjectAnalyzer 插件 (Editor 内运行)             │
│  ┌─────────────────────────┐  ┌────────────────────────────────┐ │
│  │   HTTP Server (:8080)   │  │   MCP 启动器 (uv 进程)          │ │
│  │   蓝图/资产 API          │  │   从 Editor 自动启动            │ │
│  └─────────────────────────┘  └────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## 可用工具

### 蓝图工具
| 工具 | 描述 |
|------|------|
| `search_blueprints` | 按名称模式和类过滤器搜索蓝图 |
| `get_blueprint_hierarchy` | 获取类继承链 |
| `get_blueprint_dependencies` | 获取所有依赖 |
| `get_blueprint_referencers` | 获取所有引用者 |
| `get_blueprint_graph` | 获取节点图（EventGraph、函数） |
| `get_blueprint_details` | 获取变量、函数、组件详情 |

### 资产工具
| 工具 | 描述 |
|------|------|
| `search_assets` | 按名称/类型搜索资产 |
| `get_asset_references` | 获取引用的资产 |
| `get_asset_referencers` | 获取引用此资产的资产 |
| `get_asset_metadata` | 获取资产元数据 |

### C++ 分析工具
| 工具 | 描述 |
|------|------|
| `analyze_cpp_class` | 分析类结构（方法、属性） |
| `get_cpp_class_hierarchy` | 获取继承层次 |
| `search_cpp_code` | 使用正则表达式搜索源码 |
| `find_cpp_references` | 查找标识符引用 |
| `detect_ue_patterns` | 检测 UPROPERTY/UFUNCTION 模式 |
| `get_cpp_blueprint_exposure` | 获取暴露给蓝图的 API |

### 跨域工具
| 工具 | 描述 |
|------|------|
| `trace_reference_chain` | 跨域追踪完整引用链 |
| `find_cpp_class_usage` | 查找 C++ 类在蓝图中的使用 |

## 插件设置

| 设置 | 描述 | 默认值 |
|------|------|--------|
| `Auto Start MCP Server` | Editor 启动时自动启动 MCP | `false` |
| `Uv Executable` | uv 可执行文件路径 | `uv` |
| `Capture Server Output` | 将 MCP 输出打印到 UE Log | `true` |
| `Transport` | MCP 传输模式 | `http` |
| `MCP Port` | HTTP/SSE 监听端口 | `19840` |
| `Cpp Source Path` | 项目 C++ 源码根目录 | 自动检测 |
| `Unreal Engine Source Path` | 引擎源码路径（用于分析引擎类） | 自动检测 |

## 使用示例

### 追踪 GAS 能力

```
用户: 帮我追踪 GA_Hero_Dash 这个能力是怎么触发和执行的

AI Agent:
[使用 search_blueprints, get_blueprint_details, get_blueprint_graph...]

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

### 查找资产引用

```
用户: B_Hero_Default 被哪些地方引用了？

AI Agent:
[使用 get_blueprint_referencers, trace_reference_chain...]

B_Hero_Default 引用情况：

直接引用者:
├─ B_Hero_ShooterMannequin (蓝图)
├─ B_Hero_Explorer (蓝图)
├─ DA_HeroData_Default (数据资产)
└─ ... (共 8 个资产)

间接引用者 (通过 Experience):
├─ B_LyraDefaultExperience
├─ B_ShooterGame_Elimination
└─ ...
```

## 常见问题

### MCP 服务器启动失败

1. **检查 uv 路径**：确保在设置中填写了正确的 uv 完整路径
2. **检查端口冲突**：默认端口 19840，如有冲突可在设置中修改
3. **查看日志**：Output Log 中搜索 `LogMcpServer` 查看详细错误

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
```

## 致谢

本项目参考了以下优秀项目的实现方案：

- **[unreal-analyzer-mcp](https://github.com/ayeletstudioindia/unreal-analyzer-mcp)** - C++ 源码分析方案（tree-sitter）
- **[ue5-mcp](https://github.com/cutehusky/ue5-mcp)** - Unreal Editor HTTP API 暴露方案

## 许可证

MIT
