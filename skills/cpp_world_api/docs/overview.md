# CppSkillApiSubsystem - World Operations

## 获取子系统

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## API 参考

### load_map

加载关卡。

**C++ 签名**:
```cpp
bool LoadMap(const FString& MapPath, FString& OutError);
```

**Python 调用**:
```python
success, error = api.load_map(map_path="/Game/Maps/MainLevel")
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `map_path` | `str` | 关卡资产路径（不含 `.umap` 扩展名） |

**返回**：`tuple[bool, str]`

---

### spawn_actor_by_class_path

在编辑器世界中生成 Actor。

**C++ 签名**:
```cpp
AActor* SpawnActorByClassPath(
    const FString& ClassPath,
    const FTransform& Transform,
    FString& OutError
);
```

**Python 调用**:
```python
actor, error = api.spawn_actor_by_class_path(
    class_path="/Game/Characters/BP_Hero.BP_Hero_C",
    transform=unreal.Transform(
        location=unreal.Vector(100, 200, 0),
        rotation=unreal.Rotator(0, 90, 0),
        scale=unreal.Vector(1, 1, 1)
    )
)
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `class_path` | `str` | 类路径（蓝图需加 `_C` 后缀） |
| `transform` | `unreal.Transform` | 生成位置、旋转、缩放 |

**返回**：`tuple[Actor, str]`
- `actor`: 生成的 Actor 对象，失败时为 `None`
- `error`: 错误信息

**类路径格式**：
| 类型 | 格式 | 示例 |
|------|------|------|
| 蓝图类 | `/Game/Path/BP_Name.BP_Name_C` | `/Game/Characters/BP_Hero.BP_Hero_C` |
| 原生类 | `/Script/Module.ClassName` | `/Script/Engine.PointLight` |

---

### find_actor_by_name

按名称查找 Actor。

**C++ 签名**:
```cpp
AActor* FindActorByName(const FString& ActorName);
```

**Python 调用**:
```python
actor = api.find_actor_by_name(actor_name="BP_Hero_C_0")
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `actor_name` | `str` | Actor 名称（大小写不敏感） |

**返回**：`Actor or None` - **注意：此函数没有 `error` 返回值**

---

### destroy_actor_by_name

按名称销毁 Actor。

**C++ 签名**:
```cpp
bool DestroyActorByName(const FString& ActorName, FString& OutError);
```

**Python 调用**:
```python
success, error = api.destroy_actor_by_name(actor_name="BP_Hero_C_0")
```

**返回**：`tuple[bool, str]`

---

### set_actor_property_by_string

设置 Actor 属性值。

**C++ 签名**:
```cpp
bool SetActorPropertyByString(
    const FString& ActorName,
    const FName& PropertyName,
    const FString& ValueAsString,
    FString& OutError
);
```

**Python 调用**:
```python
success, error = api.set_actor_property_by_string(
    actor_name="BP_Hero_C_0",
    property_name="MaxHealth",
    value_as_string="200.0"
)
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `actor_name` | `str` | Actor 名称 |
| `property_name` | `str` | 属性名称 |
| `value_as_string` | `str` | 属性值的字符串表示 |

**返回**：`tuple[bool, str]`

**支持的值格式**：同 `set_blueprint_cdo_property_by_string`

---

### set_actor_transform_by_name

设置 Actor 的 Transform。

**C++ 签名**:
```cpp
bool SetActorTransformByName(
    const FString& ActorName,
    const FTransform& Transform,
    FString& OutError
);
```

**Python 调用**:
```python
success, error = api.set_actor_transform_by_name(
    actor_name="BP_Hero_C_0",
    transform=unreal.Transform(
        location=unreal.Vector(500, 0, 100),
        rotation=unreal.Rotator(0, 180, 0),
        scale=unreal.Vector(2, 2, 2)
    )
)
```

**返回**：`tuple[bool, str]`

---

## 完整示例

### 批量生成 Actor

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

spawned = []
errors = []

for x in range(5):
    for y in range(5):
        transform = unreal.Transform(
            location=unreal.Vector(x * 200, y * 200, 0),
            rotation=unreal.Rotator(0, 0, 0),
            scale=unreal.Vector(1, 1, 1)
        )
        actor, error = api.spawn_actor_by_class_path(
            class_path="/Game/Props/BP_Crate.BP_Crate_C",
            transform=transform
        )
        if actor:
            spawned.append(actor.get_name())
        else:
            errors.append(error)

RESULT = {
    "spawned": spawned,
    "count": len(spawned),
    "errors": errors if errors else None
}
```

### 查找并修改 Actor

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 查找 Actor（注意：find_actor_by_name 只返回 Actor，没有 error）
actor = api.find_actor_by_name(actor_name="BP_Enemy_C_0")

if actor:
    # 获取当前位置
    current_loc = actor.get_actor_location()
    
    # 创建新 Transform（向上移动 100 单位）
    new_transform = unreal.Transform(
        location=unreal.Vector(current_loc.x, current_loc.y, current_loc.z + 100),
        rotation=unreal.Rotator(0, 0, 0),
        scale=unreal.Vector(1, 1, 1)
    )
    
    # 设置新位置
    success, error = api.set_actor_transform_by_name(
        actor_name="BP_Enemy_C_0",
        transform=new_transform
    )
    
    RESULT = {"found": True, "moved": success}
else:
    RESULT = {"found": False, "error": "Actor not found"}
```

### 清理关卡中的特定类型 Actor

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 获取所有以 "BP_Debris" 开头的 Actor
# 注意：这需要使用原生 unreal API 来遍历
actors = unreal.EditorLevelLibrary.get_all_level_actors()

deleted = []
for actor in actors:
    name = actor.get_name()
    if name.startswith("BP_Debris"):
        success, error = api.destroy_actor_by_name(actor_name=name)
        if success:
            deleted.append(name)

RESULT = {"deleted": deleted, "count": len(deleted)}
```
