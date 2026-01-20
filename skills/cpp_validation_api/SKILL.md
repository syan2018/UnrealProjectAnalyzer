---
name: cpp_validation_api
description: CppSkillApiSubsystem 验证原语 - 编译所有蓝图并返回错误/警告摘要
tags: [cpp, validation, compile, api]
---

# CppSkillApiSubsystem - ValidationOps

本 skill 文档描述 `UCppSkillApiSubsystem` 的验证相关原语。

## 入口说明

从 UE Python 中获取子系统：

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## 可用操作

| 方法 | C++ 签名 | Python 返回值 |
|------|----------|---------------|
| `compile_all_blueprints_summary` | `FString CompileAllBlueprintsSummary()` | `str` |

详细接口和示例见 `docs/overview.md`。

## 快速示例

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 编译所有蓝图 - 直接返回字符串摘要
summary = api.compile_all_blueprints_summary()
print(summary)
# 输出示例: "Compiled 42 blueprints. Errors=2, Warnings=5"

# 解析结果
import re
match = re.search(r"Errors=(\d+)", summary)
error_count = int(match.group(1)) if match else 0
has_errors = error_count > 0

RESULT = {
    "summary": summary,
    "has_errors": has_errors,
    "error_count": error_count
}
```

## 注意事项

- 此操作可能需要较长时间（取决于项目中蓝图数量）
- 建议在执行前保存所有修改
- 编译过程中会自动加载所有蓝图资产到内存
