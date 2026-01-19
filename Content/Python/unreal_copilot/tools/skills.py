from __future__ import annotations

import ast
import json
from typing import Any, Dict, Optional

from ..skills.runner import SkillRunner

_runner = SkillRunner()


def list_unreal_skill(query: Optional[str] = None, include_hidden: Optional[bool] = None) -> Dict[str, Any]:
    try:
        return _runner.list_skills(query=query, include_hidden=bool(include_hidden))
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def read_unreal_skill(skill_name: str, path: Optional[str] = None) -> Dict[str, Any]:
    try:
        return _runner.read_skill(skill_name=skill_name, path=path)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_unreal_skill(
    *,
    skill_name: Optional[str] = None,
    script: Optional[str] = None,
    args: Optional[Dict[str, Any] | str] = None,
    python: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        normalized_args = _normalize_args(args)

        if python is not None and python.strip():
            return _runner.run_inline_python(python_code=python, args=normalized_args)

        if not skill_name:
            return {"ok": False, "error": "skill_name is required when running a skill script"}
        if not script:
            return {"ok": False, "error": "script is required when running a skill script"}

        return _runner.run_script(skill_name=skill_name, script=script, args=normalized_args)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _normalize_args(args: Optional[Dict[str, Any] | str]) -> Optional[Dict[str, Any]]:
    if args is None:
        return None
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        raw = args.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            try:
                # Accept Python-style dict strings (e.g. "{'foo': 1}") from tools/LLMs.
                parsed = ast.literal_eval(raw)
            except (ValueError, SyntaxError) as exc:
                raise ValueError("args must be a JSON object or dict string") from exc
        if not isinstance(parsed, dict):
            raise ValueError("args must resolve to a dict/object")
        return parsed
    raise ValueError("args must be a dict or JSON object string")

