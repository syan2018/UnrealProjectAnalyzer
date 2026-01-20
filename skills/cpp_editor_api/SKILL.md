---
name: cpp_editor_api
description: CppSkillApiSubsystem 编辑器原语 - 列出/保存未保存包、撤销/重做事务
tags: [cpp, editor, save, undo, api]
---

# CppSkillApiSubsystem - EditorOps

本 skill 文档描述 `UCppSkillApiSubsystem` 的编辑器相关原语。

## 入口说明

从 UE Python 中获取子系统：

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## 可用操作

| 方法 | C++ 签名 | Python 返回值 |
|------|----------|---------------|
| `list_dirty_packages` | `TArray<FString> ListDirtyPackages() const` | `list[str]` |
| `save_dirty_packages` | `bool SaveDirtyPackages(bPromptUser, OutError)` | `(success: bool, error: str)` |
| `undo_last_transaction` | `bool UndoLastTransaction(OutError)` | `(success: bool, error: str)` |
| `redo_last_transaction` | `bool RedoLastTransaction(OutError)` | `(success: bool, error: str)` |

详细接口和示例见 `docs/overview.md`。

## 快速示例

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 列出未保存的包 - 直接返回列表
dirty = api.list_dirty_packages()
print(f"Dirty packages ({len(dirty)}): {dirty}")

# 保存所有未保存的包
# prompt_user=False: 静默保存，不弹出对话框
# prompt_user=True: 弹出保存对话框让用户确认
success, error = api.save_dirty_packages(prompt_user=False)
if not success:
    unreal.log_error(f"保存失败: {error}")

# 撤销上一个事务 - 返回 (success, error)
success, error = api.undo_last_transaction()
if not success:
    unreal.log_warning(f"撤销失败: {error}")

# 重做上一个撤销的事务 - 返回 (success, error)
success, error = api.redo_last_transaction()
if not success:
    unreal.log_warning(f"重做失败: {error}")
```

## 注意事项

- `undo_last_transaction` / `redo_last_transaction` 只能撤销/重做支持事务系统的操作
- 某些编辑器操作可能不支持撤销
