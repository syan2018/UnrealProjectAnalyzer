---
name: cpp_world_api
description: CppSkillApiSubsystem 世界原语 - 加载关卡、生成/查找/销毁 Actor、设置属性和 Transform
tags: [cpp, world, actor, api]
---

# CppSkillApiSubsystem - WorldOps

本 skill 文档描述 `UCppSkillApiSubsystem` 的世界/关卡相关原语。

## 入口说明

从 UE Python 中获取子系统：

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## 可用操作

| 方法 | C++ 签名 | Python 返回值 |
|------|----------|---------------|
| `load_map` | `bool LoadMap(MapPath, OutError)` | `(success: bool, error: str)` |
| `spawn_actor_by_class_path` | `AActor* SpawnActorByClassPath(ClassPath, Transform, OutError)` | `(actor: Actor, error: str)` |
| `find_actor_by_name` | `AActor* FindActorByName(ActorName)` | `Actor or None` |
| `destroy_actor_by_name` | `bool DestroyActorByName(ActorName, OutError)` | `(success: bool, error: str)` |
| `set_actor_property_by_string` | `bool SetActorPropertyByString(ActorName, PropertyName, ValueAsString, OutError)` | `(success: bool, error: str)` |
| `set_actor_transform_by_name` | `bool SetActorTransformByName(ActorName, Transform, OutError)` | `(success: bool, error: str)` |

详细接口和示例见 `docs/overview.md`。

## 快速示例

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 加载关卡
success, error = api.load_map(map_path="/Game/Maps/MainLevel")

# 生成 Actor
transform = unreal.Transform(
    location=unreal.Vector(100, 0, 0),
    rotation=unreal.Rotator(0, 0, 0),
    scale=unreal.Vector(1, 1, 1)
)
# 注意：蓝图类路径需要加 _C 后缀
actor, error = api.spawn_actor_by_class_path(
    class_path="/Game/Characters/BP_Hero.BP_Hero_C",
    transform=transform
)

# 查找 Actor - 直接返回 Actor 或 None，无 error
found = api.find_actor_by_name(actor_name="BP_Hero_C_0")
if found:
    print(f"找到 Actor: {found.get_name()}")

# 设置 Transform
success, error = api.set_actor_transform_by_name(
    actor_name="BP_Hero_C_0",
    transform=transform
)

# 设置属性
success, error = api.set_actor_property_by_string(
    actor_name="BP_Hero_C_0",
    property_name="MaxHealth",
    value_as_string="200.0"
)

# 销毁 Actor
success, error = api.destroy_actor_by_name(actor_name="BP_Hero_C_0")
```

## 常用类路径格式

| 类型 | 格式 | 示例 |
|------|------|------|
| 蓝图类 | `/Game/Path/BP_Name.BP_Name_C` | `/Game/Characters/BP_Hero.BP_Hero_C` |
| 原生类 | `/Script/Module.ClassName` | `/Script/Engine.PointLight` |
