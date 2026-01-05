"""
Lyra Starter Game smoke test for Unreal Project Analyzer tools.

Usage (PowerShell):
  $env:CPP_SOURCE_PATH = "D:\\Projects\\Games\\Unreal Projects\\LyraStarterGame\\Source"
  & ".\\.venv\\Scripts\\python.exe" scripts\\lyra_smoke_test.py
"""

import asyncio
import argparse
import os
from pathlib import Path

from unreal_analyzer.config import get_config
from unreal_analyzer.tools import asset, blueprint, cpp, cross_domain


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lyra_smoke_test",
        description="Smoke test for Unreal Project Analyzer tools on LyraStarterGame",
    )
    parser.add_argument(
        "--cpp-source-path",
        default=None,
        help="LyraStarterGame/Source 路径（覆盖 CPP_SOURCE_PATH）",
    )
    parser.add_argument(
        "--ue-plugin-host",
        default=None,
        help="UE 插件 HTTP host（覆盖 UE_PLUGIN_HOST）",
    )
    parser.add_argument(
        "--ue-plugin-port",
        type=int,
        default=None,
        help="UE 插件 HTTP port（覆盖 UE_PLUGIN_PORT）",
    )
    return parser


async def main() -> None:
    args = _build_arg_parser().parse_args()
    if args.cpp_source_path:
        os.environ["CPP_SOURCE_PATH"] = args.cpp_source_path
    if args.ue_plugin_host:
        os.environ["UE_PLUGIN_HOST"] = args.ue_plugin_host
    if args.ue_plugin_port is not None:
        os.environ["UE_PLUGIN_PORT"] = str(args.ue_plugin_port)

    # Source root is expected via env var (CPP_SOURCE_PATH). Fallback keeps the example runnable.
    source_root = Path(os.getenv("CPP_SOURCE_PATH") or r"D:\Projects\Games\Unreal Projects\LyraStarterGame\Source")

    if not source_root.exists():
        raise FileNotFoundError(
            "Lyra Source path not found. Set CPP_SOURCE_PATH to your LyraStarterGame\\Source."
        )

    # Ensure analyzer is initialized (via config/env) for tool wrappers that rely on it.
    # (cpp tools call get_analyzer() internally, which relies on config.cpp_source_paths populated from env)
    _ = get_config()

    print("== C++ tools ==")
    info = await cpp.analyze_cpp_class("ULyraAbilitySystemComponent")
    print("analyze_cpp_class: ULyraAbilitySystemComponent superclasses:", info["superclasses"])

    hierarchy = await cpp.get_cpp_class_hierarchy("ALyraCharacter")
    print("get_cpp_class_hierarchy: root:", hierarchy["class"])
    print("get_cpp_class_hierarchy: direct superclasses:", [h["class"] for h in hierarchy.get("superclasses", [])])
    print("get_cpp_class_hierarchy: interfaces:", hierarchy.get("interfaces", []))

    search = await cpp.search_cpp_code(r"ULyraAbilitySystemComponent\b", "*.h", include_comments=False)
    print("search_cpp_code: ULyraAbilitySystemComponent matches:", search["count"])

    refs = await cpp.find_cpp_references("ULyraAbilitySystemComponent")
    print("find_cpp_references: ULyraAbilitySystemComponent refs:", refs["count"])

    print("\n== UE macro / blueprint exposure tools ==")
    lyra_char_h = source_root / "LyraGame" / "Character" / "LyraCharacter.h"
    patterns = await cpp.detect_ue_patterns(str(lyra_char_h))
    print("detect_ue_patterns:", len(patterns["patterns"]))

    exposure = await cpp.get_cpp_blueprint_exposure(str(lyra_char_h))
    print("get_cpp_blueprint_exposure BlueprintCallable:", exposure["blueprint_callable_functions"])

    print("\n== UE Plugin HTTP tools (optional) ==")
    print("这些工具需要 UE Editor 插件 HTTP API 在线，否则会失败/报错（属于预期）。")
    print("UE Plugin URL:", get_config().ue_plugin_url)

    # We don't hard-fail the smoke test if plugin isn't running.
    try:
        _ = await blueprint.search_blueprints("Lyra*", "")
        print("blueprint.search_blueprints: OK")
    except Exception as e:
        print("blueprint.search_blueprints: SKIPPED (plugin not running?) ->", type(e).__name__)

    try:
        _ = await asset.search_assets("Lyra*", "")
        print("asset.search_assets: OK")
    except Exception as e:
        print("asset.search_assets: SKIPPED (plugin not running?) ->", type(e).__name__)

    # Cross-domain tools are also plugin-backed in this repo state.
    try:
        _ = await cross_domain.find_cpp_class_usage("ULyraAbilitySystemComponent")
        print("cross_domain.find_cpp_class_usage: OK")
    except Exception as e:
        print("cross_domain.find_cpp_class_usage: SKIPPED (plugin not running?) ->", type(e).__name__)


if __name__ == "__main__":
    asyncio.run(main())

