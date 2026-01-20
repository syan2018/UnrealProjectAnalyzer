# CppSkillApiSubsystem - Editor Operations

## 获取子系统

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## API 参考

### list_dirty_packages

列出所有未保存的包。

**C++ 签名**:
```cpp
TArray<FString> ListDirtyPackages() const;
```

**Python 调用**:
```python
dirty_packages = api.list_dirty_packages()
# 返回: ["/Game/Characters/BP_Hero", "/Game/Maps/MainLevel", ...]
```

**返回**：`list[str]` - 未保存的包路径列表

**注意**：此函数没有 `OutError` 参数，直接返回列表。

---

### save_dirty_packages

保存所有未保存的包。

**C++ 签名**:
```cpp
bool SaveDirtyPackages(bool bPromptUser, FString& OutError);
```

**Python 调用**:
```python
success, error = api.save_dirty_packages(prompt_user=False)
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `prompt_user` | `bool` | `True`: 弹出保存对话框让用户确认；`False`: 静默保存 |

**返回**：`tuple[bool, str]`

---

### undo_last_transaction

撤销上一个事务。

**C++ 签名**:
```cpp
bool UndoLastTransaction(FString& OutError);
```

**Python 调用**:
```python
success, error = api.undo_last_transaction()
```

**返回**：`tuple[bool, str]`

**注意**：只能撤销支持 Unreal 事务系统的操作。

---

### redo_last_transaction

重做上一个撤销的事务。

**C++ 签名**:
```cpp
bool RedoLastTransaction(FString& OutError);
```

**Python 调用**:
```python
success, error = api.redo_last_transaction()
```

**返回**：`tuple[bool, str]`

---

## 完整示例

### 检查并保存所有修改

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 列出所有未保存的包
dirty = api.list_dirty_packages()

if dirty:
    print(f"Found {len(dirty)} dirty packages:")
    for pkg in dirty:
        print(f"  - {pkg}")
    
    # 静默保存所有
    success, error = api.save_dirty_packages(prompt_user=False)
    
    RESULT = {
        "dirty_count": len(dirty),
        "packages": dirty,
        "save_success": success,
        "error": error if not success else None
    }
else:
    RESULT = {"dirty_count": 0, "message": "No dirty packages"}
```

### 带撤销保护的操作

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 执行可能失败的操作
success, error = api.set_actor_property_by_string(
    actor_name="BP_Hero_C_0",
    property_name="MaxHealth",
    value_as_string="999"
)

if not success:
    # 操作失败，尝试撤销之前的修改
    undo_ok, undo_err = api.undo_last_transaction()
    RESULT = {"error": error, "reverted": undo_ok}
else:
    RESULT = {"success": True}
```

### 事务操作序列

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 执行一系列操作
operations = [
    lambda: api.set_actor_property_by_string("Actor1", "Health", "100"),
    lambda: api.set_actor_property_by_string("Actor2", "Health", "100"),
    lambda: api.set_actor_property_by_string("Actor3", "Health", "100"),
]

results = []
for i, op in enumerate(operations):
    success, error = op()
    results.append({"index": i, "success": success, "error": error})
    if not success:
        # 失败时撤销所有已完成的操作
        for _ in range(i):
            api.undo_last_transaction()
        break

# 成功后保存
if all(r["success"] for r in results):
    api.save_dirty_packages(prompt_user=False)

RESULT = {"operations": results}
```
