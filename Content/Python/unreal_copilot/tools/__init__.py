"""
MCP Tools for Unreal Copilot.

工具设计原则：最小困惑度，用最少工具达成最完整能力。

核心工具（unified 模块）：
- search: 统一搜索（C++/Blueprint/Asset）
- get_hierarchy: 获取继承层次
- get_references: 获取引用关系
- get_details: 获取详细信息

特殊工具：
- blueprint.get_blueprint_graph: 蓝图节点图
- cpp.detect_ue_patterns: UE 模式检测
- cpp.get_cpp_blueprint_exposure: Blueprint 暴露 API
- cross_domain.trace_reference_chain: 跨域引用链
- cross_domain.find_cpp_class_usage: C++ 类使用查找

搜索范围（scope）：
- project: 只搜索项目源码（默认，快）
- engine: 只搜索引擎源码
- all: 搜索所有（慢但全面）
"""

from . import blueprint, cpp, cross_domain, unified

__all__ = ["unified", "blueprint", "cpp", "cross_domain"]

