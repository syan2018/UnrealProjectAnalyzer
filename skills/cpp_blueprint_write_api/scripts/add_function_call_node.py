import unreal


def _as_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def main(args):
    api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

    blueprint_path = args.get("blueprint_path")
    graph_name = args.get("graph_name", "EventGraph")
    function_path = args.get("function_path")
    node_pos_x = _as_int(args.get("node_pos_x", 0))
    node_pos_y = _as_int(args.get("node_pos_y", 0))

    if not blueprint_path:
        return {"ok": False, "error": "blueprint_path is required."}
    if not function_path:
        return {"ok": False, "error": "function_path is required."}

    node_guid, error = api.add_blueprint_function_call_node(
        blueprint_path=blueprint_path,
        graph_name=graph_name,
        function_path=function_path,
        node_pos_x=node_pos_x,
        node_pos_y=node_pos_y,
    )

    return {
        "ok": (error is None or str(error).strip() == ""),
        "error": error,
        "blueprint_path": blueprint_path,
        "graph_name": graph_name,
        "function_path": function_path,
        "node_guid": node_guid,
    }
