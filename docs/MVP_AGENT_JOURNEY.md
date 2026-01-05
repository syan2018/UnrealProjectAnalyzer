# Unreal MCP 最小原型设计：基于 Agent Journey 分析

## 背景与动机

> **核心痛点**：Lyra 示例工程中存在大量 Blueprint ↔ C++ 的交叉引用，人工追踪这些引用链耗时且容易遗漏。我们希望 AI Agent 能够自动化这个分析过程，准确理解项目的每一处实现。

---

## 一、典型 Agent Journey：分析 Lyra 中的角色系统

### 场景设定

用户提问：
> "帮我分析 Lyra 项目中 `B_Hero_ShooterMannequin` 角色的完整实现，包括它引用了哪些 C++ 类，这些 C++ 类又暴露了哪些 API 给蓝图。"

### 1.1 Agent 理想工作流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Agent Journey Map                                   │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: 定位目标蓝图
        │
        ▼
┌───────────────────────────────────────┐
│ 🔍 find_blueprint_by_name             │  ← 需要的工具
│    "B_Hero_ShooterMannequin"          │
│                                       │
│ 返回: /Game/Characters/Heroes/...     │
└───────────────────────────────────────┘
        │
        ▼
Step 2: 获取蓝图的类层次结构
        │
        ▼
┌───────────────────────────────────────┐
│ 📊 get_blueprint_class_hierarchy      │  ← 需要的工具
│                                       │
│ 返回:                                 │
│ B_Hero_ShooterMannequin               │
│   └─ B_Hero_Default (Blueprint)       │
│       └─ ALyraCharacter (C++)         │
│           └─ AModularCharacter (C++)  │
│               └─ ACharacter (C++)     │
│                   └─ APawn (C++)      │
└───────────────────────────────────────┘
        │
        ▼
Step 3: 获取蓝图的直接 C++ 依赖
        │
        ▼
┌───────────────────────────────────────┐
│ 🔗 get_blueprint_cpp_dependencies     │  ← 需要的工具
│                                       │
│ 返回:                                 │
│ • ALyraCharacter (父类)               │
│ • ULyraHealthComponent (组件)         │
│ • ULyraPawnExtensionComponent (组件)  │
│ • ULyraAbilitySystemComponent (组件)  │
│ • UInputAction (变量类型)             │
│ • ULyraInputConfig (变量类型)         │
│ • ... 更多依赖                        │
└───────────────────────────────────────┘
        │
        ▼
Step 4: 分析关键 C++ 类暴露的蓝图 API
        │
        ▼
┌───────────────────────────────────────┐
│ 📖 analyze_cpp_blueprint_exposure     │  ← 需要的工具
│    "ALyraCharacter"                   │
│                                       │
│ 返回:                                 │
│ BlueprintCallable 函数:               │
│ • GetLyraAbilitySystemComponent()     │
│ • GetHealthComponent()                │
│ • ToggleCrouch()                      │
│                                       │
│ BlueprintReadOnly 属性:               │
│ • AbilitySystemComponent              │
│ • HealthComponent                     │
│                                       │
│ BlueprintImplementableEvent:          │
│ • OnDeathStarted                      │
│ • OnDeathFinished                     │
└───────────────────────────────────────┘
        │
        ▼
Step 5: 查看蓝图中的实际使用
        │
        ▼
┌───────────────────────────────────────┐
│ 📋 get_graph                          │  ← 已有工具
│    "EventGraph"                       │
│                                       │
│ 返回: 节点列表，包含对上述 C++ API    │
│       的调用                          │
└───────────────────────────────────────┘
        │
        ▼
Step 6: Agent 综合分析，输出理解报告
        │
        ▼
