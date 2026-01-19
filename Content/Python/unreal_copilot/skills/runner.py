from __future__ import annotations

import contextlib
import io
import os
import runpy
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SkillRunner:
    def __init__(self, skills_root: Optional[Path] = None) -> None:
        self.skills_root = skills_root or self._resolve_default_skills_root()

    def list_skills(self, query: Optional[str] = None, include_hidden: bool = False) -> Dict[str, Any]:
        if not self.skills_root.exists():
            return {"ok": True, "skills": []}

        query_lower = query.strip().lower() if query else None
        skills: List[Dict[str, Any]] = []

        for skill_dir in sorted(self.skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            text = skill_md.read_text(encoding="utf-8")
            meta, body = self._parse_front_matter(text)
            name = (meta.get("name") or skill_dir.name).strip()
            description = (meta.get("description") or self._first_non_empty_line(body)).strip()
            tags = meta.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]

            if not include_hidden and "hidden" in tags:
                continue

            item = {
                "name": name,
                "description": description,
                "tags": tags,
                "skill_root": str(skill_dir),
            }

            if query_lower:
                hay = " ".join([name, description, " ".join(tags)]).lower()
                if query_lower not in hay:
                    continue

            skills.append(item)

        return {"ok": True, "skills": skills}

    def read_skill(self, skill_name: str, path: Optional[str] = None) -> Dict[str, Any]:
        skill_root = self._resolve_skill_root(skill_name)

        relative_path = path or "SKILL.md"
        target = self._resolve_safe_path(skill_root, relative_path)
        if not target.exists() or not target.is_file():
            return {"ok": False, "error": f"File not found: {relative_path}"}

        content = target.read_text(encoding="utf-8")
        result: Dict[str, Any] = {"ok": True, "content": content}

        if path is None:
            result["tree"] = self._build_tree(skill_root)

        return result

    def run_script(
        self, skill_name: str, script: str, args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        skill_root = self._resolve_skill_root(skill_name)
        script_path = Path(script)
        if script_path.is_absolute():
            return {"ok": False, "error": "Absolute script path is not allowed"}

        if "scripts" not in script_path.parts:
            script_path = Path("scripts") / script_path

        target = self._resolve_safe_path(skill_root, str(script_path))
        if not target.exists() or not target.is_file():
            return {"ok": False, "error": f"Script not found: {script_path.as_posix()}"}

        return self._exec_script(target, args or {})

    def run_inline_python(
        self, python_code: str, args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        stdout, result, error = self._exec_inline(python_code, args or {})
        if error:
            return {"ok": False, "stdout": stdout, "error": error}
        return {"ok": True, "stdout": stdout, "result": result}

    def _resolve_default_skills_root(self) -> Path:
        # .../Plugins/UnrealCopilot/Content/Python/unreal_copilot/skills/runner.py
        # skill root: .../Plugins/UnrealCopilot/skills
        here = Path(__file__).resolve()
        plugin_root = here.parents[4]
        return plugin_root / "skills"

    def _resolve_skill_root(self, skill_name: str) -> Path:
        skill_root = (self.skills_root / skill_name).resolve()
        if not skill_root.exists() or not skill_root.is_dir():
            raise ValueError(f"Skill not found: {skill_name}")
        return skill_root

    def _resolve_safe_path(self, skill_root: Path, relative_path: str) -> Path:
        candidate = (skill_root / relative_path).resolve()
        root = skill_root.resolve()
        if os.path.commonpath([str(candidate), str(root)]) != str(root):
            raise ValueError("Path escapes skill root")
        return candidate

    def _build_tree(self, skill_root: Path) -> List[str]:
        files: List[str] = []

        skill_md = skill_root / "SKILL.md"
        if skill_md.exists():
            files.append(skill_md.relative_to(skill_root).as_posix())

        for folder_name in ("docs", "scripts"):
            folder = skill_root / folder_name
            if not folder.exists():
                continue
            for item in sorted(folder.rglob("*")):
                if item.is_file():
                    files.append(item.relative_to(skill_root).as_posix())

        return files

    def _parse_front_matter(self, text: str) -> Tuple[Dict[str, Any], str]:
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, text

        end_index = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                end_index = idx
                break

        if end_index is None:
            return {}, text

        yaml_lines = lines[1:end_index]
        body = "\n".join(lines[end_index + 1 :])
        meta = self._parse_simple_yaml(yaml_lines)
        return meta, body

    def _parse_simple_yaml(self, lines: List[str]) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue

            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()

            if value.startswith("[") and value.endswith("]"):
                items = [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
                data[key] = items
            else:
                data[key] = value.strip().strip("'\"")
        return data

    def _first_non_empty_line(self, body: str) -> str:
        for line in body.splitlines():
            if line.strip():
                return line.strip()
        return ""

    def _exec_script(self, script_path: Path, args: Dict[str, Any]) -> Dict[str, Any]:
        stdout, result, error = self._exec_with_capture(script_path, args)
        if error:
            return {"ok": False, "stdout": stdout, "error": error}
        return {"ok": True, "stdout": stdout, "result": result}

    def _exec_with_capture(self, script_path: Path, args: Dict[str, Any]) -> Tuple[str, Any, str]:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        result: Any = {}

        try:
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                globals_dict = runpy.run_path(str(script_path), init_globals={"ARGS": args})
                main_fn = globals_dict.get("main")
                if callable(main_fn):
                    result = main_fn(args)
                elif "RESULT" in globals_dict:
                    result = globals_dict.get("RESULT")
        except Exception:
            error = traceback.format_exc()
            stdout = stdout_buffer.getvalue() + stderr_buffer.getvalue()
            return stdout, None, error

        stdout = stdout_buffer.getvalue() + stderr_buffer.getvalue()
        return stdout, result, ""

    def _exec_inline(self, python_code: str, args: Dict[str, Any]) -> Tuple[str, Any, str]:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        globals_dict: Dict[str, Any] = {"ARGS": args}

        try:
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                exec(python_code, globals_dict)
        except Exception:
            error = traceback.format_exc()
            stdout = stdout_buffer.getvalue() + stderr_buffer.getvalue()
            return stdout, None, error

        result = globals_dict.get("RESULT", {})
        stdout = stdout_buffer.getvalue() + stderr_buffer.getvalue()
        return stdout, result, ""



