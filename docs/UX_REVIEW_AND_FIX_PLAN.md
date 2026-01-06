## UnrealProjectAnalyzer 体验复盘 & 修复计划（Lyra 伤害链路）- 进度看板

本文件用于监控：在真实使用 UnrealProjectAnalyzer 追踪 Lyra 伤害链路（Input → Ability → GE → Apply → AttributeSet → HealthComponent → Death）时暴露的体验问题，以及本轮修复进度与验收标准。

### 本轮范围（目标）

- **工具集原则**：最小困惑度（最少暴露工具，最大能力覆盖；当前工具数已精简为 9）
- **优化重点**：日常排查路径：`search` → `get_details` → `get_references`/`trace_reference_chain`
- **完成标准**：用户能稳定找到 Lyra 伤害链条的 Blueprint/Asset/C++ 入口，并能得到明确的提示与错误建议（不靠“猜”）

---

### 当前暴露工具集（9 个）

- **核心工具（4）**：`search`, `get_hierarchy`, `get_references`, `get_details`
- **特殊工具（5）**：`get_blueprint_graph`, `detect_ue_patterns`, `get_cpp_blueprint_exposure`, `trace_reference_chain`, `find_cpp_class_usage`

---

## 需求复盘（含伪需求清理）

标记说明：**[P0]** 必修，**[P1]** 重要，**[P2]** 锦上添花。

“伪需求”定义：由于未了解工具契约/输入规则而提出的方案性需求（通常可以通过调整提示/参数语义或用现有工具实现），这类会**删掉或降级为文档/提示**，不新增工具。

### 1) Blueprint/Asset 多词搜索返回空 **[P0]** ✅ 已修复

- **问题**：UE 侧搜索本质是“按名称通配符”，多词字符串（含空格）极易 0 命中。
- **修复**：
  - 对 Blueprint/Asset 的 `query` 做空格分词，逐 token 搜索后合并去重
  - 增加 `relevance_score`（按命中 token 数）排序
  - 空结果时返回可执行的示例（`GA_*`/`*Weapon*`/`*Fire*`）
- **验收**：
  - `search(query="GA Weapon Fire", domains=["blueprint"])` 返回结果且带 `relevance_score`
  - 空结果时 tips 包含明确示例与建议 pattern
- **状态**：DONE（对应 `Mcp/src/unreal_analyzer/tools/unified.py`）

### 2) `get_details` 不支持 C++ 文件路径 **[P0]** ✅ 已修复

- **问题**：用户传 `.h/.cpp` 时被当成 class name，报 “Class not found”。
- **修复**：
  - `domain="cpp"` 下识别文件路径，走文件分析：`includes/classes/functions/ue_patterns/preview`
  - 失败时返回结构化建议（而不是裸报错）
- **验收**：
  - `get_details(path=".../LyraHealthComponent.h", domain="cpp")` 返回 `type="cpp_file"`
- **状态**：DONE（`cpp_analyzer.analyze_file` + `unified.get_details`）

### 3) scope 语义不直观（project vs plugin）**[P0]** ✅ 已修复（不新增 scope 值）

- **问题**：用户以为 `project` = “整个 UE 项目”，但实际是 `CPP_SOURCE_PATH` 被配置成插件目录导致只搜插件。
- **修复（删掉伪需求：不新增 plugin/project/engine/all 四层 scope）**：
  - 增加 **自动探测 `<Project>/Source`**（当 `CPP_SOURCE_PATH` 未设置时）
  - `search` 返回 `config_summary`，并在疑似插件目录时给 `warnings`
  - 增加可关闭开关：`ANALYZER_AUTO_DETECT_PROJECT_SOURCE=false`（测试/特殊场景）
- **验收**：
  - 手动从插件目录启动也能默认搜到 `<Project>/Source`
  - 用户看到 `config_summary` 可直接确认实际搜索路径
- **状态**：DONE（`config.py` + `unified.search`）

### 4) `find_cpp_class_usage` 返回空 **[P0]** ✅ 已修复（合并 C++ 引用）

- **问题**：UE 端实现偏 MVP，只查 Blueprint 父类链；C++ 使用完全缺失。
- **修复**：
  - 保留 UE 端结果，同时追加 tree-sitter 的 C++ references（支持 `scope`）
  - 新增参数：`scope/include_cpp/max_cpp_results`
- **验收**：
  - `find_cpp_class_usage("LyraHealthSet")` 返回 `cpp_references`
- **状态**：DONE（`Mcp/src/unreal_analyzer/tools/cross_domain.py`）

### 5) 反向追踪：谁引用了某个资产/名字/Tag **[P1]**（保留，但不新增工具）

- **定位**：不是伪需求，但“新增一个 find_asset_references 工具”是伪方案；应在现有 `get_references` 增强一个参数即可。
- **计划**：
  - `get_references(..., include_cpp=True)`：在 `incoming` 结果里追加 `referenced_by_cpp`
- **状态**：TODO

### 6) 结果更结构化（class/function 上下文）**[P1]**

- **Fix**:
  - Enrich C++ matches with lightweight `enclosing_class` / `enclosing_function` (best-effort).
  - Add `relevance_score` and stable sorting.
- **Status**: TODO

### 7) 链路追踪可视化（mermaid）**[P2]**（先降级为文档/Agent 输出）

- **定位**：偏锦上添花。工具层面实现成本高且容易绑死格式；更适合由 Agent 用现有结果生成 mermaid。
- **计划**：先在 README 的“常见任务指南”给出 mermaid 模板与生成规则（工具暂不做）。
- **Status**: TODO

### 8) Better filtering when results are too many **[P1]**

- **Fix**:
  - Keep `max_results`, but add scoring, and add `filters` hints (by class/function).
- **Status**: TODO

### 9) 文档与端到端示例不足 **[P1]**

- **Fix**:
  - Add "Common Tasks" section in README (damage chain recipes).
- **Status**: TODO

### 10) 错误提示不够友好 **[P0]**（部分已做，继续补齐）

- **Fix**:
  - Normalize error shape: `error_code`, `details`, `suggestions`, `examples`.
  - Special-case the common mistake: passing a file path to a class-name API.
- **Status**: TODO

---

## 执行顺序（P0 优先）

1. ✅ Blueprint/Asset 多词搜索 + tips 示例
2. ✅ `get_details` 支持 C++ 文件路径
3. ✅ 自动探测 `<Project>/Source` + `config_summary` + warnings
4. ✅ `find_cpp_class_usage` 合并 C++ 引用
5. 🚧 错误提示统一（error_code/suggestions/examples）+ 反向引用增强 + README 任务指南