┌───────────────────────────────────────┐
│ 💡 Agent 输出:                        │
│                                       │
│ "B_Hero_ShooterMannequin 是一个继承   │
│  自 ALyraCharacter 的角色蓝图。       │
│                                       │
│  它通过以下方式与 C++ 交互:           │
│  1. 继承 ALyraCharacter 获得基础能力  │
│  2. 使用 ULyraHealthComponent 管理生命│
│  3. 在 EventGraph 中实现 OnDeathStarted│
│     事件来处理死亡逻辑...             │
│                                       │
│  关键引用链:                          │
│  BP → ALyraCharacter → ACharacter     │
│  BP → ULyraHealthComponent → ...      │
│ "                                     │
└───────────────────────────────────────┘
```

### 1.2 Journey 中的关键决策点

| 步骤 | Agent 需要知道的 | 工具提供的 |
|------|------------------|-----------|
| Step 1 | 蓝图在哪里 | 蓝图路径 |
| Step 2 | 继承了什么 | 完整类层次 + 每层是 BP 还是 C++ |
| Step 3 | 用了什么 C++ | 组件、变量类型、函数调用的 C++ 类 |
| Step 4 | C++ 提供了什么 | UPROPERTY/UFUNCTION 及其蓝图说明符 |
| Step 5 | 蓝图怎么用的 | 节点连接关系 |
| Step 6 | 综合理解 | Agent 自身能力 |

---

## 二、从 Journey 推导最小原型

### 2.1 必要工具清单

根据上述 Journey，**最小原型**需要以下工具：

```
┌─────────────────────────────────────────────────────────────────┐
│                    MVP 工具集 (6 个新工具)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🟢 必须 - 构成完整 Journey                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. find_blueprint_by_name                               │   │
│  │    输入: 蓝图名称（模糊匹配）                            │   │
│  │    输出: 匹配的蓝图路径列表                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 2. get_blueprint_class_hierarchy                        │   │
│  │    输入: 蓝图路径                                        │   │
│  │    输出: 类继承链 + 每层类型标注(BP/Native)              │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 3. get_blueprint_cpp_dependencies                       │   │
│  │    输入: 蓝图路径                                        │   │
│  │    输出: 依赖的 C++ 类列表 + 依赖类型                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 4. analyze_cpp_blueprint_exposure                       │   │
│  │    输入: C++ 头文件路径                                  │   │
│  │    输出: BlueprintCallable/ReadWrite/Event 列表         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🟡 已有 - 直接复用                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 5. get_graph (已有)                                     │   │
│  │ 6. get_blueprint_functions (已有)                       │   │
│  │ 7. get_blueprint_variables (已有)                       │   │
│  │ 8. get_components_of_bp (已有)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 MVP 不需要的功能

| 功能 | 为什么 MVP 不需要 | 何时添加 |
|------|-------------------|----------|
| 项目全局扫描 | 可以按需分析单个蓝图 | v1.1 |
| 依赖图可视化 | Agent 可文字描述 | v1.2 |
| 变更影响分析 | 分析优先，修改其次 | v1.3 |
| 反向查询(C++→BP) | 正向查询先满足需求 | v1.1 |

---

## 三、MVP 实现规格

### 3.1 工具 1: `find_blueprint_by_name`

**目的**：让 Agent 能通过名称快速定位蓝图

```python
@mcp.tool()
def find_blueprint_by_name(name_pattern: str, search_path: str = "/Game/") -> str:
    """通过名称模糊搜索蓝图资产。
    
    参数:
        name_pattern: 蓝图名称或部分名称（支持通配符 *）
        search_path: 搜索起始路径，默认 /Game/
    
    返回示例:
    {
        "matches": [
            {"name": "B_Hero_ShooterMannequin", "path": "/Game/Characters/Heroes/Mannequin/B_Hero_ShooterMannequin"},
            {"name": "B_Hero_Default", "path": "/Game/Characters/Heroes/B_Hero_Default"}
        ],
        "count": 2
    }
    """
```

**UE 插件端实现要点**：
```cpp
// 使用 AssetRegistry 搜索
FAssetRegistryModule& AssetRegistry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
TArray<FAssetData> Assets;
AssetRegistry.Get().GetAssetsByClass(UBlueprint::StaticClass()->GetClassPathName(), Assets);
// 过滤名称匹配的
```

---

### 3.2 工具 2: `get_blueprint_class_hierarchy`

**目的**：让 Agent 理解蓝图的继承结构

```python
@mcp.tool()
def get_blueprint_class_hierarchy(bp_path: str) -> str:
    """获取蓝图的完整类继承链。
    
    返回示例:
    {
        "blueprint": "/Game/Characters/Heroes/Mannequin/B_Hero_ShooterMannequin",
        "hierarchy": [
            {"class": "B_Hero_ShooterMannequin_C", "type": "Blueprint", "path": "/Game/Characters/Heroes/Mannequin/B_Hero_ShooterMannequin"},
            {"class": "B_Hero_Default_C", "type": "Blueprint", "path": "/Game/Characters/Heroes/B_Hero_Default"},
            {"class": "ALyraCharacter", "type": "Native", "module": "/Script/LyraGame"},
            {"class": "AModularCharacter", "type": "Native", "module": "/Script/ModularGameplayActors"},
            {"class": "ACharacter", "type": "Native", "module": "/Script/Engine"},
            {"class": "APawn", "type": "Native", "module": "/Script/Engine"},
            {"class": "AActor", "type": "Native", "module": "/Script/Engine"},
            {"class": "UObject", "type": "Native", "module": "/Script/CoreUObject"}
        ],
        "native_parent": "ALyraCharacter",
        "blueprint_parents": ["B_Hero_Default"]
    }
    """
```

