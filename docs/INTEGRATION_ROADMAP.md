# UE5 MCP 与 Unreal Analyzer 整合工程推进文档

## 文档版本
- **版本**: 1.0.0
- **日期**: 2026-01-05
- **作者**: AI Engineering Assistant
- **状态**: 技术调研完成，待实施

---

## 一、项目目标

### 1.1 核心愿景
构建一个统一的 MCP 工具链，使 AI 代理能够：
1. **双向理解** Blueprint ↔ C++ 的引用关系
2. **全局视角** 理解 UE5 项目的完整架构
3. **智能操作** 基于理解进行精准的蓝图/代码修改

### 1.2 解决的核心问题

| 当前痛点 | 目标状态 |
|---------|---------|
| `ue5-mcp` 只能操作蓝图，不知道蓝图引用了哪些 C++ | AI 能获取蓝图的完整 C++ 依赖图 |
| `unreal-analyzer-mcp` 只分析 C++，不知道被哪些蓝图使用 | AI 能反向追溯 C++ 的蓝图使用情况 |
| 两个工具孤立运行，无法形成完整项目理解 | 统一的项目上下文，跨域引用分析 |

---

## 二、技术可行性调研

### 2.1 UE5 Blueprint API 分析

#### 2.1.1 关键 API 支持 ✅

根据 Context7 文档调研，UE5 提供了充足的 API 支持：

| API | 用途 | 头文件 |
|-----|------|--------|
| `UBlueprintEditorLibrary::GeneratedClass()` | 获取蓝图编译后的 UClass | BlueprintEditorLibrary.h |
| `UBlueprintEditorLibrary::GetBlueprintForClass()` | 反向查找蓝图资产 | BlueprintEditorLibrary.h |
| `UBlueprintEditorLibrary::FindEventGraph()` | 获取事件图 | BlueprintEditorLibrary.h |
| `FBlueprintCompileReinstancer::GetSortedClassHierarchy()` | 获取完整类层次 | KismetCompilerModule.h |
| `UBlueprintVariableNodeSpawner::GetVarProperty()` | 获取变量属性信息 | BlueprintVariableNodeSpawner.h |

#### 2.1.2 K2Node 节点信息提取

蓝图节点存储了完整的 C++ 引用信息：

```cpp
// K2Node_VariableGet 示例（来自文档）
VariableReference=(MemberName="Bp_HealthComponent",bSelfContext=True)
PinType.PinSubCategoryObject=BlueprintGeneratedClass'"/Game/Bp_HealthComponent.Bp_HealthComponent_C"'
```

**关键字段：**
- `VariableReference.MemberName` - 变量名
- `FunctionReference` - 函数调用引用
- `PinType.PinSubCategoryObject` - 类型的 C++ 类路径
- `MemberParent` - 所属类

#### 2.1.3 可行性结论

✅ **完全可行** - UE5 Editor API 提供了获取蓝图→C++ 引用的所有必要接口

---

### 2.2 C++ 代码分析方案

#### 2.2.1 tree-sitter Python 绑定 ✅

根据 `py-tree-sitter` 文档，可以实现 C++ 宏解析：

```python
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_cpp

CPP_LANGUAGE = Language(tree_sitter_cpp.language())
parser = Parser(CPP_LANGUAGE)

# 解析 UPROPERTY 宏
query = Query(
    CPP_LANGUAGE,
    """
    (call_expression
      function: (identifier) @macro_name
      (#match? @macro_name "UPROPERTY|UFUNCTION|UCLASS")
      arguments: (argument_list) @specifiers)
    """
)

# 执行查询
query_cursor = QueryCursor(query)
captures = query_cursor.captures(tree.root_node)
```

#### 2.2.2 需要检测的 UE 宏模式

| 宏 | 正则/查询模式 | 用途 |
|----|--------------|------|
| `UPROPERTY(...)` | `UPROPERTY\s*\([^)]*\)` | 检测蓝图可见属性 |
| `UFUNCTION(...)` | `UFUNCTION\s*\([^)]*BlueprintCallable[^)]*\)` | 检测蓝图可调用函数 |
| `UCLASS(Blueprintable)` | `UCLASS\s*\([^)]*Blueprintable[^)]*\)` | 检测可派生蓝图类 |
| `BlueprintImplementableEvent` | 字符串匹配 | 蓝图可实现事件 |
| `BlueprintNativeEvent` | 字符串匹配 | C++/蓝图混合事件 |

#### 2.2.3 可行性结论

✅ **完全可行** - tree-sitter 提供了强大的 C++ 解析和模式匹配能力

---

### 2.3 FastMCP 服务整合

#### 2.3.1 当前架构

```python
# ue5-mcp/Python/MCP/mcp_server.py
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("UE5BlueprintMCP", port=PORT)

@mcp.tool()
def get_blueprint_functions(bp_path: str) -> str:
    """现有工具：获取蓝图函数列表"""
    ...
```

#### 2.3.2 扩展方案

FastMCP 支持：
- ✅ 异步工具定义
- ✅ HTTP Streamable 传输
- ✅ 多工具并行注册
- ✅ 复杂返回类型（JSON）

**无需架构变更**，可直接在现有 `mcp_server.py` 中添加新工具。

---

## 三、系统架构设计

