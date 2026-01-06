# UnrealProjectAnalyzer 改进记录

## ✅ v0.3.0 - 工具集精简

**设计原则**：最小困惑度，用最少工具达成最完整能力。

### 工具数量

| 版本 | 工具数 | 说明 |
|------|--------|------|
| v0.1.0 | 18 | 原始设计 |
| v0.2.0 | 22 | 新增 unified 但未删除旧工具 |
| v0.3.0 | **9** | 精简：unified + 必要特殊工具 |

### 最终工具清单

**核心工具（4 个）**：
```
search         - 统一搜索（C++/Blueprint/Asset）
get_hierarchy  - 获取继承层次
get_references - 获取引用关系
get_details    - 获取详细信息
```

**特殊工具（5 个）**：
```
get_blueprint_graph       - 蓝图节点图（需要图结构）
detect_ue_patterns        - UE 模式检测
get_cpp_blueprint_exposure - C++ 暴露 API 汇总
trace_reference_chain     - 跨域引用链追踪
find_cpp_class_usage      - C++ 类使用查找
```

### 删除的工具（被 unified 替代）

| 原工具 | 替代方案 |
|--------|----------|
| `search_blueprints` | `search(domain="blueprint")` |
| `search_assets` | `search(domain="asset")` |
| `search_cpp_code` | `search(domain="cpp")` |
| `get_blueprint_hierarchy` | `get_hierarchy(domain="blueprint")` |
| `get_cpp_class_hierarchy` | `get_hierarchy(domain="cpp")` |
| `get_blueprint_dependencies` | `get_references(direction="outgoing")` |
| `get_blueprint_referencers` | `get_references(direction="incoming")` |
| `get_asset_references` | `get_references(direction="outgoing")` |
| `get_asset_referencers` | `get_references(direction="incoming")` |
| `find_cpp_references` | `get_references(domain="cpp")` |
| `get_blueprint_details` | `get_details(domain="blueprint")` |
| `get_asset_metadata` | `get_details(domain="asset")` |
| `analyze_cpp_class` | `get_details(domain="cpp")` |

---

## ✅ v0.2.0 - 三层搜索模型

### scope 参数

所有工具支持 `scope` 参数控制搜索范围：

| 值 | 描述 | 场景 |
|---|------|------|
| `project` | 只搜索项目源码 | 默认，快速搜索 |
| `engine` | 只搜索引擎源码 | 分析 UE 内部实现 |
| `all` | 搜索所有 | 全面分析 |

### 健康检查

新增 `/health` 端点：

```bash
curl http://localhost:8080/health
```

---

## ✅ v0.1.0 - 基础功能

### HTTP 大响应修复

- 异步任务机制避免 socket_send_failure
- 分块拉取 + JSON 重组

### Bug 修复

- UPROPERTY 不再被误判为方法
- 接口检测正确识别 `IXxxInterface`

---

## 📝 更新日志

- **v0.3.0**：工具集精简（22 → 9），删除被 unified 替代的工具
- **v0.2.0**：新增统一工具、三层搜索模型、健康检查
- **v0.1.0**：初始版本
