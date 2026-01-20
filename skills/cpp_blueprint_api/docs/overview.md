# CppSkillApiSubsystem - Blueprint Operations

## 获取子系统

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## API 参考

### create_blueprint

创建新蓝图。

**C++ 签名**:
```cpp
bool CreateBlueprint(
    const FString& ParentClassPath,
    const FString& PackagePath,
    const FString& BlueprintName,
    FString& OutBlueprintPath,
    FString& OutError
);
```

**Python 调用**:
```python
success, bp_path, error = api.create_blueprint(
    parent_class_path="/Script/Engine.Actor",
    package_path="/Game/Characters",
    blueprint_name="BP_NewCharacter"
)
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `parent_class_path` | `str` | 父类路径（如 `/Script/Engine.Actor`） |
| `package_path` | `str` | 蓝图存放目录（如 `/Game/Characters`） |
| `blueprint_name` | `str` | 蓝图名称 |

**返回**：`tuple[bool, str, str]`
- `success` (bool): 是否成功
- `bp_path` (str): 创建的蓝图完整路径
- `error` (str): 失败时的错误信息

**常用父类路径**：
| 类型 | 路径 |
|------|------|
| Actor | `/Script/Engine.Actor` |
| Pawn | `/Script/Engine.Pawn` |
| Character | `/Script/Engine.Character` |
| ActorComponent | `/Script/Engine.ActorComponent` |
| SceneComponent | `/Script/Engine.SceneComponent` |
| GameModeBase | `/Script/Engine.GameModeBase` |
| PlayerController | `/Script/Engine.PlayerController` |

---

### compile_blueprint

编译蓝图。

**C++ 签名**:
```cpp
bool CompileBlueprint(const FString& BlueprintPath, FString& OutError);
```

**Python 调用**:
```python
success, error = api.compile_blueprint(blueprint_path="/Game/Characters/BP_Hero")
```

**返回**：`tuple[bool, str]`

---

### save_blueprint

保存蓝图（内部调用 `save_asset`）。

**C++ 签名**:
```cpp
bool SaveBlueprint(const FString& BlueprintPath, FString& OutError);
```

**Python 调用**:
```python
success, error = api.save_blueprint(blueprint_path="/Game/Characters/BP_Hero")
```

**返回**：`tuple[bool, str]`

---

### set_blueprint_cdo_property_by_string

设置蓝图 CDO（Class Default Object）属性值。

**C++ 签名**:
```cpp
bool SetBlueprintCDOPropertyByString(
    const FString& BlueprintPath,
    const FName& PropertyName,
    const FString& ValueAsString,
    FString& OutError
);
```

**Python 调用**:
```python
success, error = api.set_blueprint_cdo_property_by_string(
    blueprint_path="/Game/Characters/BP_Hero",
    property_name="MaxHealth",
    value_as_string="100.0"
)
```

**参数**：
| 参数 | 类型 | 描述 |
|------|------|------|
| `blueprint_path` | `str` | 蓝图路径 |
| `property_name` | `str` | 属性名称 |
| `value_as_string` | `str` | 属性值的字符串表示 |

**返回**：`tuple[bool, str]`

**支持的值格式**：
| 类型 | 格式示例 |
|------|----------|
| 整数 | `"100"` |
| 浮点数 | `"3.14"` |
| 布尔 | `"true"`, `"false"` |
| 字符串 | `"Hello World"` |
| FVector | `"(X=1.0,Y=2.0,Z=3.0)"` |
| FRotator | `"(Pitch=0.0,Yaw=90.0,Roll=0.0)"` |
| FLinearColor | `"(R=1.0,G=0.5,B=0.0,A=1.0)"` |

---

### add_blueprint_component

向蓝图添加组件。

**C++ 签名**:
```cpp
bool AddBlueprintComponent(
    const FString& BlueprintPath,
    const FString& ComponentClassPath,
    const FName& ComponentName,
    FString& OutError
);
```

**Python 调用**:
```python
success, error = api.add_blueprint_component(
    blueprint_path="/Game/Characters/BP_Hero",
    component_class_path="/Script/Engine.StaticMeshComponent",
    component_name="MyMesh"
)
```

**返回**：`tuple[bool, str]`

**常用组件类路径**：
| 组件类型 | 路径 |
|----------|------|
| StaticMeshComponent | `/Script/Engine.StaticMeshComponent` |
| SkeletalMeshComponent | `/Script/Engine.SkeletalMeshComponent` |
| BoxComponent | `/Script/Engine.BoxComponent` |
| SphereComponent | `/Script/Engine.SphereComponent` |
| CapsuleComponent | `/Script/Engine.CapsuleComponent` |
| AudioComponent | `/Script/Engine.AudioComponent` |
| PointLightComponent | `/Script/Engine.PointLightComponent` |
| SpotLightComponent | `/Script/Engine.SpotLightComponent` |
| ParticleSystemComponent | `/Script/Engine.ParticleSystemComponent` |

---

### remove_blueprint_component

从蓝图移除组件。

**C++ 签名**:
```cpp
bool RemoveBlueprintComponent(
    const FString& BlueprintPath,
    const FName& ComponentName,
    FString& OutError
);
```

**Python 调用**:
```python
success, error = api.remove_blueprint_component(
    blueprint_path="/Game/Characters/BP_Hero",
    component_name="MyMesh"
)
```

**返回**：`tuple[bool, str]`

---

## 完整示例

### 创建并配置蓝图

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

# 1. 创建蓝图
success, bp_path, error = api.create_blueprint(
    parent_class_path="/Script/Engine.Actor",
    package_path="/Game/Gameplay",
    blueprint_name="BP_HealthPickup"
)

if success:
    # 2. 添加组件
    api.add_blueprint_component(
        blueprint_path=bp_path,
        component_class_path="/Script/Engine.StaticMeshComponent",
        component_name="PickupMesh"
    )
    api.add_blueprint_component(
        blueprint_path=bp_path,
        component_class_path="/Script/Engine.SphereComponent",
        component_name="CollisionSphere"
    )
    
    # 3. 设置默认值
    api.set_blueprint_cdo_property_by_string(
        blueprint_path=bp_path,
        property_name="HealAmount",
        value_as_string="50.0"
    )
    
    # 4. 编译并保存
    compile_ok, compile_err = api.compile_blueprint(blueprint_path=bp_path)
    save_ok, save_err = api.save_blueprint(blueprint_path=bp_path)
    
    RESULT = {
        "created": bp_path,
        "compiled": compile_ok,
        "saved": save_ok
    }
else:
    RESULT = {"error": error}
```

### 批量修改蓝图属性

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
registry = unreal.AssetRegistryHelpers.get_asset_registry()

# 获取所有角色蓝图
filter = unreal.ARFilter()
filter.class_paths = [unreal.TopLevelAssetPath("/Script/Engine", "Blueprint")]
filter.package_paths = ["/Game/Characters"]
assets = registry.get_assets(filter)

results = []
for asset in assets:
    bp_path = str(asset.package_name)
    
    # 修改属性
    success, error = api.set_blueprint_cdo_property_by_string(
        blueprint_path=bp_path,
        property_name="MaxHealth",
        value_as_string="150.0"
    )
    
    if success:
        # 编译并保存
        api.compile_blueprint(blueprint_path=bp_path)
        api.save_blueprint(blueprint_path=bp_path)
    
    results.append({"path": bp_path, "success": success})

RESULT = {"modified": results}
```
