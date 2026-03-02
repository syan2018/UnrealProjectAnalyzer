---
name: cpp_blueprint_write_api
description: CppSkillApiSubsystem 蓝图写入原语 - 变量/图/节点增删改与批处理事务
tags: [cpp, blueprint, write, api]
---

# CppSkillApiSubsystem - Blueprint Write Ops

本 skill 面向蓝图写入与重构场景，覆盖：

- 变量：增删改、默认值设置
- 图：函数图/宏图/EventGraph 的增删改
- 节点：新增、删除、连线、引脚默认值
- 批处理：`execute_blueprint_commands` 事务化执行命令序列

## 入口说明

```python
import unreal
api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)
```

## 可用脚本

- `scripts/create_blueprint_with_components.py`
  - 创建蓝图后，批量添加组件和变量，最后编译/保存。
- `scripts/patch_graph_nodes.py`
  - 对单个蓝图执行节点级命令序列（推荐用于图重构）。
- `scripts/batch_refactor_blueprints.py`
  - 将同一组命令批量应用到多个蓝图路径。

详细 API 和命令格式见 `docs/overview.md`。
