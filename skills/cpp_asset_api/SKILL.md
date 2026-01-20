---
name: cpp_asset_api
description: CppSkillApiSubsystem 资产原语 - 重命名、复制、删除、保存资产
tags: [cpp, asset, api]
---

# CppSkillApiSubsystem - AssetOps

本 skill 文档描述 `UCppSkillApiSubsystem` 的资产相关原语。

## 入口说明

从 UE Python 中获取子系统：

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## 可用操作

| 方法 | C++ 签名 | Python 返回值 |
|------|----------|---------------|
| `rename_asset` | `bool RenameAsset(SourcePath, DestPath, OutError)` | `(success: bool, error: str)` |
| `duplicate_asset` | `bool DuplicateAsset(SourcePath, DestPath, OutError)` | `(success: bool, error: str)` |
| `delete_asset` | `bool DeleteAsset(AssetPath, OutError)` | `(success: bool, error: str)` |
| `save_asset` | `bool SaveAsset(AssetPath, OutError)` | `(success: bool, error: str)` |

详细接口和示例见 `docs/overview.md`。

## 快速示例

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 重命名资产 - 路径格式: /Game/Folder/AssetName
success, error = api.rename_asset(
    source_path="/Game/OldFolder/MyAsset",
    dest_path="/Game/NewFolder/RenamedAsset"
)

# 复制资产
success, error = api.duplicate_asset(
    source_path="/Game/Original/Asset",
    dest_path="/Game/Copied/Asset"
)

# 删除资产（警告：不可撤销）
success, error = api.delete_asset(asset_path="/Game/ToDelete")

# 保存资产
success, error = api.save_asset(asset_path="/Game/Modified")

# 错误处理
if not success:
    unreal.log_error(f"操作失败: {error}")
```
