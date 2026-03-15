Bundled UnrealMCPHub for UnrealCopilot

This folder contains a ready-to-run Windows build of UnrealMCPHub.

Files
- Win64\unreal-mcphub.exe

Recommended usage from the UnrealCopilot plugin root
- .\Tools\UnrealMCPHub\Win64\unreal-mcphub.exe setup
- .\Tools\UnrealMCPHub\Win64\unreal-mcphub.exe launch --wait-seconds 30
- .\Tools\UnrealMCPHub\Win64\unreal-mcphub.exe sync-mcphub

Important
- Enable "Auto Start MCP Server" in Project Settings -> Plugins -> Unreal Copilot for the active MCP when possible.
- If auto-start is disabled, UnrealMCPHub can launch the editor but the MCP endpoint may stay offline until it is started manually inside the editor.
- unreal-mcphub.exe is a single-file distribution and links MCPHub directly as a Rust library.
- Standalone project and release notes: https://github.com/syan2018/UnrealMCPHub
