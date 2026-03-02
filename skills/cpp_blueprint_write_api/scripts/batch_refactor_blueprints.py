import json
import unreal


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _to_commands_json(args):
    if "commands_json" in args and args["commands_json"]:
        if isinstance(args["commands_json"], str):
            return args["commands_json"]
        return json.dumps(args["commands_json"], ensure_ascii=False)

    return json.dumps(args.get("commands", []), ensure_ascii=False)


def main(args):
    api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

    blueprint_paths = args.get("blueprint_paths", [])
    if not blueprint_paths:
        return {"ok": False, "error": "blueprint_paths is required and must not be empty."}

    commands_json = _to_commands_json(args)
    auto_compile = _as_bool(args.get("auto_compile"), True)
    auto_save = _as_bool(args.get("auto_save"), False)

    reports = []
    success_count = 0
    failure_count = 0

    for blueprint_path in blueprint_paths:
        report_json = api.execute_blueprint_commands(
            blueprint_path=blueprint_path,
            commands_json=commands_json,
            auto_compile=auto_compile,
            auto_save=auto_save,
        )

        try:
            report = json.loads(report_json)
        except Exception:
            report = {
                "ok": False,
                "error": "execute_blueprint_commands returned invalid json.",
                "raw": report_json,
            }

        report["blueprint_path"] = blueprint_path
        reports.append(report)

        if report.get("ok"):
            success_count += 1
        else:
            failure_count += 1

    return {
        "ok": failure_count == 0,
        "total": len(blueprint_paths),
        "success_count": success_count,
        "failure_count": failure_count,
        "reports": reports,
    }
