import json
import unreal


def main(args):
    api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

    blueprint_path = args.get("blueprint_path")
    graph_name = args.get("graph_name", "EventGraph")
    node_guid = args.get("node_guid")

    if not blueprint_path:
        return {"ok": False, "error": "blueprint_path is required."}
    if not node_guid:
        return {"ok": False, "error": "node_guid is required."}

    raw = api.get_blueprint_node_pins(
        blueprint_path=blueprint_path,
        graph_name=graph_name,
        node_guid=node_guid,
    )

    try:
        return json.loads(raw)
    except Exception:
        return {"ok": False, "error": "get_blueprint_node_pins returned invalid json.", "raw": raw}