### 3.1 整体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                         AI Agent (Claude/Cursor)                      │
│                              MCP Client                               │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ MCP Protocol (HTTP Streamable)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Unified MCP Server (Python)                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                     Bridge Layer (新增)                         │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │  │
│  │  │ BP→C++ 依赖分析   │  │ C++→BP 暴露分析  │  │ 跨域引用图   │  │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                │                                      │
│  ┌─────────────────────────────┼─────────────────────────────────┐   │
│  │                             │                                  │   │
│  ▼                             ▼                                  ▼   │
│ ┌────────────────┐    ┌────────────────┐    ┌─────────────────────┐  │
│ │ Blueprint Ops  │    │ C++ Analyzer   │    │ Project Context     │  │
│ │ (现有 ue5-mcp) │    │ (tree-sitter)  │    │ Manager (新增)      │  │
│ └───────┬────────┘    └───────┬────────┘    └─────────┬───────────┘  │
│         │                     │                       │              │
└─────────┼─────────────────────┼───────────────────────┼──────────────┘
          │                     │                       │
          ▼                     ▼                       ▼
┌─────────────────┐    ┌────────────────┐    ┌─────────────────────────┐
│  UE5 Editor     │    │ C++ Source     │    │ Project File System     │
│  HTTP API       │    │ Files          │    │ (.uproject, .uasset)    │
│  (C++ Plugin)   │    │ (.h, .cpp)     │    │                         │
└─────────────────┘    └────────────────┘    └─────────────────────────┘
```

### 3.2 数据流设计

```
[用户查询: "分析 BP_Player 的 C++ 依赖"]
            │
            ▼
┌──────────────────────────────────────┐
│  1. 调用 get_blueprint_cpp_deps      │
│     - 请求 UE5 Editor API            │
│     - 解析节点中的 C++ 类引用         │
└──────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────┐
│  2. 获取类层次                        │
│     - 遍历父类直到原生 C++ 类         │
│     - 收集接口实现                    │
└──────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────┐
│  3. 分析 C++ 源码（可选）             │
│     - 使用 tree-sitter 解析          │
│     - 提取 UPROPERTY/UFUNCTION       │
│     - 识别蓝图暴露的 API              │
└──────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────┐
│  4. 构建依赖图返回                    │
│     {                                │
│       "blueprint": "/Game/BP_Player",│
│       "parent_class": "ACharacter",  │
│       "cpp_dependencies": [...],     │
│       "exposed_api": [...]           │
│     }                                │
└──────────────────────────────────────┘
```

---

## 四、实施计划

### 4.1 阶段划分

```
Phase 1 (1-2周)          Phase 2 (2-3周)          Phase 3 (1-2周)
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ UE5 插件扩展    │ ──▶  │ MCP 工具扩展    │ ──▶  │ 整合与优化      │
│ C++ API 实现    │      │ Python 侧实现   │      │ 文档与测试      │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

### 4.2 Phase 1: UE5 Editor 插件扩展

#### 4.2.1 新增 HTTP API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/get_blueprint_cpp_dependencies` | GET | 获取蓝图的 C++ 依赖列表 |
| `/get_blueprint_class_hierarchy` | GET | 获取完整类继承链 |
| `/get_node_cpp_metadata` | GET | 获取节点的 C++ 源信息 |
| `/get_blueprint_exposed_events` | GET | 获取蓝图实现的 C++ 事件 |
| `/analyze_project_blueprints` | GET | 扫描项目所有蓝图 |

#### 4.2.2 C++ 实现文件结构

```
Source/UE5_MCP/
├── API/
│   ├── Route/
│   │   ├── BP.cpp/h              (现有)
│   │   ├── Function.cpp/h        (现有)
│   │   ├── Graph.cpp/h           (现有)
│   │   └── Analysis.cpp/h        (新增) ★
│   └── DTO/
│       └── AnalysisReq.cpp/h     (新增) ★
└── Core/
    └── DependencyAnalyzer.cpp/h  (新增) ★
```

#### 4.2.3 核心实现代码框架

```cpp
// Source/UE5_MCP/Core/DependencyAnalyzer.h
#pragma once

#include "CoreMinimal.h"
#include "Engine/Blueprint.h"

struct FCppDependency
{
    FString ClassName;      // C++ 类名
    FString ModulePath;     // 模块路径 (e.g., /Script/Engine)
    FString SourceFile;     // 源文件路径（如果可获取）
    FString DependencyType; // "ParentClass", "Component", "FunctionCall", "Variable"
};

struct FBlueprintAnalysisResult
{
    FString BlueprintPath;
    FString GeneratedClassName;
    TArray<FString> ClassHierarchy;
    TArray<FCppDependency> CppDependencies;
    TArray<FString> ImplementedInterfaces;
};

class FUECP_DependencyAnalyzer
{
public:
    // 分析单个蓝图的 C++ 依赖
    static FBlueprintAnalysisResult AnalyzeBlueprint(UBlueprint* Blueprint);
    
    // 获取完整类层次（直到原生 C++ 类）
    static TArray<FString> GetClassHierarchy(UClass* Class);
    
    // 从图表节点提取 C++ 引用
    static TArray<FCppDependency> ExtractGraphDependencies(UEdGraph* Graph);
    
    // 获取组件类型依赖
    static TArray<FCppDependency> GetComponentDependencies(UBlueprint* Blueprint);
    
private:
    // 解析 K2Node_CallFunction 获取目标类
    static FCppDependency ParseCallFunctionNode(UK2Node_CallFunction* Node);
    
    // 解析变量节点获取类型引用
    static FCppDependency ParseVariableNode(UK2Node_Variable* Node);
};
```

