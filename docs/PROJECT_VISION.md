# UE5 Project Analyzer MCP - 项目愿景与目标

> **一句话目标**：让 AI 能够完整追踪 UE5 项目中任意一条引用链，从入口到实现，跨越 Blueprint / C++ / Asset 边界。

---

## 一、核心场景

### 场景 1：追踪 GAS Ability 的完整实现

**用户提问**：
> "帮我追踪 GA_Hero_Dash 这个 Ability 从触发到执行的完整链路"

**Agent 应该能回答**：
```
GA_Hero_Dash (GameplayAbility Blueprint)
│
├─ 触发方式
│   ├─ InputAction: IA_Dash (EnhancedInput Asset)
│   ├─ 绑定位置: B_Hero_ShooterMannequin → InputComponent
│   └─ AbilityTag: Ability.Dash
│
├─ 激活流程
│   ├─ ULyraAbilitySystemComponent::TryActivateAbility()  [C++]
│   │   └─ 定义于: LyraAbilitySystemComponent.h:45
│   └─ UGameplayAbility::ActivateAbility()  [C++ Native]
│
├─ 执行逻辑
│   ├─ EventGraph 节点链:
│   │   ActivateAbility → ApplyRootMotion → PlayMontage → EndAbility
│   └─ 使用的 GameplayEffect: GE_Dash_Cost, GE_Dash_Cooldown
│
└─ 相关资产
    ├─ Montage: AM_Hero_Dash
    ├─ Curve: C_DashMotion
    └─ Sound: S_Dash_Whoosh
```

### 场景 2：理解一个角色的完整构成

**用户提问**：
> "B_Hero_ShooterMannequin 这个角色是怎么组装起来的？"

**Agent 应该能回答**：
```
B_Hero_ShooterMannequin
│
├─ 继承链
│   B_Hero_ShooterMannequin → B_Hero_Default → ALyraCharacter → ACharacter
│
├─ 组件构成
│   ├─ ULyraHealthComponent (管理生命值)
│   ├─ ULyraPawnExtensionComponent (Pawn 扩展数据)
│   ├─ ULyraAbilitySystemComponent (GAS 核心)
│   └─ ULyraHeroComponent (英雄特有逻辑)
│
├─ 能力配置
│   ├─ AbilitySet: AS_Hero_Shooter
│   │   ├─ GA_Hero_Jump
│   │   ├─ GA_Hero_Dash  
│   │   └─ GA_Weapon_Fire
│   └─ InputConfig: IC_Default_KBM
│
├─ 使用的资产
│   ├─ Skeleton: SK_Mannequin
│   ├─ AnimBlueprint: ABP_Mannequin
│   └─ Materials: [...]
│
└─ 被哪些地方引用
    ├─ BP_GameMode_ShooterGame (默认 Pawn 类)
    └─ DA_HeroData_Shooter (数据资产)
```

### 场景 3：追踪资产引用链

**用户提问**：
> "SK_Mannequin 这个骨骼被哪些地方用到了？"

**Agent 应该能回答**：
```
SK_Mannequin (Skeleton Asset)
│
├─ 直接引用
│   ├─ SKM_Mannequin (SkeletalMesh)
│   ├─ ABP_Mannequin (AnimBlueprint) 
│   └─ Phys_Mannequin (PhysicsAsset)
│
├─ 间接引用 (通过 Mesh)
│   ├─ B_Hero_ShooterMannequin
│   ├─ B_Hero_Default
│   └─ B_NPC_Enemy_Base
│
└─ 动画资产
    ├─ AM_Hero_Dash
    ├─ AM_Hero_Jump
    └─ ... (共 47 个 Montage)
```

---

## 二、能力矩阵

### 2.1 我们需要的能力

