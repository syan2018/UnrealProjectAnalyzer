---
name: skill_script
description: 最小脚本示例，展示 main(args) + stdout + result
tags: [example, script, hidden]
---

# Skill 脚本示例

本 skill 演示一个最小可执行脚本：

- 脚本入口：`scripts/echo_args.py`
- 入口函数：`main(args: dict) -> dict`
- 运行方式：通过 `run_unreal_skill` 调用该脚本

## 说明

脚本会打印 `stdout`，并原样返回入参 `args` 作为 `result`。