**UE 插件端实现要点**：
```cpp
TArray<FClassInfo> GetClassHierarchy(UBlueprint* Blueprint)
{
    TArray<FClassInfo> Hierarchy;
    UClass* CurrentClass = Blueprint->GeneratedClass;
    
    while (CurrentClass)
    {
        FClassInfo Info;
        Info.ClassName = CurrentClass->GetName();
        Info.bIsNative = !CurrentClass->ClassGeneratedBy; // 没有生成它的蓝图 = 原生类
        
        if (UBlueprint* BP = Cast<UBlueprint>(CurrentClass->ClassGeneratedBy))
        {
            Info.BlueprintPath = BP->GetPathName();
        }
        else
        {
            Info.ModulePath = CurrentClass->GetOuterUPackage()->GetName();
        }
        
        Hierarchy.Add(Info);
        CurrentClass = CurrentClass->GetSuperClass();
    }
    
    return Hierarchy;
}
```

---

### 3.3 工具 3: `get_blueprint_cpp_dependencies`

**目的**：让 Agent 知道蓝图使用了哪些 C++ 类

```python
@mcp.tool()
def get_blueprint_cpp_dependencies(bp_path: str) -> str:
    """获取蓝图引用的所有 C++ 类。
    
    返回示例:
    {
        "blueprint": "/Game/Characters/Heroes/Mannequin/B_Hero_ShooterMannequin",
        "dependencies": [
            {
                "class": "ALyraCharacter",
                "module": "/Script/LyraGame", 
                "type": "ParentClass",
                "source_file": "LyraCharacter.h"  // 如果能获取到
            },
            {
                "class": "ULyraHealthComponent",
                "module": "/Script/LyraGame",
                "type": "Component",
                "source_file": "LyraHealthComponent.h"
            },
            {
                "class": "ULyraAbilitySystemComponent", 
                "module": "/Script/LyraGame",
                "type": "Component",
                "source_file": null
            },
            {
                "class": "UKismetMathLibrary",
                "module": "/Script/Engine",
                "type": "FunctionCall",
                "functions_used": ["RandomFloat", "VSize"]
            },
            {
                "class": "UInputAction",
                "module": "/Script/EnhancedInput",
                "type": "VariableType"
            }
        ],
        "summary": {
            "total_cpp_classes": 12,
            "by_type": {
                "ParentClass": 1,
                "Component": 4,
                "FunctionCall": 3,
                "VariableType": 4
            }
        }
    }
    """
```

**UE 插件端实现要点**：
```cpp
TArray<FCppDependency> GetBlueprintCppDependencies(UBlueprint* Blueprint)
{
    TArray<FCppDependency> Dependencies;
    
    // 1. 父类（第一个原生父类）
    UClass* NativeParent = FindFirstNativeParent(Blueprint->GeneratedClass);
    AddDependency(Dependencies, NativeParent, "ParentClass");
    
    // 2. 组件
    if (Blueprint->SimpleConstructionScript)
    {
        for (USCS_Node* Node : Blueprint->SimpleConstructionScript->GetAllNodes())
        {
            AddDependency(Dependencies, Node->ComponentClass, "Component");
        }
    }
    
    // 3. 遍历所有图表节点
    for (UEdGraph* Graph : Blueprint->UbergraphPages)
    {
        for (UEdGraphNode* Node : Graph->Nodes)
        {
            // 函数调用
            if (UK2Node_CallFunction* CallNode = Cast<UK2Node_CallFunction>(Node))
            {
                if (UFunction* Func = CallNode->GetTargetFunction())
                {
                    AddDependency(Dependencies, Func->GetOuterUClass(), "FunctionCall");
                }
            }
            // 变量类型
            if (UK2Node_Variable* VarNode = Cast<UK2Node_Variable>(Node))
            {
                ExtractVariableTypeDependency(VarNode, Dependencies);
            }
        }
    }
    
    // 4. 变量定义的类型
    for (FBPVariableDescription& Var : Blueprint->NewVariables)
    {
        ExtractPinTypeDependency(Var.VarType, Dependencies);
    }
    
    return DeduplicateDependencies(Dependencies);
}
```

