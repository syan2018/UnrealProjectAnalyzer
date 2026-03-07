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

### list_blueprint_components

列举蓝图 SCS 中所有组件（名称 + 类名）。

**C++ 签名**:
```cpp
FString ListBlueprintComponents(const FString& BlueprintPath);
```

**Python 调用**:
```python
import json
result = json.loads(api.list_blueprint_components(blueprint_path="/Game/Characters/BP_Hero"))
# result = {"ok": true, "components": [{"name": "MyMesh", "class": "StaticMeshComponent"}, ...]}
```

**返回**：`str`（JSON 字符串）
- `ok` (bool): 是否成功
- `components` (array): 组件列表，每项包含 `name` 和 `class`

---

### get_blueprint_component_template

获取蓝图 SCS 组件模板的 UObject 引用。**这是操作 SCS 组件属性的核心原语**——拿到引用后，Python 可以直接用 `set_editor_property` / `get_editor_property` 操作任意属性类型，包括 TMap、TArray、TSet 等容器类型。

**C++ 签名**:
```cpp
UActorComponent* GetBlueprintComponentTemplate(
    const FString& BlueprintPath,
    const FName& ComponentName,
    FString& OutError
);
```

**Python 调用**:
```python
template, error = api.get_blueprint_component_template(
    blueprint_path="/Game/Characters/BP_Hero",
    component_name="SyCombatLyraInputBridge_GEN_VARIABLE"
)
# template 是 UActorComponent*，可直接用 set_editor_property
```

**返回**：`tuple[UActorComponent, str]`
- `template`: 组件模板对象引用（None 表示失败）
- `error` (str): 失败时的错误信息

> **推荐工作流**：对于简单类型（bool/int/float/string/struct），可用 `set_blueprint_component_property_by_string`。
> 对于容器类型（TMap/TArray/TSet），使用 `get_blueprint_component_template` 拿到引用后用 Python 原生 API 操作。

---

### set_blueprint_component_property_by_string

设置蓝图 SCS 组件模板上的简单属性（通过文本导入）。适用于 bool、int、float、FString、FGameplayTag 等可文本化的类型。**不支持 TMap/TArray 等容器类型**——容器类型请用 `get_blueprint_component_template` + `set_editor_property`。

**C++ 签名**:
```cpp
bool SetBlueprintComponentPropertyByString(
    const FString& BlueprintPath,
    const FName& ComponentName,
    const FName& PropertyName,
    const FString& ValueAsString,
    FString& OutError
);
```

**Python 调用**:
```python
success, error = api.set_blueprint_component_property_by_string(
    blueprint_path="/Game/Characters/BP_Hero",
    component_name="SyCombatLyraInputBridge_GEN_VARIABLE",
    property_name="bTakeoverMode",
    value_as_string="true"
)
```

**返回**：`tuple[bool, str]`

---

### get_blueprint_component_property_by_string

读取蓝图 SCS 组件模板上的属性值（文本导出）。

**C++ 签名**:
```cpp
bool GetBlueprintComponentPropertyByString(
    const FString& BlueprintPath,
    const FName& ComponentName,
    const FName& PropertyName,
    FString& OutValue,
    FString& OutError
);
```

**Python 调用**:
```python
value, error = api.get_blueprint_component_property_by_string(
    blueprint_path="/Game/Characters/BP_Hero",
    component_name="SyCombatLyraInputBridge_GEN_VARIABLE",
    property_name="bTakeoverMode"
)
# value 为属性的 ExportText 字符串
```

**返回**：`tuple[str, str]`
- `value` (str): 属性值的文本表示
- `error` (str): 失败时的错误信息

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

### 配置蓝图组件属性（简单类型）

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
bp_path = "/Game/Characters/Heroes/B_Hero_Default"

# 1. 列举组件（名称带 _GEN_VARIABLE 后缀）
import json
comps = json.loads(api.list_blueprint_components(blueprint_path=bp_path))
print(comps)  # {"ok": true, "components": [{"name": "xxx_GEN_VARIABLE", "class": "..."}]}

# 2. 设置简单属性
api.set_blueprint_component_property_by_string(
    blueprint_path=bp_path,
    component_name="SyCombatLyraInputBridge_GEN_VARIABLE",
    property_name="bTakeoverMode",
    value_as_string="true"
)

# 3. 编译并保存
api.compile_blueprint(blueprint_path=bp_path)
api.save_blueprint(blueprint_path=bp_path)
```

### 配置蓝图组件属性（TMap/TArray 容器类型）

对于 TMap、TArray、TSet 等容器类型，`ImportText` 不可靠。
**推荐方式**：用 `get_blueprint_component_template` 拿到组件模板引用，再用 Python 原生 `set_editor_property` 操作。

```python
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
bp_path = "/Game/Characters/Heroes/B_Hero_Default"

# 1. 获取组件模板引用
template, error = api.get_blueprint_component_template(
    blueprint_path=bp_path,
    component_name="SyCombatLyraInputBridge_GEN_VARIABLE"
)

# 2. 构建 TMap<FGameplayTag, FGameplayTag>
def make_tag(name):
    tag = unreal.GameplayTag()
    tag.import_text(f'(TagName="{name}")')
    return tag

tag_map = unreal.Map(unreal.GameplayTag, unreal.GameplayTag)
for tag_name in ["InputTag.Weapon.Fire", "InputTag.Weapon.Reload", "InputTag.Jump"]:
    tag_map[make_tag(tag_name)] = make_tag(tag_name)

# 3. 直接设置到组件模板上
template.set_editor_property("InputTagToActionTag", tag_map)

# 4. 标记蓝图已修改 + 编译保存
from unreal import BlueprintEditorLibrary
# 或直接编译（编译时会自动标记修改）
api.compile_blueprint(blueprint_path=bp_path)
api.save_blueprint(blueprint_path=bp_path)
```

---

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