```cpp
// Source/UE5_MCP/Core/DependencyAnalyzer.cpp
#include "DependencyAnalyzer.h"
#include "K2Node_CallFunction.h"
#include "K2Node_Variable.h"
#include "K2Node_Event.h"
#include "EdGraph/EdGraph.h"
#include "Engine/SimpleConstructionScript.h"

FBlueprintAnalysisResult FUECP_DependencyAnalyzer::AnalyzeBlueprint(UBlueprint* Blueprint)
{
    FBlueprintAnalysisResult Result;
    
    if (!Blueprint) return Result;
    
    Result.BlueprintPath = Blueprint->GetPathName();
    
    // 获取生成的类
    if (UClass* GeneratedClass = Blueprint->GeneratedClass)
    {
        Result.GeneratedClassName = GeneratedClass->GetName();
        Result.ClassHierarchy = GetClassHierarchy(GeneratedClass);
        
        // 收集接口
        for (const FImplementedInterface& Interface : GeneratedClass->Interfaces)
        {
            if (Interface.Class)
            {
                Result.ImplementedInterfaces.Add(Interface.Class->GetPathName());
            }
        }
    }
    
    // 分析所有图表
    for (UEdGraph* Graph : Blueprint->UbergraphPages)
    {
        Result.CppDependencies.Append(ExtractGraphDependencies(Graph));
    }
    
    for (UEdGraph* Graph : Blueprint->FunctionGraphs)
    {
        Result.CppDependencies.Append(ExtractGraphDependencies(Graph));
    }
    
    // 获取组件依赖
    Result.CppDependencies.Append(GetComponentDependencies(Blueprint));
    
    return Result;
}

TArray<FString> FUECP_DependencyAnalyzer::GetClassHierarchy(UClass* Class)
{
    TArray<FString> Hierarchy;
    
    UClass* Current = Class;
    while (Current)
    {
        Hierarchy.Add(Current->GetPathName());
        Current = Current->GetSuperClass();
    }
    
    return Hierarchy;
}

TArray<FCppDependency> FUECP_DependencyAnalyzer::ExtractGraphDependencies(UEdGraph* Graph)
{
    TArray<FCppDependency> Dependencies;
    
    if (!Graph) return Dependencies;
    
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        // 函数调用节点
        if (UK2Node_CallFunction* CallNode = Cast<UK2Node_CallFunction>(Node))
        {
            Dependencies.Add(ParseCallFunctionNode(CallNode));
        }
        // 变量节点
        else if (UK2Node_Variable* VarNode = Cast<UK2Node_Variable>(Node))
        {
            Dependencies.Add(ParseVariableNode(VarNode));
        }
        // 事件节点
        else if (UK2Node_Event* EventNode = Cast<UK2Node_Event>(Node))
        {
            if (UFunction* Function = EventNode->FindEventSignatureFunction())
            {
                FCppDependency Dep;
                Dep.ClassName = Function->GetOuterUClass()->GetName();
                Dep.ModulePath = Function->GetOuterUClass()->GetPathName();
                Dep.DependencyType = TEXT("Event");
                Dependencies.Add(Dep);
            }
        }
    }
    
    return Dependencies;
}

FCppDependency FUECP_DependencyAnalyzer::ParseCallFunctionNode(UK2Node_CallFunction* Node)
{
    FCppDependency Dep;
    
    if (UFunction* Function = Node->GetTargetFunction())
    {
        UClass* OwnerClass = Function->GetOuterUClass();
        Dep.ClassName = OwnerClass->GetName();
        Dep.ModulePath = OwnerClass->GetPathName();
        Dep.DependencyType = TEXT("FunctionCall");
    }
    
    return Dep;
}

FCppDependency FUECP_DependencyAnalyzer::ParseVariableNode(UK2Node_Variable* Node)
{
    FCppDependency Dep;
    
    FProperty* Property = Node->GetPropertyForVariable();
    if (Property)
    {
        // 获取属性类型
        if (FObjectProperty* ObjProp = CastField<FObjectProperty>(Property))
        {
            if (ObjProp->PropertyClass)
            {
                Dep.ClassName = ObjProp->PropertyClass->GetName();
                Dep.ModulePath = ObjProp->PropertyClass->GetPathName();
                Dep.DependencyType = TEXT("Variable");
            }
        }
    }
    
    return Dep;
}

TArray<FCppDependency> FUECP_DependencyAnalyzer::GetComponentDependencies(UBlueprint* Blueprint)
{
    TArray<FCppDependency> Dependencies;
    
    if (Blueprint->SimpleConstructionScript)
    {
        const TArray<USCS_Node*>& Nodes = Blueprint->SimpleConstructionScript->GetAllNodes();
        for (USCS_Node* SCSNode : Nodes)
        {
            if (SCSNode->ComponentClass)
            {
                FCppDependency Dep;
                Dep.ClassName = SCSNode->ComponentClass->GetName();
                Dep.ModulePath = SCSNode->ComponentClass->GetPathName();
                Dep.DependencyType = TEXT("Component");
                Dependencies.Add(Dep);
            }
        }
    }
    
    return Dependencies;
}
```

#### 4.2.4 HTTP 路由实现

