# CppSkillApiSubsystem - Blueprint Write API

## 获取子系统

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## API 一览

| 方法 | Python 返回值 |
|------|---------------|
| `add_blueprint_variable(blueprint_path, variable_name, variable_type, default_value)` | `(success: bool, error: str)` |
| `remove_blueprint_variable(blueprint_path, variable_name)` | `(success: bool, error: str)` |
| `rename_blueprint_variable(blueprint_path, old_variable_name, new_variable_name)` | `(success: bool, error: str)` |
| `set_blueprint_variable_default(blueprint_path, variable_name, default_value)` | `(success: bool, error: str)` |
| `add_blueprint_graph(blueprint_path, graph_name, graph_type)` | `(success: bool, error: str)` |
| `remove_blueprint_graph(blueprint_path, graph_name)` | `(success: bool, error: str)` |
| `rename_blueprint_graph(blueprint_path, old_graph_name, new_graph_name)` | `(success: bool, error: str)` |
| `add_blueprint_node(blueprint_path, graph_name, node_class_path, node_pos_x, node_pos_y)` | `(success: bool, node_guid: str, error: str)` |
| `remove_blueprint_node(blueprint_path, graph_name, node_guid)` | `(success: bool, error: str)` |
| `connect_blueprint_pins(blueprint_path, graph_name, from_node_guid, from_pin_name, to_node_guid, to_pin_name)` | `(success: bool, error: str)` |
| `set_blueprint_pin_default(blueprint_path, graph_name, node_guid, pin_name, value_as_string)` | `(success: bool, error: str)` |
| `execute_blueprint_commands(blueprint_path, commands_json, auto_compile, auto_save)` | `report_json: str` |

> 说明：在当前 UE Python 绑定下，很多 `bool + OutError` 形式接口会只返回 `OutError`（空字符串表示成功）。

## 变量类型格式 (`variable_type`)

基础类型：

- `bool`
- `int` / `int32`
- `int64`
- `float`
- `double`
- `name`
- `string`
- `text`
- `vector`
- `rotator`
- `transform`

带子类型路径：

- `object:/Script/Engine.Texture2D`
- `class:/Script/Engine.Actor`
- `softobject:/Script/Engine.StaticMesh`
- `softclass:/Script/Engine.Actor`
- `struct:/Script/CoreUObject.Vector`

## 批处理命令格式

`commands_json` 支持两种格式：

1. `[{...}, {...}]`
2. `{"commands": [{...}, {...}]}`

每条命令至少包含 `op` 字段。当前支持：

- `add_variable`
- `remove_variable`
- `rename_variable`
- `set_variable_default`
- `add_graph`
- `remove_graph`
- `rename_graph`
- `add_node`
- `remove_node`
- `connect_pins`
- `set_pin_default`

### 示例：节点写入批处理

```python
import json
import unreal

api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

commands = [
    {
        "op": "add_graph",
        "graph_name": "AI_Init",
        "graph_type": "function",
    },
    {
        "op": "add_node",
        "graph_name": "AI_Init",
        "node_class_path": "/Script/BlueprintGraph.K2Node_Event",
        "node_pos_x": 0,
        "node_pos_y": 0,
    },
]

report_json = api.execute_blueprint_commands(
    blueprint_path="/Game/AI/BP_BotController",
    commands_json=json.dumps(commands),
    auto_compile=True,
    auto_save=True,
)
report = json.loads(report_json)
RESULT = report
```

## 事务与回滚约定

- 写操作在 Editor + GameThread 下执行。
- PIE 运行中会拒绝写入。
- `execute_blueprint_commands` 中命令或自动编译失败时，会触发回滚（Undo）。
- 自动保存失败会返回错误信息，但不自动回滚已执行写入。