---

### 3.4 工具 4: `analyze_cpp_blueprint_exposure`

**目的**：让 Agent 了解 C++ 类暴露了什么给蓝图

```python
@mcp.tool()
def analyze_cpp_blueprint_exposure(file_path: str) -> str:
    """分析 C++ 头文件中暴露给蓝图的 API。
    
    参数:
        file_path: C++ 头文件的完整路径
    
    返回示例:
    {
        "file": "D:/Unreal/Lyra/Source/LyraGame/Character/LyraCharacter.h",
        "classes": [
            {
                "name": "ALyraCharacter",
                "parent": "AModularCharacter",
                "is_blueprintable": true,
                "blueprint_callable_functions": [
                    {
                        "name": "GetLyraAbilitySystemComponent",
                        "return_type": "ULyraAbilitySystemComponent*",
                        "parameters": [],
                        "category": "Lyra|Character"
                    },
                    {
                        "name": "ToggleCrouch", 
                        "return_type": "void",
                        "parameters": [],
                        "category": "Lyra|Character"
                    }
                ],
                "blueprint_pure_functions": [
                    {
                        "name": "GetHealthComponent",
                        "return_type": "ULyraHealthComponent*",
                        "parameters": []
                    }
                ],
                "blueprint_events": [
                    {
                        "name": "OnDeathStarted",
                        "event_type": "BlueprintImplementableEvent",
                        "parameters": [{"type": "AActor*", "name": "InstigatingActor"}]
                    },
                    {
                        "name": "OnDeathFinished",
                        "event_type": "BlueprintImplementableEvent", 
                        "parameters": [{"type": "AActor*", "name": "InstigatingActor"}]
                    }
                ],
                "blueprint_readable_properties": [
                    {"name": "AbilitySystemComponent", "type": "ULyraAbilitySystemComponent*", "category": "Lyra|Character"},
                    {"name": "HealthComponent", "type": "ULyraHealthComponent*", "category": "Lyra|Character"}
                ],
                "blueprint_writable_properties": []
            }
        ]
    }
    """
```

**Python 实现（tree-sitter）**：

