Bundled UnrealMCPHub for UnrealCopilot

This folder contains a ready-to-run Windows build of UnrealMCPHub plus the optional raw MCPHub CLI.

Files
- Win64\unreal-mcphub.exe
- Win64\mcphub.exe

Recommended usage from the UnrealCopilot plugin root
- .\Tools\UnrealMCPHub\Win64\unreal-mcphub.exe setup
- .\Tools\UnrealMCPHub\Win64\unreal-mcphub.exe launch --wait-seconds 30
- .\Tools\UnrealMCPHub\Win64\unreal-mcphub.exe sync-mcphub

Important
- Enable "Auto Start MCP Server" in Project Settings -> Plugins -> Unreal Copilot for the active MCP when possible.
- If auto-start is disabled, UnrealMCPHub can launch the editor but the MCP endpoint may stay offline until it is started manually inside the editor.
- unreal-mcphub.exe now links MCPHub directly as a Rust library. mcphub.exe is kept only for users who want the original generic MCPHub CLI.
- Standalone project and release notes: https://github.com/syan2018/UnrealMCPHub
