UnrealCopilot (Content/Python)

This folder is designed to run **inside Unreal Editor's embedded Python**.

## Layout

- `unreal_copilot/`: MCP server implementation (FastMCP) + tools
- `../skills/`: Skill 包目录（`SKILL.md` + `scripts/` + 可选 `docs/`）
- `init_analyzer.py`: UE entry point (bridge + start/stop helpers)
- `uv_sync.py`: dependency bootstrapper for UE environment
- `.venv/`: uv-managed virtual environment (created by `uv sync`)

## One-time setup (recommended)

For the first run (or after dependency changes), sync the environment manually:

```powershell
cd <PluginRoot>\Content\Python
uv sync
```

Then open Unreal Editor and use:
`Tools → Unreal Copilot → Start MCP Server`

## Notes

- This project pins Python to **3.11** via `requires-python` in `pyproject.toml`.
- If `uv sync` fails in-editor, run it manually outside the editor and restart Unreal Editor.