```cpp
// Source/UE5_MCP/API/Route/Analysis.cpp
#include "Analysis.h"
#include "Core/DependencyAnalyzer.h"
#include "JsonObjectConverter.h"

void FAnalysisRoute::RegisterRoutes(FHttpRouter& Router)
{
    Router.BindRoute(
        FHttpPath(TEXT("/get_blueprint_cpp_dependencies")),
        EHttpServerRequestVerbs::VERB_GET,
        [](const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
        {
            FString BpPath = Request.QueryParams.FindRef(TEXT("bp_path"));
            
            UBlueprint* Blueprint = LoadObject<UBlueprint>(nullptr, *BpPath);
            if (!Blueprint)
            {
                // 返回错误
                return;
            }
            
            FBlueprintAnalysisResult Result = 
                FUECP_DependencyAnalyzer::AnalyzeBlueprint(Blueprint);
            
            // 转换为 JSON 返回
            TSharedPtr<FJsonObject> JsonResult = MakeShared<FJsonObject>();
            // ... 序列化 Result
            
            OnComplete(/* JSON Response */);
        }
    );
    
    Router.BindRoute(
        FHttpPath(TEXT("/get_blueprint_class_hierarchy")),
        EHttpServerRequestVerbs::VERB_GET,
        // ... 类似实现
    );
}
```

---

### 4.3 Phase 2: MCP Server 工具扩展

#### 4.3.1 新增 Python 工具

```python
# ue5-mcp/Python/MCP/mcp_server.py (扩展)

# ==================== Bridge Layer Tools ====================

@mcp.tool()
def get_blueprint_cpp_dependencies(bp_path: str) -> str:
    """获取蓝图引用的所有 C++ 类、函数和类型。
    
    分析蓝图中的：
    - 父类继承链（直到原生 C++ 类）
    - 组件类型（如 UStaticMeshComponent）
    - 函数调用涉及的 C++ 类（如 UKismetMathLibrary）
    - 变量类型引用的 C++ 类/结构体
    - 实现的 C++ 接口
    
    返回格式:
    {
        "blueprint_path": "/Game/Blueprints/BP_Player",
        "generated_class": "BP_Player_C",
        "class_hierarchy": ["BP_Player_C", "ACharacter", "APawn", "AActor", "UObject"],
        "cpp_dependencies": [
            {"class": "ACharacter", "module": "/Script/Engine", "type": "ParentClass"},
            {"class": "UCharacterMovementComponent", "module": "/Script/Engine", "type": "Component"},
            ...
        ],
        "interfaces": ["/Script/Engine.INavAgentInterface"]
    }
    """
    url = f"{BASE_URL}/get_blueprint_cpp_dependencies"
    params = {"bp_path": bp_path}
    response = httpx.get(url, params=params)
    return response.text


@mcp.tool()
def get_blueprint_class_hierarchy(bp_path: str) -> str:
    """获取蓝图的完整类继承链。
    
    从蓝图类开始，向上遍历直到 UObject，
    标注每一层是蓝图生成类还是原生 C++ 类。
    
    返回格式:
    {
        "hierarchy": [
            {"class": "BP_Player_C", "type": "Blueprint", "path": "/Game/Blueprints/BP_Player"},
            {"class": "ACharacter", "type": "Native", "module": "/Script/Engine"},
            {"class": "APawn", "type": "Native", "module": "/Script/Engine"},
            {"class": "AActor", "type": "Native", "module": "/Script/Engine"},
            {"class": "UObject", "type": "Native", "module": "/Script/CoreUObject"}
        ]
    }
    """
    url = f"{BASE_URL}/get_blueprint_class_hierarchy"
    params = {"bp_path": bp_path}
    response = httpx.get(url, params=params)
    return response.text


@mcp.tool()
def get_node_cpp_source(bp_path: str, graph_name: str, node_id: str) -> str:
    """获取蓝图节点对应的 C++ 源信息。
    
    对于函数调用节点，返回：
    - 目标 C++ 类名
    - 函数签名
    - 所属模块
    
    对于事件节点，返回：
    - 事件定义的 C++ 类
    - 是否为 BlueprintImplementableEvent
    
    可用于在 C++ 源码中定位具体实现。
    """
    url = f"{BASE_URL}/get_node_cpp_source"
    params = {"bp_path": bp_path, "graph_name": graph_name, "node_id": node_id}
    response = httpx.get(url, params=params)
    return response.text


@mcp.tool()
def get_project_blueprint_summary(project_content_path: str) -> str:
    """获取项目中所有蓝图的概要信息。
    
    扫描指定 Content 目录下的所有蓝图资产，返回：
    - 蓝图数量
    - 各蓝图的父类分布
    - C++ 类使用频率统计
    
    用于快速了解项目的蓝图-C++ 架构。
    """
    url = f"{BASE_URL}/get_project_blueprint_summary"
    params = {"content_path": project_content_path}
    response = httpx.get(url, params=params)
    return response.text
```

#### 4.3.2 C++ 分析模块（Python tree-sitter）

