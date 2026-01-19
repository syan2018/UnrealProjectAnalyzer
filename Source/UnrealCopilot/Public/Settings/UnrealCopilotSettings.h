// Copyright Unreal Copilot Team. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "UnrealCopilotSettings.generated.h"

UENUM()
enum class EUnrealAnalyzerMcpTransport : uint8
{
	Stdio UMETA(DisplayName = "stdio (Cursor 默认)"),
	Http UMETA(DisplayName = "http (Streamable HTTP)"),
	Sse UMETA(DisplayName = "sse (Server-Sent Events)"),
};

/**
 * UnrealCopilot settings (Editor per-project).
 *
 * 运行方式：
 * - MCP Server 在 UE 内置 Python 环境中运行（类似 UnrealRemoteMCP）
 * - 依赖通过 uv sync 自动管理到 Content/Python/.venv（启动时自动加入 sys.path）
 * - Subsystem 负责管理 MCP Server 的生命周期
 */
UCLASS(Config=EditorPerProjectUserSettings, DefaultConfig)
class UUnrealCopilotSettings : public UObject
{
	GENERATED_BODY()

public:
	/** 是否在 Editor 启动后自动启动 MCP Server（仅在 UE 进程内运行） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Launcher")
	bool bAutoStartMcpServer = false;

	/** MCP transport：stdio/http/sse */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Transport")
	EUnrealAnalyzerMcpTransport Transport = EUnrealAnalyzerMcpTransport::Http;

	/** HTTP/SSE 监听 Host（安全默认：127.0.0.1） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Transport", meta=(EditCondition="Transport!=EUnrealAnalyzerMcpTransport::Stdio"))
	FString McpHost = TEXT("127.0.0.1");

	/** HTTP/SSE 监听端口（默认使用不常用端口避免冲突） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Transport", meta=(EditCondition="Transport!=EUnrealAnalyzerMcpTransport::Stdio", ClampMin="1", ClampMax="65535"))
	int32 McpPort = 19840;

	/** HTTP MCP path（例如 /mcp） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Transport", meta=(EditCondition="Transport==EUnrealAnalyzerMcpTransport::Http"))
	FString McpPath = TEXT("/mcp");

	/** 传给 unreal-analyzer 的项目 C++ 源码路径（默认：<Project>/Source） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Analyzer")
	FString CppSourcePath = TEXT("");

	/** Unreal Engine 源码路径（默认：自动检测引擎安装目录/Source）；用于分析引擎类 */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Analyzer")
	FString UnrealEngineSourcePath = TEXT("");

	/** UE 插件 HTTP API（MCP Server 会调用回 Editor 内 API） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Analyzer")
	FString UePluginHost = TEXT("127.0.0.1");

	UPROPERTY(EditAnywhere, Config, Category="MCP|Analyzer", meta=(ClampMin="1", ClampMax="65535"))
	int32 UePluginPort = 8080;

	/** 额外传给 unreal-analyzer 的参数（高级） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Advanced")
	FString ExtraArgs = TEXT("");

	// ============================================================================
	// Launcher Settings (用于外部进程启动方式)
	// ============================================================================

	/** uv 可执行文件路径（默认：系统 PATH 中的 uv） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Launcher")
	FString UvExecutable = TEXT("");

	/** MCP Server 目录（默认：插件根目录） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Launcher")
	FString McpServerDirectory = TEXT("");

	/** 是否捕获服务器输出到日志 */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Launcher")
	bool bCaptureServerOutput = false;
};



