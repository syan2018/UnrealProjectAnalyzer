# Blueprint 增删改能力实施规划（UnrealCopilot）

## 1. 背景与目标

当前 `UnrealCopilot` 已具备：

- 蓝图创建/编译/保存
- CDO 属性写入
- 组件增删

但尚不具备完整的“图节点级编辑”（如 EventGraph 节点增删改、连线重写、函数图重构）。  
本规划用于定义一个可落地、可回滚、可验证的蓝图写入体系，支持 AI 通过 MCP 安全执行蓝图增删改。

核心目标：

1. 统一写入口：所有写操作通过 C++ 子系统执行。
2. 可恢复：每次操作可撤销，失败可回滚。
3. 可验证：写后自动编译与一致性检查。
4. 可编排：上层 MCP/Skill 只做任务编排，不直接操作底层图 API。

## 2. 范围定义

### 2.1 In Scope（本期）

1. 蓝图资产级操作：创建、重命名、复制、删除、保存、编译。
2. 蓝图结构级操作：变量、函数图、宏图、组件树的增删改。
3. 蓝图节点级最小操作：新增节点、删除节点、连线、断线、设置引脚默认值。
4. 批处理事务：一组操作原子执行（全部成功或整体失败回滚）。
5. 校验与诊断：编译结果、错误摘要、警告摘要、操作报告。

### 2.2 Out of Scope（本期不做）

1. 可视化编辑器 UI（拖拽式图编辑前端）。
2. 跨引擎版本自动适配所有差异（先锁定 UE 5.3+）。
3. 全自动语义重构（例如“智能重写逻辑”不要求一次到位）。

## 3. 总体方案（推荐）

采用“**C++ 命令式蓝图写服务 + MCP 编排层**”两层架构：

1. C++ 层（唯一写入口）
   - 新增 `BlueprintWriteService`（内部服务类）封装底层 API。
   - 由 `UCppSkillApiSubsystem` 暴露稳定 `UFUNCTION(BlueprintCallable)`。
2. Python/MCP 层（编排层）
   - 将高层任务拆为命令序列，调用 `run_unreal_skill` 或技能脚本。
   - 不直接触达 `UEdGraph` 细节，避免不稳定行为。

设计原则：

1. 强约束执行上下文（Editor + GameThread）。
2. 命令显式参数化（路径、GraphName、NodeGuid、PinName）。
3. 结果结构化（`ok/error/warnings/affected_assets`）。

## 4. 分层能力模型

### 4.1 L0：资产级（已有 + 补齐）

- `CreateBlueprint`
- `RenameAsset` / `DuplicateAsset` / `DeleteAsset`
- `CompileBlueprint` / `SaveBlueprint`

### 4.2 L1：结构级（优先实现）

- 变量：`AddVariable` / `RemoveVariable` / `RenameVariable` / `SetVariableDefault`
- 图：`AddFunctionGraph` / `RemoveGraph` / `RenameGraph`
- 组件：`AddBlueprintComponent` / `RemoveBlueprintComponent` / `SetComponentProperty`

### 4.3 L2：节点级（第二阶段）

- `AddNode`（按节点类型与模板创建）
- `RemoveNode`
- `ConnectPins` / `BreakLink`
- `SetPinDefaultValue`
- `MoveNode`（坐标布局）

### 4.4 L3：批处理与事务（并行推进）

- `ExecuteBlueprintCommands(BlueprintPath, CommandsJson, bAutoCompile, bAutoSave)`
- 单事务包裹 + 失败回滚
- 输出详细执行报告

## 5. API 设计草案（CppSkillApiSubsystem）

建议新增 BlueprintOps 接口：

1. `bool AddBlueprintVariable(BlueprintPath, VariableName, VariableType, DefaultValue, OutError)`
2. `bool RemoveBlueprintVariable(BlueprintPath, VariableName, OutError)`
3. `bool AddBlueprintGraph(BlueprintPath, GraphName, GraphType, OutError)`
4. `bool RemoveBlueprintGraph(BlueprintPath, GraphName, OutError)`
5. `bool AddBlueprintNode(BlueprintPath, GraphName, NodeClassPath, NodePosX, NodePosY, OutNodeGuid, OutError)`
6. `bool RemoveBlueprintNode(BlueprintPath, GraphName, NodeGuid, OutError)`
7. `bool ConnectBlueprintPins(BlueprintPath, GraphName, FromNodeGuid, FromPinName, ToNodeGuid, ToPinName, OutError)`
8. `bool SetBlueprintPinDefault(BlueprintPath, GraphName, NodeGuid, PinName, ValueAsString, OutError)`
9. `FString ExecuteBlueprintCommands(BlueprintPath, CommandsJson, bAutoCompile, bAutoSave)`