```python
# ue5-mcp/Python/MCP/cpp_analyzer.py (新文件)

from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_cpp
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
import re

@dataclass
class UPropertyInfo:
    """UPROPERTY 宏信息"""
    name: str
    type: str
    specifiers: List[str]  # EditAnywhere, BlueprintReadWrite, etc.
    line: int
    is_blueprint_visible: bool
    is_blueprint_writable: bool
    category: Optional[str]

@dataclass 
class UFunctionInfo:
    """UFUNCTION 宏信息"""
    name: str
    return_type: str
    parameters: List[Dict[str, str]]
    specifiers: List[str]
    line: int
    is_blueprint_callable: bool
    is_blueprint_pure: bool
    is_blueprint_event: bool

@dataclass
class UClassInfo:
    """UCLASS 信息"""
    name: str
    parent_class: str
    specifiers: List[str]
    is_blueprintable: bool
    is_blueprint_type: bool
    properties: List[UPropertyInfo]
    functions: List[UFunctionInfo]
    file_path: str


class CppBlueprintAnalyzer:
    """分析 C++ 代码中暴露给蓝图的 API"""
    
    def __init__(self):
        self.language = Language(tree_sitter_cpp.language())
        self.parser = Parser(self.language)
        
        # 预编译查询模式
        self._init_queries()
    
    def _init_queries(self):
        """初始化 tree-sitter 查询"""
        # 类定义查询
        self.class_query = Query(
            self.language,
            """
            (class_specifier
              name: (type_identifier) @class_name
              body: (field_declaration_list) @class_body)
            """
        )
        
        # 函数定义查询  
        self.function_query = Query(
            self.language,
            """
            (function_definition
              declarator: (function_declarator
                declarator: (identifier) @func_name
                parameters: (parameter_list) @params)
              body: (compound_statement) @body)
            """
        )
    
    def analyze_file(self, file_path: str) -> List[UClassInfo]:
        """分析单个 C++ 头文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = self.parser.parse(bytes(content, 'utf-8'))
        
        classes = []
        
        # 提取所有 UCLASS 定义
        uclass_pattern = re.compile(
            r'UCLASS\s*\(([^)]*)\)\s*class\s+\w*\s+(\w+)\s*:\s*public\s+(\w+)',
            re.MULTILINE | re.DOTALL
        )
        
        for match in uclass_pattern.finditer(content):
            specifiers_str = match.group(1)
            class_name = match.group(2)
            parent_class = match.group(3)
            
            specifiers = self._parse_specifiers(specifiers_str)
            
            class_info = UClassInfo(
                name=class_name,
                parent_class=parent_class,
                specifiers=specifiers,
                is_blueprintable='Blueprintable' in specifiers,
                is_blueprint_type='BlueprintType' in specifiers,
                properties=self._extract_properties(content, class_name),
                functions=self._extract_functions(content, class_name),
                file_path=file_path
            )
            classes.append(class_info)
        
        return classes
    
    def _parse_specifiers(self, specifiers_str: str) -> List[str]:
        """解析宏说明符"""
        # 移除嵌套括号内容，简化解析
        cleaned = re.sub(r'\([^)]*\)', '', specifiers_str)
        return [s.strip() for s in cleaned.split(',') if s.strip()]
    
    def _extract_properties(self, content: str, class_name: str) -> List[UPropertyInfo]:
        """提取类中的 UPROPERTY"""
        properties = []
        
        # UPROPERTY 模式
        uprop_pattern = re.compile(
            r'UPROPERTY\s*\(([^)]*)\)\s*\n?\s*(\w+[\w\s\*<>,]*)\s+(\w+)\s*[;=]',
            re.MULTILINE
        )
        
        for match in uprop_pattern.finditer(content):
            specifiers_str = match.group(1)
            prop_type = match.group(2).strip()
            prop_name = match.group(3)
            
            specifiers = self._parse_specifiers(specifiers_str)
            
            # 提取 Category
            category = None
            cat_match = re.search(r'Category\s*=\s*"([^"]*)"', specifiers_str)
            if cat_match:
                category = cat_match.group(1)
            
            prop_info = UPropertyInfo(
                name=prop_name,
                type=prop_type,
                specifiers=specifiers,
                line=content[:match.start()].count('\n') + 1,
                is_blueprint_visible=any(s in specifiers for s in 
                    ['BlueprintReadOnly', 'BlueprintReadWrite', 'EditAnywhere', 'VisibleAnywhere']),
                is_blueprint_writable='BlueprintReadWrite' in specifiers,
                category=category
            )
            properties.append(prop_info)
        
        return properties
    
    def _extract_functions(self, content: str, class_name: str) -> List[UFunctionInfo]:
        """提取类中的 UFUNCTION"""
        functions = []
        
        # UFUNCTION 模式
        ufunc_pattern = re.compile(
            r'UFUNCTION\s*\(([^)]*)\)\s*\n?\s*([\w\s\*&<>]+)\s+(\w+)\s*\(([^)]*)\)',
            re.MULTILINE
        )
        
        for match in ufunc_pattern.finditer(content):
            specifiers_str = match.group(1)
            return_type = match.group(2).strip()
            func_name = match.group(3)
            params_str = match.group(4)
            
            specifiers = self._parse_specifiers(specifiers_str)
            
            # 解析参数
            parameters = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    if param:
                        parts = param.rsplit(' ', 1)
                        if len(parts) == 2:
                            parameters.append({
                                'type': parts[0].strip(),
                                'name': parts[1].strip()
                            })
            
            func_info = UFunctionInfo(
                name=func_name,
                return_type=return_type,
                parameters=parameters,
                specifiers=specifiers,
                line=content[:match.start()].count('\n') + 1,
                is_blueprint_callable='BlueprintCallable' in specifiers,
                is_blueprint_pure='BlueprintPure' in specifiers,
                is_blueprint_event=any(s in specifiers for s in 
                    ['BlueprintImplementableEvent', 'BlueprintNativeEvent'])
            )
            functions.append(func_info)
        
        return functions
    
    def get_blueprint_exposed_api(self, file_path: str) -> Dict:
        """获取文件中暴露给蓝图的所有 API 摘要"""
        classes = self.analyze_file(file_path)
        
        result = {
            'file': file_path,
            'classes': []
        }
        
        for cls in classes:
            class_summary = {
                'name': cls.name,
                'parent': cls.parent_class,
                'blueprintable': cls.is_blueprintable,
                'blueprint_readable_properties': [
                    {'name': p.name, 'type': p.type, 'category': p.category}
                    for p in cls.properties if p.is_blueprint_visible
                ],
                'blueprint_writable_properties': [
                    {'name': p.name, 'type': p.type}
                    for p in cls.properties if p.is_blueprint_writable
                ],
                'blueprint_callable_functions': [
                    {'name': f.name, 'return_type': f.return_type, 'params': f.parameters}
                    for f in cls.functions if f.is_blueprint_callable
                ],
                'blueprint_events': [
                    {'name': f.name, 'params': f.parameters}
                    for f in cls.functions if f.is_blueprint_event
                ]
            }
            result['classes'].append(class_summary)
        
        return result


# 创建全局分析器实例
_cpp_analyzer = None

def get_cpp_analyzer() -> CppBlueprintAnalyzer:
    global _cpp_analyzer
    if _cpp_analyzer is None:
        _cpp_analyzer = CppBlueprintAnalyzer()
    return _cpp_analyzer
```