| 能力 | 描述 | 实现方案 |
|------|------|----------|
| **Blueprint 内省** | 获取蓝图的变量、函数、组件、图表节点 | UE5 Editor HTTP API (ue5-mcp 已有) |
| **Blueprint 继承分析** | 获取蓝图的类层次结构 | UE5 Editor HTTP API (新增) |
| **Blueprint 依赖分析** | 获取蓝图引用的 C++/其他蓝图/资产 | UE5 Editor HTTP API (新增) |
| **C++ 代码分析** | 分析 C++ 类的结构和蓝图暴露 | **unreal-analyzer-mcp** (直接集成) |
| **资产引用查询** | 查询资产的引用和被引用关系 | UE5 AssetRegistry API (新增) |
| **资产搜索** | 按名称/类型搜索资产 | UE5 AssetRegistry API (新增) |

### 2.2 能力来源划分

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      UE5 Project Analyzer MCP                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐    │
│  │    Blueprint Analysis       │    │      C++ Analysis           │    │
│  │    (我们实现)               │    │   (unreal-analyzer-mcp)     │    │
│  │                             │    │                             │    │
│  │  • 继承链分析               │    │  • 类结构分析               │    │
│  │  • 组件依赖                 │    │  • UPROPERTY/UFUNCTION      │    │
│  │  • 图表节点解析             │    │  • 继承层次                 │    │
│  │  • 变量/函数列表            │    │  • 代码搜索                 │    │
│  └─────────────────────────────┘    └─────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐    │
│  │    Asset Analysis           │    │    Cross-Domain Query       │    │
│  │    (我们实现)               │    │    (我们实现)               │    │
│  │                             │    │                             │    │
│  │  • 资产搜索                 │    │  • BP → C++ 引用追踪        │    │
│  │  • 引用关系查询             │    │  • C++ → BP 使用查询        │    │
│  │  • 被引用关系查询           │    │  • 完整引用链构建           │    │
│  │  • 资产元数据               │    │  • GAS 流程追踪             │    │
│  └─────────────────────────────┘    └─────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、系统架构

### 3.1 整体架构

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              AI Agent (Cursor)                                │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │ MCP Protocol
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         MCP Server (Python/FastMCP)                           │
│                              统一入口                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        C++ Source Analyzer                               │ │
│  │                   (从 unreal-analyzer-mcp 迁移)                          │ │
│  │                                                                          │ │
│  │  • tree-sitter C++ 解析     • 类结构/继承分析                            │ │
│  │  • UPROPERTY/UFUNCTION 检测 • 代码搜索                                   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │ HTTP
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        UE5ProjectAnalyzer Plugin                              │
│                            (单一 UE5 插件)                                    │
│  ┌────────────────────────────────┐  ┌─────────────────────────────────────┐ │
│  │     C++ HTTP Server            │  │     Python Bridge (自动拉起)        │ │
│  │     :8080                      │  │     (Unreal Python API)             │ │
│  │                                │  │                                     │ │
│  │  • Blueprint 内省              │  │  • 补充 C++ 无法实现的功能          │ │
│  │  • Asset 引用查询              │  │  • 通过 C++ Server 统一暴露         │ │
│  │  • 类层次分析                  │  │                                     │ │
│  └────────────────────────────────┘  └─────────────────────────────────────┘ │
│                                                                               │
│  启用插件 = 同时启动 C++ Server + Python Bridge                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 架构简化说明

| 组件 | 位置 | 职责 |
|------|------|------|
| **MCP Server** | 外部 Python 进程 | 统一 MCP 入口 + C++ 源码分析 (tree-sitter) |
| **UE5 Plugin** | Editor 内 | Blueprint/Asset 运行时查询 + Python Bridge |

**关键决策**：
- ✅ 将 unreal-analyzer-mcp (TypeScript) 迁移到 Python，自主维护
- ✅ Python Bridge 集成在 C++ 插件中，启用插件自动拉起
- ✅ 全 Python 技术栈，降低维护复杂度

### 3.3 项目结构

