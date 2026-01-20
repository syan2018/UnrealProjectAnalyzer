# CppSkillApiSubsystem - Asset Operations

## 获取子系统

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## API 参考

### rename_asset

重命名/移动资产。

**C++ 签名**:
```cpp
bool RenameAsset(const FString& SourcePath, const FString& DestPath, FString& OutError);
```

**Python 调用**:
```python
success, error = api.rename_asset(
    source_path="/Game/OldFolder/MyAsset",
    dest_path="/Game/NewFolder/RenamedAsset"
)
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `source_path` | `str` | 源资产路径（如 `/Game/Characters/BP_Hero`） |
| `dest_path` | `str` | 目标路径（如 `/Game/Characters/BP_Hero_New`） |

**返回**：`tuple[bool, str]`
- `success` (bool): 是否成功
- `error` (str): 失败时的错误信息，成功时为空字符串

**注意**：会自动修复重定向器（Redirectors）。

---

### duplicate_asset

复制资产到新位置。

**C++ 签名**:
```cpp
bool DuplicateAsset(const FString& SourcePath, const FString& DestPath, FString& OutError);
```

**Python 调用**:
```python
success, error = api.duplicate_asset(
    source_path="/Game/Characters/BP_Hero",
    dest_path="/Game/Characters/BP_Hero_Copy"
)
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `source_path` | `str` | 源资产路径 |
| `dest_path` | `str` | 目标路径 |

**返回**：`tuple[bool, str]`

---

### delete_asset

删除资产。

**C++ 签名**:
```cpp
bool DeleteAsset(const FString& AssetPath, FString& OutError);
```

**Python 调用**:
```python
success, error = api.delete_asset(asset_path="/Game/Characters/BP_Old")
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `asset_path` | `str` | 要删除的资产路径 |

**返回**：`tuple[bool, str]`

**⚠️ 警告**：此操作不可撤销，请谨慎使用。

---

### save_asset

保存单个资产。

**C++ 签名**:
```cpp
bool SaveAsset(const FString& AssetPath, FString& OutError);
```

**Python 调用**:
```python
success, error = api.save_asset(asset_path="/Game/Characters/BP_Hero")
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `asset_path` | `str` | 要保存的资产路径 |

**返回**：`tuple[bool, str]`

---

## 完整示例

### 批量重命名资产

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
registry = unreal.AssetRegistryHelpers.get_asset_registry()

# 获取指定目录下所有蓝图
filter = unreal.ARFilter()
filter.class_paths = [unreal.TopLevelAssetPath("/Script/Engine", "Blueprint")]
filter.package_paths = ["/Game/Characters"]
assets = registry.get_assets(filter)

results = []
for asset in assets:
    old_path = str(asset.package_name)
    if "Old" in old_path:
        new_path = old_path.replace("Old", "New")
        success, error = api.rename_asset(old_path, new_path)
        results.append({
            "old": old_path,
            "new": new_path,
            "success": success,
            "error": error if not success else None
        })

RESULT = {"renamed": results, "count": len(results)}
```

### 安全删除资产（带确认）

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 先尝试复制作为备份
asset_path = "/Game/ToDelete/MyAsset"
backup_path = "/Game/Backup/MyAsset_Backup"

success, error = api.duplicate_asset(asset_path, backup_path)
if success:
    # 备份成功后再删除
    success, error = api.delete_asset(asset_path)
    RESULT = {"deleted": success, "backup": backup_path}
else:
    RESULT = {"deleted": False, "error": f"备份失败: {error}"}
```
