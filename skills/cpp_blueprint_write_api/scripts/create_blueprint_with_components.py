import unreal


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _normalize_error_result(ret):
    if isinstance(ret, tuple):
        if len(ret) >= 2 and isinstance(ret[0], bool):
            return bool(ret[0]), str(ret[1] or "")
        if len(ret) >= 1:
            err = ret[-1]
            err_str = "" if err is None else str(err)
            return err_str == "", err_str
        return True, ""
    if ret is None:
        return True, ""
    err_str = str(ret)
    return err_str.strip() == "", err_str


def _normalize_create_result(ret):
    if isinstance(ret, tuple):
        if len(ret) >= 3 and isinstance(ret[0], bool):
            return bool(ret[0]), str(ret[1] or ""), str(ret[2] or "")
        if len(ret) >= 2 and isinstance(ret[0], str):
            path = str(ret[0] or "")
            err = str(ret[1] or "")
            return err.strip() == "" and path != "", path, err
        if len(ret) >= 2 and isinstance(ret[0], bool):
            return bool(ret[0]), str(ret[1] or ""), ""
    if isinstance(ret, str):
        # Fallback: treat a single string as error text when no structured tuple is provided.
        return False, "", ret
    return False, "", "Unexpected create_blueprint return format."


def main(args):
    api = unreal.get_editor_subsystem(unreal.CppSkillApiSubsystem)

    parent_class_path = args.get("parent_class_path", "/Script/Engine.Actor")
    package_path = args.get("package_path")
    blueprint_name = args.get("blueprint_name")
    components = args.get("components", [])
    variables = args.get("variables", [])
    auto_compile = _as_bool(args.get("auto_compile"), True)
    auto_save = _as_bool(args.get("auto_save"), True)

    if not package_path or not blueprint_name:
        return {
            "ok": False,
            "error": "package_path and blueprint_name are required.",
        }

    ok, bp_path, error = _normalize_create_result(api.create_blueprint(
        parent_class_path=parent_class_path,
        package_path=package_path,
        blueprint_name=blueprint_name,
    ))
    if not ok:
        return {"ok": False, "error": error}

    step_results = []

    for item in components:
        class_path = item.get("component_class_path")
        name = item.get("component_name")
        if not class_path or not name:
            step_results.append(
                {
                    "op": "add_component",
                    "ok": False,
                    "error": "component_class_path and component_name are required.",
                    "input": item,
                }
            )
            continue

        comp_ok, comp_error = _normalize_error_result(api.add_blueprint_component(
            blueprint_path=bp_path,
            component_class_path=class_path,
            component_name=name,
        ))
        step_results.append(
            {
                "op": "add_component",
                "ok": bool(comp_ok),
                "error": comp_error,
                "component_name": name,
                "component_class_path": class_path,
            }
        )

    for item in variables:
        var_name = item.get("variable_name")
        var_type = item.get("variable_type", "string")
        default_value = item.get("default_value", "")
        if not var_name:
            step_results.append(
                {
                    "op": "add_variable",
                    "ok": False,
                    "error": "variable_name is required.",
                    "input": item,
                }
            )
            continue

        var_ok, var_error = _normalize_error_result(api.add_blueprint_variable(
            blueprint_path=bp_path,
            variable_name=var_name,
            variable_type=var_type,
            default_value=str(default_value),
        ))
        step_results.append(
            {
                "op": "add_variable",
                "ok": bool(var_ok),
                "error": var_error,
                "variable_name": var_name,
                "variable_type": var_type,
            }
        )

    compile_ok = None
    compile_error = ""
    if auto_compile:
        compile_ok, compile_error = _normalize_error_result(
            api.compile_blueprint(blueprint_path=bp_path)
        )

    save_ok = None
    save_error = ""
    if auto_save:
        save_ok, save_error = _normalize_error_result(
            api.save_blueprint(blueprint_path=bp_path)
        )

    return {
        "ok": True,
        "blueprint_path": bp_path,
        "steps": step_results,
        "compile": {"enabled": auto_compile, "ok": compile_ok, "error": compile_error},
        "save": {"enabled": auto_save, "ok": save_ok, "error": save_error},
    }