#### 4.3.3 MCP Server 集成

```python
# ue5-mcp/Python/MCP/mcp_server.py (继续扩展)

from cpp_analyzer import get_cpp_analyzer, CppBlueprintAnalyzer
import json

# ==================== C++ Analysis Tools ====================

@mcp.tool()
def analyze_cpp_blueprint_exposure(file_path: str) -> str:
    """分析 C++ 文件中暴露给蓝图的 API。
    
    解析 .h 文件，提取：
    - UCLASS 定义及 Blueprintable 说明符
    - UPROPERTY 及其 BlueprintReadOnly/BlueprintReadWrite 说明符
    - UFUNCTION 及其 BlueprintCallable/BlueprintPure 说明符
    - BlueprintImplementableEvent/BlueprintNativeEvent 声明
    
    参数:
        file_path: C++ 头文件路径
    
    返回格式:
    {
        "file": "/path/to/MyActor.h",
        "classes": [
            {
                "name": "AMyActor",
                "parent": "AActor",
                "blueprintable": true,
                "blueprint_readable_properties": [...],
                "blueprint_callable_functions": [...],
                "blueprint_events": [...]
            }
        ]
    }
    """
    analyzer = get_cpp_analyzer()
    result = analyzer.get_blueprint_exposed_api(file_path)
    return json.dumps(result, indent=2)


@mcp.tool()
def find_cpp_class_definition(class_name: str, source_paths: str) -> str:
    """在指定目录中查找 C++ 类定义。
    
    搜索给定路径下的所有 .h 文件，找到指定类的定义，
    返回文件路径、继承关系和蓝图暴露信息。
    
    参数:
        class_name: C++ 类名（如 "ACharacter", "UStaticMeshComponent"）
        source_paths: 搜索目录，多个用逗号分隔
    
    返回:
        类定义信息，包括文件位置、父类、蓝图 API
    """
    from pathlib import Path
    
    analyzer = get_cpp_analyzer()
    search_dirs = [p.strip() for p in source_paths.split(',')]
    
    for search_dir in search_dirs:
        for h_file in Path(search_dir).rglob('*.h'):
            try:
                classes = analyzer.analyze_file(str(h_file))
                for cls in classes:
                    if cls.name == class_name:
                        return json.dumps({
                            'found': True,
                            'file': str(h_file),
                            'class_info': {
                                'name': cls.name,
                                'parent': cls.parent_class,
                                'blueprintable': cls.is_blueprintable,
                                'properties_count': len(cls.properties),
                                'functions_count': len(cls.functions),
                                'blueprint_exposed_properties': len([p for p in cls.properties if p.is_blueprint_visible]),
                                'blueprint_callable_functions': len([f for f in cls.functions if f.is_blueprint_callable])
                            }
                        }, indent=2)
            except Exception as e:
                continue
    
    return json.dumps({'found': False, 'searched_dirs': search_dirs}, indent=2)


@mcp.tool()
def analyze_cpp_to_blueprint_usage(cpp_class: str, project_content_path: str) -> str:
    """分析指定 C++ 类在项目蓝图中的使用情况。
    
    结合蓝图依赖分析，反向查找哪些蓝图使用了指定的 C++ 类。
    
    参数:
        cpp_class: C++ 类名
        project_content_path: 项目 Content 目录
    
    返回:
        使用该 C++ 类的蓝图列表及使用方式
    """
    # 调用 UE API 获取项目蓝图列表
    url = f"{BASE_URL}/analyze_cpp_usage_in_blueprints"
    params = {"cpp_class": cpp_class, "content_path": project_content_path}
    response = httpx.get(url, params=params)
    return response.text
```

---

### 4.4 Phase 3: 整合与优化

#### 4.4.1 项目上下文管理器