```
ue5-project-analyzer/
│
├── README.md
├── pyproject.toml                    # uv 项目配置
│
├── src/ue5_analyzer/                 # MCP Server (外部运行)
│   ├── __init__.py
│   ├── server.py                     # MCP 入口
│   │
│   ├── tools/                        # MCP 工具定义
│   │   ├── blueprint.py              # 蓝图分析工具
│   │   ├── asset.py                  # 资产分析工具
│   │   ├── cpp.py                    # C++ 分析工具
│   │   └── cross_domain.py           # 跨域查询工具
│   │
│   ├── cpp_analyzer/                 # C++ 源码分析 (迁移自 unreal-analyzer-mcp)
│   │   ├── __init__.py
│   │   ├── analyzer.py               # 核心分析器 (tree-sitter)
│   │   ├── patterns.py               # UE 模式检测 (UPROPERTY 等)
│   │   └── queries.py                # tree-sitter 查询定义
│   │
│   ├── ue_client/                    # UE5 插件通信
│   │   ├── __init__.py
│   │   └── http_client.py            # HTTP 客户端
│   │
│   └── config.py
│
├── unreal-plugin/                    # UE5 插件 (Editor 内运行)
│   ├── UE5ProjectAnalyzer.uplugin
│   ├── Source/UE5ProjectAnalyzer/    # C++ 代码
│   │   ├── Public/
│   │   ├── Private/
│   │   │   ├── Module.cpp            # 模块启动，拉起 Python Bridge
│   │   │   ├── HttpServer.cpp        # HTTP API Server
│   │   │   ├── BlueprintAnalyzer.cpp # 蓝图分析
│   │   │   └── AssetAnalyzer.cpp     # 资产引用分析
│   │   └── UE5ProjectAnalyzer.Build.cs
│   │
│   └── Content/Python/               # Python Bridge (随插件分发)
│       └── bridge_server.py          # 被 C++ 自动拉起
│
└── tests/
```

### 3.4 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| MCP 入口 | Python/FastMCP | 统一路由，易于扩展 |
| C++ 分析 | 复用 unreal-analyzer-mcp | 不重复造轮子，作者维护 |
| Blueprint/Asset 查询 | 自研 C++ 插件 | 需要深度访问 Editor API |
| Python Bridge | TCP Server in Editor | Unreal Python 必须在 Editor 内运行 |
| 包管理 | uv | 现代、快速 |

---

## 四、MCP 工具清单

### 4.1 Blueprint 工具组

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `search_blueprints` | name_pattern, class_filter | 蓝图路径列表 | 按名称/类型搜索蓝图 |
| `get_blueprint_hierarchy` | bp_path | 继承链 | 查看蓝图继承结构 |
| `get_blueprint_dependencies` | bp_path | 依赖列表 | 蓝图引用了什么 |
| `get_blueprint_referencers` | bp_path | 引用者列表 | 谁引用了这个蓝图 |
| `get_blueprint_graph` | bp_path, graph_name | 节点列表 | 查看图表逻辑 |
| `get_blueprint_details` | bp_path | 完整信息 | 变量、函数、组件汇总 |

### 4.2 Asset 工具组

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `search_assets` | name_pattern, asset_type | 资产路径列表 | 按名称/类型搜索 |
| `get_asset_references` | asset_path | 引用列表 | 这个资产引用了什么 |
| `get_asset_referencers` | asset_path | 被引用列表 | 谁引用了这个资产 |
| `get_asset_metadata` | asset_path | 元数据 | 资产的基本信息 |

### 4.3 Cross-Domain 工具组

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `trace_reference_chain` | start_asset, max_depth | 引用树 | 追踪完整引用链 |
| `find_cpp_class_usage` | cpp_class_name | 使用位置列表 | 哪些蓝图/资产用了这个 C++ 类 |
| `analyze_gas_ability` | ability_path | 能力分析报告 | 专门分析 GAS Ability |
| `analyze_character_composition` | character_bp | 角色构成报告 | 专门分析角色构成 |