返回约定：

1. 简单接口返回 `(bool success, FString OutError)`。
2. 批处理返回 JSON 字符串，包含执行明细、失败点、回滚状态、编译摘要。

## 6. 事务、回滚与一致性

每个写操作必须遵守：

1. `FScopedTransaction` 包裹。
2. `Modify()` 标记受影响对象。
3. 图结构改动后调用结构修改标记（如 `FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified`）。
4. 可选自动编译；编译失败视为操作失败并触发回滚。
5. 可选自动保存；保存失败返回明确错误，不吞异常。

批处理策略：

1. 默认“全有或全无”（Atomic）。
2. 提供可选 `best_effort`（仅用于低风险批量任务，默认关闭）。

## 7. MCP/Skill 对接方案

在现有 `run_unreal_skill` 基础上新增标准技能包：

- `skills/cpp_blueprint_write_api/`
  - `SKILL.md`：参数规范与示例
  - `scripts/`
    - `create_blueprint_with_components.py`
    - `patch_graph_nodes.py`
    - `batch_refactor_blueprints.py`

Skill 脚本职责：

1. 参数校验与预检查（资产是否存在、图名是否存在）。
2. 调用 `unreal.CppSkillApiSubsystem` 的稳定接口。
3. 输出统一 JSON 报告供 MCP 返回。

## 8. 安全与风控

### 8.1 执行保护

1. 禁止运行时（PIE）执行破坏性写操作。
2. 可选白名单路径（仅允许 `/Game/...` 指定目录）。
3. 批量操作前可选 dry-run（只生成计划不落地）。

### 8.2 审计

1. 每次操作生成 `operation_id`。
2. 记录：输入参数摘要、变更对象、编译结果、耗时、错误信息。
3. 支持将最近 N 次写操作导出为报告。

## 9. 测试策略

### 9.1 自动化测试（优先）

1. C++ Editor 自动化测试：
   - 资产创建/删除回归
   - 变量增删改
   - 图增删改
   - 节点连线校验
2. Python 集成测试：
   - `run_unreal_skill` 调用链完整性
   - 批处理返回 JSON 结构校验

### 9.2 回归样例库

建立 `Content/Tests/BlueprintWriteSamples/`：

1. 简单 Actor 蓝图
2. 含组件层级蓝图
3. 含函数图/宏图蓝图
4. 故障样例（非法路径、非法节点、编译错误）

## 10. 里程碑与排期（建议 4 周）

1. 第 1 周：L1 结构级 API + 基础测试。
2. 第 2 周：L2 节点级最小集（Add/Remove/Connect/SetDefault）。
3. 第 3 周：批处理事务与回滚、统一报告模型。
4. 第 4 周：Skill 脚本封装、端到端回归、文档完善。

## 11. 验收标准（Definition of Done）

同时满足以下条件才算完成：

1. 能通过 MCP 创建蓝图并完成变量/组件/图/节点的增删改。
2. 任意失败场景不产生半完成状态（可回滚）。
3. 写后编译成功率达到预期；失败可给出定位信息（图/节点/引脚）。
4. 所有关键接口具备自动化测试与最小示例脚本。
5. 文档覆盖：API、示例、错误码、限制条件。

## 12. 已知风险与应对

1. UE 版本差异导致节点 API 行为变化  
   - 应对：先锁 UE 5.3+，封装版本差异层。
2. 大批量改图耗时高  
   - 应对：分批执行 + 进度日志 + 超时控制。
3. AI 指令不稳定导致非法输入  
   - 应对：严格参数校验 + dry-run + 白名单策略。

## 13. 对现有代码的最小改动建议

1. 在 `Source/UnrealCopilot/Private/Skill/` 新增：
   - `BlueprintWriteService.h/.cpp`（内部逻辑）
   - `CppSkillApiSubsystem.BlueprintGraph.cpp`（节点级接口实现）
2. 在 `Source/UnrealCopilot/Public/Skill/CppSkillApiSubsystem.h` 增补 BlueprintOps 接口声明。
3. 在 `skills/` 新增 `cpp_blueprint_write_api` 技能包及示例脚本。
4. 在 `README.md` 与 `README_CN.md` 添加本规划文档入口。

## 14. 实施顺序（执行清单）

1. 锁定接口签名与错误码约定。
2. 实现 L1（结构级）并补测试。
3. 实现 L2（节点级最小集）并补测试。
4. 实现批处理事务与回滚。
5. 新增技能包脚本与端到端样例。
6. 压测与回归，发布 v0.5.0（建议版本）。