```python
# ue5-mcp/Python/MCP/project_context.py (新文件)

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from pathlib import Path
import json

@dataclass
class ProjectContext:
    """项目上下文，维护蓝图-C++ 引用关系"""
    
    project_path: str
    content_path: str
    source_path: str
    
    # 缓存
    blueprint_cache: Dict[str, dict] = field(default_factory=dict)
    cpp_class_cache: Dict[str, dict] = field(default_factory=dict)
    
    # 引用图
    bp_to_cpp_refs: Dict[str, Set[str]] = field(default_factory=dict)  # BP -> [C++ classes]
    cpp_to_bp_refs: Dict[str, Set[str]] = field(default_factory=dict)  # C++ class -> [BPs]
    
    def add_blueprint(self, bp_path: str, analysis: dict):
        """添加蓝图分析结果到上下文"""
        self.blueprint_cache[bp_path] = analysis
        
        # 更新引用图
        cpp_deps = set()
        for dep in analysis.get('cpp_dependencies', []):
            cpp_class = dep.get('class', '')
            if cpp_class:
                cpp_deps.add(cpp_class)
                
                # 反向引用
                if cpp_class not in self.cpp_to_bp_refs:
                    self.cpp_to_bp_refs[cpp_class] = set()
                self.cpp_to_bp_refs[cpp_class].add(bp_path)
        
        self.bp_to_cpp_refs[bp_path] = cpp_deps
    
    def get_blueprints_using_cpp(self, cpp_class: str) -> List[str]:
        """获取使用指定 C++ 类的所有蓝图"""
        return list(self.cpp_to_bp_refs.get(cpp_class, set()))
    
    def get_cpp_deps_of_blueprint(self, bp_path: str) -> List[str]:
        """获取蓝图的 C++ 依赖"""
        return list(self.bp_to_cpp_refs.get(bp_path, set()))
    
    def export_dependency_graph(self) -> dict:
        """导出完整的依赖图（用于可视化）"""
        return {
            'nodes': {
                'blueprints': list(self.blueprint_cache.keys()),
                'cpp_classes': list(self.cpp_class_cache.keys())
            },
            'edges': {
                'bp_to_cpp': {k: list(v) for k, v in self.bp_to_cpp_refs.items()},
                'cpp_to_bp': {k: list(v) for k, v in self.cpp_to_bp_refs.items()}
            }
        }


# 全局上下文
_project_context: Optional[ProjectContext] = None

def init_project_context(project_path: str) -> ProjectContext:
    """初始化项目上下文"""
    global _project_context
    
    project_path = Path(project_path)
    _project_context = ProjectContext(
        project_path=str(project_path),
        content_path=str(project_path / 'Content'),
        source_path=str(project_path / 'Source')
    )
    
    return _project_context

def get_project_context() -> Optional[ProjectContext]:
    return _project_context
```

#### 4.4.2 高级分析工具

```python
# ue5-mcp/Python/MCP/mcp_server.py (高级工具)

from project_context import init_project_context, get_project_context

@mcp.tool()
def initialize_project_analysis(project_path: str) -> str:
    """初始化项目分析上下文。
    
    扫描项目，建立蓝图和 C++ 的索引，
    构建双向引用图以支持后续的快速查询。
    
    这是使用高级分析功能前的必要步骤。
    
    参数:
        project_path: UE5 项目根目录（包含 .uproject 文件）
    """
    ctx = init_project_context(project_path)
    
    # 扫描所有蓝图
    # ... 调用 UE API 获取蓝图列表并分析
    
    return json.dumps({
        'status': 'initialized',
        'project_path': project_path,
        'content_path': ctx.content_path,
        'source_path': ctx.source_path
    }, indent=2)


@mcp.tool()
def get_project_dependency_graph() -> str:
    """获取项目的完整 Blueprint-C++ 依赖图。
    
    返回所有蓝图和 C++ 类之间的引用关系，
    可用于：
    - 项目架构可视化
    - 影响分析（修改 C++ 会影响哪些蓝图）
    - 依赖统计
    
    需要先调用 initialize_project_analysis。
    """
    ctx = get_project_context()
    if not ctx:
        return json.dumps({'error': 'Project not initialized. Call initialize_project_analysis first.'})
    
    return json.dumps(ctx.export_dependency_graph(), indent=2)


@mcp.tool()
def analyze_impact_of_cpp_change(cpp_class: str, change_type: str) -> str:
    """分析修改 C++ 类对蓝图的影响。
    
    评估对指定 C++ 类的修改会影响哪些蓝图，
    帮助在修改前了解潜在风险。
    
    参数:
        cpp_class: C++ 类名
        change_type: 修改类型 ("add_property", "remove_property", "change_function", "change_parent")
    
    返回:
        受影响的蓝图列表及影响程度评估
    """
    ctx = get_project_context()
    if not ctx:
        return json.dumps({'error': 'Project not initialized'})
    
    affected_bps = ctx.get_blueprints_using_cpp(cpp_class)
    
    impact_analysis = {
        'cpp_class': cpp_class,
        'change_type': change_type,
        'affected_blueprints': affected_bps,
        'affected_count': len(affected_bps),
        'risk_level': 'high' if len(affected_bps) > 10 else 'medium' if len(affected_bps) > 3 else 'low',
        'recommendation': ''
    }
    
    if change_type == 'remove_property':
        impact_analysis['recommendation'] = '建议先检查受影响蓝图中是否使用了该属性'
    elif change_type == 'change_function':
        impact_analysis['recommendation'] = '建议使用 UFUNCTION 的 DeprecatedFunction 说明符进行过渡'
    
    return json.dumps(impact_analysis, indent=2)
```

---

## 五、依赖与环境

### 5.1 Python 依赖

```txt
# requirements.txt (更新)
mcp>=0.9.0
httpx>=0.24.0
python-dotenv>=1.0.0
tree-sitter>=0.23.0
tree-sitter-cpp>=0.23.0
```

### 5.2 UE5 插件依赖

```cs
// UE5_MCP.Build.cs (更新)
PublicDependencyModuleNames.AddRange(new string[] {
    "Core",
    "CoreUObject",
    "Engine",
    "HTTP",
    "HTTPServer",
    "Json",
    "JsonUtilities",
    "UnrealEd",        // 编辑器 API
    "BlueprintGraph",  // 蓝图图表 API (新增)
    "Kismet",          // K2Node API (新增)
    "KismetCompiler"   // 编译器工具 (新增)
});
```