### 4.4 C++ 分析工具组 (内置)

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `analyze_cpp_class` | class_name, source_path | 类结构 | 分析 C++ 类 |
| `get_cpp_class_hierarchy` | class_name | 继承链 | C++ 继承层次 |
| `search_cpp_code` | query, file_pattern | 匹配列表 | 代码搜索 |
| `find_cpp_references` | identifier | 引用列表 | 代码引用查找 |
| `detect_ue_patterns` | file_path | 模式列表 | 检测 UPROPERTY/UFUNCTION |
| `get_cpp_blueprint_exposure` | file_path | 暴露 API | 分析蓝图可见的 C++ API |

---

## 五、UE5 插件需要暴露的 API

### 5.1 Blueprint API

```
GET  /blueprint/search?pattern=xxx&class=xxx
GET  /blueprint/{path}/hierarchy
GET  /blueprint/{path}/dependencies
GET  /blueprint/{path}/referencers
GET  /blueprint/{path}/graph/{graph_name}
GET  /blueprint/{path}/details
```

### 5.2 Asset API

```
GET  /asset/search?pattern=xxx&type=xxx
GET  /asset/{path}/references
GET  /asset/{path}/referencers  
GET  /asset/{path}/metadata
```

### 5.3 Analysis API

```
GET  /analysis/reference-chain?start=xxx&depth=xxx
GET  /analysis/cpp-class-usage?class=xxx
```

---

## 六、Agent 示例对话

### 对话 1: GAS Ability 追踪

```
User: 帮我分析 GA_Hero_Dash 这个能力是怎么触发和执行的

Agent: 
[调用 search_blueprints("GA_Hero_Dash", "GameplayAbility")]
[调用 get_blueprint_details("/Game/Abilities/GA_Hero_Dash")]
[调用 get_blueprint_dependencies("/Game/Abilities/GA_Hero_Dash")]
[调用 get_blueprint_referencers("/Game/Abilities/GA_Hero_Dash")]
[调用 get_blueprint_graph("/Game/Abilities/GA_Hero_Dash", "EventGraph")]

基于分析，GA_Hero_Dash 的完整流程如下：

**触发路径**：
玩家按下 Shift 键 
  → IA_Dash (Input Action) 
  → IC_Default_KBM (Input Config) 
  → ULyraHeroComponent::Input_AbilityInputTagPressed()
  → ULyraAbilitySystemComponent::TryActivateAbility(Ability.Dash)

**能力配置**：
- 所属 AbilitySet: AS_Hero_Shooter
- 激活 Tag: Ability.Dash
- 阻挡 Tag: Ability.Dash (防止重复激活)

**执行逻辑** (EventGraph):
1. ActivateAbility 事件开始
2. 检查 Cooldown (GE_Dash_Cooldown)
3. 消耗资源 (GE_Dash_Cost)  
4. 应用位移 (ApplyRootMotionConstantForce)
5. 播放动画 (AM_Hero_Dash)
6. 播放音效 (S_Dash_Whoosh)
7. EndAbility

**关联资产**：
- GE_Dash_Cooldown: 2秒冷却
- GE_Dash_Cost: 消耗 20 体力
- AM_Hero_Dash: 冲刺动画
- C_DashMotion: 位移曲线
```

### 对话 2: 资产引用追踪

```
User: SK_Mannequin 被哪些地方用到了？

Agent:
[调用 get_asset_referencers("/Game/Characters/Mannequin/SK_Mannequin")]
[调用 trace_reference_chain("/Game/Characters/Mannequin/SK_Mannequin", depth=2)]

SK_Mannequin (骨骼资产) 的引用情况：

**直接引用** (3 个资产):
├─ SKM_Mannequin (Skeletal Mesh) - 使用此骨骼
├─ ABP_Mannequin (Anim Blueprint) - 动画蓝图
└─ Phys_Mannequin (Physics Asset) - 物理资产

**间接引用** (通过 SKM_Mannequin):
├─ B_Hero_ShooterMannequin - 角色蓝图
├─ B_Hero_Default - 角色基类
├─ B_NPC_Enemy_Grunt - NPC 蓝图
└─ ... (共 12 个蓝图)

**动画资产** (使用此骨骼的动画):
├─ AM_Hero_Dash, AM_Hero_Jump, AM_Hero_Death
├─ AS_Locomotion, AS_Combat
└─ ... (共 47 个)

修改此骨骼会影响以上所有资产。
```