```python
# unreal-mcp/Python/MCP/cpp_analyzer.py

import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path

@dataclass
class BlueprintFunction:
    name: str
    return_type: str
    parameters: List[Dict[str, str]]
    category: Optional[str] = None
    is_pure: bool = False
    is_event: bool = False
    event_type: Optional[str] = None  # BlueprintImplementableEvent, BlueprintNativeEvent

@dataclass
class BlueprintProperty:
    name: str
    type: str
    category: Optional[str] = None
    is_writable: bool = False

@dataclass
class CppClassExposure:
    name: str
    parent: str
    is_blueprintable: bool
    callable_functions: List[BlueprintFunction]
    pure_functions: List[BlueprintFunction]
    events: List[BlueprintFunction]
    readable_properties: List[BlueprintProperty]
    writable_properties: List[BlueprintProperty]


class CppBlueprintExposureAnalyzer:
    """分析 C++ 文件中暴露给蓝图的 API - MVP 版本"""
    
    # 正则模式
    UCLASS_PATTERN = re.compile(
        r'UCLASS\s*\(([^)]*)\)\s*class\s+(?:\w+_API\s+)?(\w+)\s*:\s*public\s+(\w+)',
        re.MULTILINE
    )
    
    UFUNCTION_PATTERN = re.compile(
        r'UFUNCTION\s*\(([^)]*)\)\s*\n?\s*([\w\s\*&<>:]+?)\s+(\w+)\s*\(([^)]*)\)\s*(?:const\s*)?(?:override\s*)?;',
        re.MULTILINE | re.DOTALL
    )
    
    UPROPERTY_PATTERN = re.compile(
        r'UPROPERTY\s*\(([^)]*)\)\s*\n?\s*([\w\s\*<>:,]+?)\s+(\w+)\s*(?:=|;)',
        re.MULTILINE
    )
    
    def analyze_file(self, file_path: str) -> Dict:
        """分析单个 C++ 头文件"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        result = {
            'file': file_path,
            'classes': []
        }
        
        # 找到所有 UCLASS
        for class_match in self.UCLASS_PATTERN.finditer(content):
            specifiers = class_match.group(1)
            class_name = class_match.group(2)
            parent_class = class_match.group(3)
            
            # 提取该类的范围（简化处理：找到下一个 UCLASS 或文件结尾）
            class_start = class_match.end()
            next_class = self.UCLASS_PATTERN.search(content, class_start)
            class_end = next_class.start() if next_class else len(content)
            class_content = content[class_start:class_end]
            
            exposure = self._analyze_class_exposure(
                class_name, parent_class, specifiers, class_content
            )
            result['classes'].append(asdict(exposure))
        
        return result
    
    def _analyze_class_exposure(self, name: str, parent: str, 
                                 specifiers: str, content: str) -> CppClassExposure:
        """分析单个类的蓝图暴露"""
        
        is_blueprintable = 'Blueprintable' in specifiers
        
        callable_funcs = []
        pure_funcs = []
        events = []
        readable_props = []
        writable_props = []
        
        # 分析 UFUNCTION
        for func_match in self.UFUNCTION_PATTERN.finditer(content):
            func_specs = func_match.group(1)
            return_type = func_match.group(2).strip()
            func_name = func_match.group(3)
            params_str = func_match.group(4)
            
            # 解析参数
            params = self._parse_parameters(params_str)
            
            # 提取 Category
            category = self._extract_category(func_specs)
            
            func = BlueprintFunction(
                name=func_name,
                return_type=return_type,
                parameters=params,
                category=category
            )
            
            if 'BlueprintImplementableEvent' in func_specs:
                func.is_event = True
                func.event_type = 'BlueprintImplementableEvent'
                events.append(func)
            elif 'BlueprintNativeEvent' in func_specs:
                func.is_event = True
                func.event_type = 'BlueprintNativeEvent'
                events.append(func)
            elif 'BlueprintPure' in func_specs:
                func.is_pure = True
                pure_funcs.append(func)
            elif 'BlueprintCallable' in func_specs:
                callable_funcs.append(func)
        
        # 分析 UPROPERTY
        for prop_match in self.UPROPERTY_PATTERN.finditer(content):
            prop_specs = prop_match.group(1)
            prop_type = prop_match.group(2).strip()
            prop_name = prop_match.group(3)
            
            # 检查蓝图可见性
            is_readable = any(s in prop_specs for s in [
                'BlueprintReadOnly', 'BlueprintReadWrite', 
                'EditAnywhere', 'VisibleAnywhere'
            ])
            is_writable = 'BlueprintReadWrite' in prop_specs
            
            if is_readable or is_writable:
                prop = BlueprintProperty(
                    name=prop_name,
                    type=prop_type,
                    category=self._extract_category(prop_specs),
                    is_writable=is_writable
                )
                
                if is_writable:
                    writable_props.append(prop)
                else:
                    readable_props.append(prop)
        
        return CppClassExposure(
            name=name,
            parent=parent,
            is_blueprintable=is_blueprintable,
            callable_functions=callable_funcs,
            pure_functions=pure_funcs,
            events=events,
            readable_properties=readable_props,
            writable_properties=writable_props
        )
    
    def _parse_parameters(self, params_str: str) -> List[Dict[str, str]]:
        """解析函数参数"""
        params = []
        if not params_str.strip():
            return params
        
        # 简单分割（不处理嵌套模板）
        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue
            
            # 尝试分离类型和名称
            parts = param.rsplit(' ', 1)
            if len(parts) == 2:
                params.append({
                    'type': parts[0].strip(),
                    'name': parts[1].strip()
                })
            else:
                params.append({
                    'type': param,
                    'name': ''
                })
        
        return params
    
    def _extract_category(self, specifiers: str) -> Optional[str]:
        """提取 Category"""
        match = re.search(r'Category\s*=\s*"([^"]*)"', specifiers)
        return match.group(1) if match else None


# 全局实例
_analyzer = CppBlueprintExposureAnalyzer()

def analyze_cpp_file(file_path: str) -> Dict:
    """供 MCP 工具调用"""
    return _analyzer.analyze_file(file_path)
```

---

## 四、MVP 技术栈