---

## 六、API 规范

### 6.1 新增 HTTP API 端点

| 端点 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/get_blueprint_cpp_dependencies` | GET | `bp_path` | JSON: 依赖列表 |
| `/get_blueprint_class_hierarchy` | GET | `bp_path` | JSON: 类层次 |
| `/get_node_cpp_source` | GET | `bp_path`, `graph_name`, `node_id` | JSON: C++ 源信息 |
| `/get_project_blueprint_summary` | GET | `content_path` | JSON: 项目摘要 |
| `/analyze_cpp_usage_in_blueprints` | GET | `cpp_class`, `content_path` | JSON: 使用分析 |

### 6.2 MCP 工具清单

| 工具名 | 类型 | 描述 |
|--------|------|------|
| `get_blueprint_cpp_dependencies` | Bridge | 获取蓝图的 C++ 依赖 |
| `get_blueprint_class_hierarchy` | Bridge | 获取蓝图类层次 |
| `get_node_cpp_source` | Bridge | 获取节点 C++ 来源 |
| `get_project_blueprint_summary` | Bridge | 项目蓝图摘要 |
| `analyze_cpp_blueprint_exposure` | C++ Analysis | 分析 C++ 蓝图暴露 |
| `find_cpp_class_definition` | C++ Analysis | 查找 C++ 类定义 |
| `analyze_cpp_to_blueprint_usage` | Cross-domain | C++ 到蓝图的反向查询 |
| `initialize_project_analysis` | Context | 初始化项目上下文 |
| `get_project_dependency_graph` | Context | 获取依赖图 |
| `analyze_impact_of_cpp_change` | Context | 变更影响分析 |

---

## 七、测试计划

### 7.1 单元测试

```python
# tests/test_cpp_analyzer.py
import pytest
from cpp_analyzer import CppBlueprintAnalyzer

def test_parse_uproperty():
    analyzer = CppBlueprintAnalyzer()
    # 测试 UPROPERTY 解析
    ...

def test_parse_ufunction():
    analyzer = CppBlueprintAnalyzer()
    # 测试 UFUNCTION 解析
    ...

def test_blueprint_exposure_detection():
    analyzer = CppBlueprintAnalyzer()
    # 测试蓝图暴露检测
    ...
```

### 7.2 集成测试

```python
# tests/test_integration.py
import pytest

def test_blueprint_cpp_dependency_flow():
    """测试完整的蓝图->C++依赖分析流程"""
    # 1. 创建测试蓝图
    # 2. 调用 get_blueprint_cpp_dependencies
    # 3. 验证返回的依赖列表
    ...

def test_cpp_to_blueprint_reverse_lookup():
    """测试 C++ 到蓝图的反向查询"""
    ...
```

### 7.3 端到端测试

```
测试场景：分析 ThirdPerson 模板项目
1. 初始化项目分析
2. 获取 BP_ThirdPersonCharacter 的 C++ 依赖
3. 验证能正确识别 ACharacter 父类
4. 验证能识别 UCharacterMovementComponent 组件
5. 反向查询 ACharacter 在项目中的使用情况
```

---

## 八、风险与缓解

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|------|--------|----------|
| tree-sitter C++ 解析不完整 | 中 | 中 | 结合正则表达式作为补充 |
| UE5 版本 API 差异 | 高 | 低 | 条件编译 + 版本检测 |
| 大型项目性能问题 | 中 | 中 | 增量分析 + 缓存机制 |
| 蓝图编译状态影响 | 中 | 中 | 检测编译状态，必要时先编译 |

---

## 九、里程碑

| 阶段 | 时间 | 交付物 | 验收标准 |
|------|------|--------|----------|
| Phase 1 | Week 1-2 | UE5 插件扩展 | 新 API 端点可调用 |
| Phase 2 | Week 3-4 | MCP 工具扩展 | 工具在 Cursor 中可用 |
| Phase 3 | Week 5-6 | 整合优化 | 端到端测试通过 |

---

## 十、后续演进

### 10.1 短期（v1.1）
- [ ] 支持 Widget Blueprint 分析
- [ ] 支持 Animation Blueprint 分析
- [ ] 增加依赖图可视化导出

### 10.2 中期（v1.5）
- [ ] 智能代码补全建议
- [ ] C++ 最佳实践检查
- [ ] 蓝图到 C++ 迁移辅助

### 10.3 长期（v2.0）
- [ ] 多项目协作支持
- [ ] 版本对比分析
- [ ] AI 驱动的架构优化建议

---

## 附录

### A. 参考文档

1. [Unreal Engine C++ API Reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/API)
2. [Guide to Unreal Engine](https://github.com/mrrobinofficial/guide-unrealengine)
3. [tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
4. [py-tree-sitter](https://github.com/tree-sitter/py-tree-sitter)
5. [FastMCP Documentation](https://gofastmcp.com)

### B. 相关代码库

- ue5-mcp: `ue5-mcp/`
- unreal-analyzer-mcp: `unreal-analyzer-mcp/`

### C. 术语表

| 术语 | 定义 |
|------|------|
| K2Node | 蓝图可视化脚本节点的基类 |
| UPROPERTY | UE 属性反射宏 |
| UFUNCTION | UE 函数反射宏 |
| BlueprintCallable | 可从蓝图调用的函数说明符 |
| BlueprintReadWrite | 蓝图可读写的属性说明符 |
| UBlueprintGeneratedClass | 蓝图编译后生成的运行时类 |
