---
name: cpp_blueprint_api
description: CppSkillApiSubsystem 蓝图原语 - 创建、编译、保存蓝图，设置 CDO 属性，管理组件
tags: [cpp, blueprint, api]
---

# CppSkillApiSubsystem - BlueprintOps

本 skill 文档描述 `UCppSkillApiSubsystem` 的蓝图相关原语。

## 入口说明

从 UE Python 中获取子系统：

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## 可用操作

| 方法 | C++ 签名 | Python 返回值 |
|------|----------|---------------|
| `create_blueprint` | `bool CreateBlueprint(ParentClassPath, PackagePath, BlueprintName, OutBlueprintPath, OutError)` | `(success: bool, bp_path: str, error: str)` |
| `compile_blueprint` | `bool CompileBlueprint(BlueprintPath, OutError)` | `(success: bool, error: str)` |
| `save_blueprint` | `bool SaveBlueprint(BlueprintPath, OutError)` | `(success: bool, error: str)` |
| `set_blueprint_cdo_property_by_string` | `bool SetBlueprintCDOPropertyByString(BlueprintPath, PropertyName, ValueAsString, OutError)` | `(success: bool, error: str)` |
| `add_blueprint_component` | `bool AddBlueprintComponent(BlueprintPath, ComponentClassPath, ComponentName, OutError)` | `(success: bool, error: str)` |
| `remove_blueprint_component` | `bool RemoveBlueprintComponent(BlueprintPath, ComponentName, OutError)` | `(success: bool, error: str)` |

详细接口和示例见 `docs/overview.md`。

## 快速示例

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 创建蓝图 - 返回 (success, bp_path, error)
success, bp_path, error = api.create_blueprint(
    parent_class_path="/Script/Engine.Actor",
    package_path="/Game/Blueprints",
    blueprint_name="BP_MyActor"
)

if success:
    # 添加组件
    success, error = api.add_blueprint_component(
        blueprint_path=bp_path,
        component_class_path="/Script/Engine.StaticMeshComponent",
        component_name="Mesh"
    )

    # 设置默认值
    success, error = api.set_blueprint_cdo_property_by_string(
        blueprint_path=bp_path,
        property_name="MyProperty",
        value_as_string="100"
    )

    # 编译并保存
    success, error = api.compile_blueprint(blueprint_path=bp_path)
    success, error = api.save_blueprint(blueprint_path=bp_path)
else:
    unreal.log_error(f"创建蓝图失败: {error}")
```

## 常用父类路径

| 类型 | 路径 |
|------|------|
| Actor | `/Script/Engine.Actor` |
| Pawn | `/Script/Engine.Pawn` |
| Character | `/Script/Engine.Character` |
| ActorComponent | `/Script/Engine.ActorComponent` |
| SceneComponent | `/Script/Engine.SceneComponent` |
| GameModeBase | `/Script/Engine.GameModeBase` |
| PlayerController | `/Script/Engine.PlayerController` |