```
┌─────────────────────────────────────────────────────────────────┐
│                         MVP 架构                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐         ┌─────────────────────────────┐   │
│  │  Cursor / AI    │ ◄─MCP─► │  mcp_server.py              │   │
│  │  Agent          │         │  (FastMCP + 新工具)          │   │
│  └─────────────────┘         └──────────────┬──────────────┘   │
│                                             │                   │
│                              ┌──────────────┼──────────────┐   │
│                              │              │              │   │
│                              ▼              ▼              ▼   │
│                      ┌───────────┐  ┌───────────┐  ┌─────────┐ │
│                      │ Unreal HTTP  │  │ cpp_      │  │ 已有    │ │
│                      │ API (新增)│  │ analyzer  │  │ 工具    │ │
│                      │           │  │ (Python)  │  │         │ │
│                      └─────┬─────┘  └─────┬─────┘  └────┬────┘ │
│                            │              │             │      │
│                            ▼              ▼             ▼      │
│                      ┌───────────┐  ┌───────────┐  ┌─────────┐ │
│                      │ Unreal       │  │ C++ 源码  │  │ Unreal     │ │
│                      │ Editor    │  │ 文件系统  │  │ Editor  │ │
│                      │ (运行中)  │  │           │  │         │ │
│                      └───────────┘  └───────────┘  └─────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.1 新增文件清单

```
unreal-mcp/
├── Python/MCP/
│   ├── mcp_server.py          (修改: 添加 4 个新工具)
│   └── cpp_analyzer.py        (新增: C++ 分析器)
│
└── Source/Unreal_MCP/
    ├── API/Route/
    │   └── Analysis.cpp/h     (新增: 3 个 HTTP 端点)
    └── Core/
        └── DependencyAnalyzer.cpp/h  (新增: 依赖分析逻辑)
```

### 4.2 依赖更新

```txt
# requirements.txt 新增
tree-sitter>=0.23.0
tree-sitter-cpp>=0.23.0
```

---

## 五、MVP 验收标准

### 5.1 功能验收

```
测试场景：分析 Lyra 的 B_Hero_ShooterMannequin

✅ 能通过名称找到蓝图
✅ 能获取完整的类继承链（区分 BP/Native）
✅ 能列出所有 C++ 依赖（组件、父类、函数调用）
✅ 能分析 C++ 头文件的蓝图暴露
✅ Agent 能基于以上信息输出有意义的分析报告
```

### 5.2 性能验收

```
单个蓝图分析响应时间 < 2s
C++ 文件分析响应时间 < 1s
```

---

## 六、开发顺序建议

```
Week 1:
├── Day 1-2: cpp_analyzer.py (Python 纯实现，可独立测试)
├── Day 3-4: Unreal 插件 DependencyAnalyzer (C++ 核心逻辑)
└── Day 5:   HTTP 路由绑定

Week 2:
├── Day 1-2: MCP 工具集成 + 测试
├── Day 3:   Lyra 项目实测
└── Day 4-5: Bug 修复 + 文档
```

---

## 七、后续迭代路线

| 版本 | 新增功能 | 解锁的 Agent 能力 |
|------|----------|-------------------|
| **MVP** | 4 个核心工具 | 单蓝图深度分析 |
| v1.1 | 项目全局扫描 | "列出所有继承自 ALyraCharacter 的蓝图" |
| v1.2 | 反向查询 (C++→BP) | "哪些蓝图使用了 ULyraHealthComponent" |
| v1.3 | 引用链追踪 | "追踪从 BP_Player 到 UAbilitySystemComponent 的完整路径" |
| v2.0 | 智能建议 | "这个蓝图应该把 X 逻辑迁移到 C++" |

---

## 附录：Lyra 项目的典型分析需求

以下是你可能会问 Agent 的问题，MVP 应该都能支持：

1. **"B_Hero_ShooterMannequin 继承自什么？"**
   → `get_blueprint_class_hierarchy`

2. **"这个角色蓝图用了哪些 C++ 组件？"**
   → `get_blueprint_cpp_dependencies` (过滤 type=Component)

3. **"ALyraCharacter 提供了哪些可以在蓝图中调用的函数？"**
   → `analyze_cpp_blueprint_exposure`

4. **"EventGraph 里调用了哪些 C++ 函数？"**
   → `get_graph` + `get_blueprint_cpp_dependencies` (过滤 type=FunctionCall)

5. **"OnDeathStarted 事件是在哪里定义的？"**
   → `get_blueprint_class_hierarchy` → 找到 ALyraCharacter → `analyze_cpp_blueprint_exposure`