---

## 七、C++ 源码分析器 (迁移自 unreal-analyzer-mcp)

### 7.1 迁移说明

原 `unreal-analyzer-mcp` (TypeScript) 已长期未更新，我们将其核心功能迁移到 Python 自主维护。

| TypeScript 依赖 | Python 等价 |
|-----------------|-------------|
| `tree-sitter` | `py-tree-sitter` (官方维护) |
| `tree-sitter-cpp` | 同一个语法包 |
| `glob` | `pathlib` |
| `@modelcontextprotocol/create-server` | `fastmcp` |

### 7.2 核心功能

```python
# src/ue5_analyzer/cpp_analyzer/analyzer.py

class CppAnalyzer:
    """C++ 源码分析器 - 基于 tree-sitter"""
    
    def analyze_class(self, class_name: str) -> ClassInfo:
        """解析 C++ 类结构"""
        ...
    
    def find_class_hierarchy(self, class_name: str) -> ClassHierarchy:
        """获取类继承层次"""
        ...
    
    def find_references(self, identifier: str) -> list[CodeReference]:
        """查找代码引用"""
        ...
    
    def search_code(self, query: str, file_pattern: str) -> list[CodeMatch]:
        """代码搜索"""
        ...
    
    def detect_ue_patterns(self, file_path: str) -> list[PatternMatch]:
        """检测 UPROPERTY/UFUNCTION 等 UE 模式"""
        ...
```

### 7.3 迁移收益

- ✅ 统一 Python 技术栈，降低维护成本
- ✅ 可针对我们的需求定制优化
- ✅ 与 Blueprint/Asset 分析无缝整合
- ✅ 部署时不需要 Node.js 运行时

---

## 八、MVP 范围

### MVP 包含

- [ ] `search_blueprints` - 蓝图搜索
- [ ] `get_blueprint_hierarchy` - 继承链
- [ ] `get_blueprint_dependencies` - 依赖分析
- [ ] `get_asset_referencers` - 被引用查询
- [ ] `trace_reference_chain` - 引用链追踪

### MVP 不包含 (后续迭代)

- 专门的 GAS 分析工具
- 专门的角色构成分析工具
- 依赖图可视化导出
- 批量分析

---

## 九、成功标准

MVP 完成后，Agent 应该能回答：

1. ✅ "GA_Hero_Dash 的触发路径是什么？"
2. ✅ "B_Hero_ShooterMannequin 继承自什么？用了哪些组件？"
3. ✅ "SK_Mannequin 被哪些蓝图使用？"
4. ✅ "ULyraHealthComponent 在哪些蓝图中被用到？"
5. ✅ "从 BP_GameMode 到 GA_Hero_Dash 的引用链是什么？"

---

## 十、开发优先级

```
P0 - 基础设施 (Week 1)
├── 项目骨架 (pyproject.toml, 目录结构)
├── MCP Server 入口 (FastMCP)
├── UE5 C++ 插件框架 (HTTP Server 骨架)
└── 基础通信验证

P1 - C++ 源码分析器 (Week 2)
├── tree-sitter 集成 (py-tree-sitter + tree-sitter-cpp)
├── 从 unreal-analyzer-mcp 迁移核心功能
│   ├── analyze_class
│   ├── find_class_hierarchy
│   └── detect_ue_patterns
└── MCP 工具绑定

P2 - UE5 插件核心 (Week 3)
├── Blueprint 内省 API
│   ├── /blueprint/search
│   ├── /blueprint/{path}/hierarchy
│   └── /blueprint/{path}/dependencies
├── Asset 引用 API
│   ├── /asset/search
│   └── /asset/{path}/referencers
└── Python Bridge 集成 (C++ 启动时拉起)

P3 - 整合验证 (Week 4)
├── 跨域查询工具 (BP ↔ C++ ↔ Asset)
├── Lyra 项目实测
├── 引用链追踪
└── 错误处理 + 文档
```
