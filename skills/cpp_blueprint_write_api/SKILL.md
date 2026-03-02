---
name: cpp_blueprint_write_api
description: CppSkillApiSubsystem 蓝图写入原语 - 变量/图/节点增删改与批处理事务
tags: [cpp, blueprint, write, api]
---

# CppSkillApiSubsystem - Blueprint Write Ops

本 skill 面向蓝图写入与重构场景，覆盖：

- 变量：增删改、默认值设置
- 图：函数图/宏图/EventGraph 的增删改
- 节点：新增、删除、连线、引脚默认值、函数调用节点快速创建
- 引脚发现：按 `node_guid` 获取结构化引脚清单
- 批处理：`execute_blueprint_commands` 与 `execute_blueprint_operation` 事务化执行

## 入口说明

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## 可用脚本

- `scripts/create_blueprint_with_components.py`
  - 创建蓝图后，批量添加组件和变量，最后编译/保存。
- `scripts/patch_graph_nodes.py`
  - 对单个蓝图执行节点级命令序列，或单操作 JSON（推荐用于图重构）。
- `scripts/batch_refactor_blueprints.py`
  - 将同一组命令或单操作批量应用到多个蓝图路径。
- `scripts/add_function_call_node.py`
  - 按函数路径新增可执行函数调用节点（例如 `PrintString`）。
- `scripts/list_node_pins.py`
  - 输出节点引脚清单，辅助连线与默认值设置。

详细 API 和命令格式见 `docs/overview.md`。
