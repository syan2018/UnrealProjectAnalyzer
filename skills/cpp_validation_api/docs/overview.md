# CppSkillApiSubsystem - Validation Operations

## 获取子系统

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## API 参考

### compile_all_blueprints_summary

编译项目中所有蓝图并返回摘要。

**C++ 签名**:
```cpp
FString CompileAllBlueprintsSummary();
```

**Python 调用**:
```python
summary = api.compile_all_blueprints_summary()
```

**返回**：`str` - 编译结果摘要

**返回格式示例**:
```
Compiled 42 blueprints. Errors=2, Warnings=5
```

**注意**：此函数没有 `OutError` 参数，直接返回字符串。

---

## 完整示例

### 编译并检查所有蓝图

```python
import unreal
import re

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 编译所有蓝图
summary = api.compile_all_blueprints_summary()
print(summary)

# 解析结果
total_match = re.search(r"Compiled (\d+) blueprints", summary)
error_match = re.search(r"Errors=(\d+)", summary)
warning_match = re.search(r"Warnings=(\d+)", summary)

total_count = int(total_match.group(1)) if total_match else 0
error_count = int(error_match.group(1)) if error_match else 0
warning_count = int(warning_match.group(1)) if warning_match else 0

RESULT = {
    "summary": summary,
    "total_blueprints": total_count,
    "error_count": error_count,
    "warning_count": warning_count,
    "has_errors": error_count > 0,
    "has_warnings": warning_count > 0
}
```

### 编译前保存所有修改

```python
import unreal
import re

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 1. 先保存所有未保存的包
dirty = api.list_dirty_packages()
if dirty:
    success, error = api.save_dirty_packages(prompt_user=False)
    if not success:
        RESULT = {"error": f"保存失败: {error}"}
        raise Exception(error)

# 2. 编译所有蓝图
summary = api.compile_all_blueprints_summary()

# 3. 解析结果
error_match = re.search(r"Errors=(\d+)", summary)
error_count = int(error_match.group(1)) if error_match else 0

RESULT = {
    "saved_packages": len(dirty),
    "summary": summary,
    "has_errors": error_count > 0
}
```

### 定期验证脚本

```python
import unreal
import re
from datetime import datetime

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 执行验证
summary = api.compile_all_blueprints_summary()

# 解析
error_match = re.search(r"Errors=(\d+)", summary)
warning_match = re.search(r"Warnings=(\d+)", summary)
error_count = int(error_match.group(1)) if error_match else 0
warning_count = int(warning_match.group(1)) if warning_match else 0

# 生成报告
report = {
    "timestamp": datetime.now().isoformat(),
    "summary": summary,
    "errors": error_count,
    "warnings": warning_count,
    "status": "PASS" if error_count == 0 else "FAIL"
}

# 如果有错误，记录警告日志
if error_count > 0:
    unreal.log_error(f"Blueprint validation failed: {error_count} errors found")
elif warning_count > 0:
    unreal.log_warning(f"Blueprint validation passed with {warning_count} warnings")
else:
    unreal.log(f"Blueprint validation passed: {summary}")

RESULT = report
```

---

## 注意事项

- 此操作可能需要较长时间（取决于项目中蓝图数量）
- 建议在执行前保存所有修改
- 编译过程中会自动加载所有蓝图资产到内存
- 大型项目可能消耗大量内存
