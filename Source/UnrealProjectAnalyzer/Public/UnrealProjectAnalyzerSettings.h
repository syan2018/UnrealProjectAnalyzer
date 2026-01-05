// Copyright Unreal Project Analyzer Team. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "UnrealProjectAnalyzerSettings.generated.h"

UENUM()
enum class EUnrealAnalyzerMcpTransport : uint8
{
	Stdio UMETA(DisplayName = "stdio (Cursor 默认)"),
	Http UMETA(DisplayName = "http (Streamable HTTP)"),
	Sse UMETA(DisplayName = "sse (Server-Sent Events)"),
};

/**
 * UnrealProjectAnalyzer settings (Editor per-project).
 *
 * 目标：
 * - 允许用户在 UE 内配置 “uv + MCP Server” 启动参数
 * - 不要求修改 UE 自带 Python 环境：MCP Server 始终作为外部进程运行
 */
UCLASS(Config=EditorPerProjectUserSettings, DefaultConfig)
class UUnrealProjectAnalyzerSettings : public UObject
{
	GENERATED_BODY()

public:
	/** 是否在 Editor 启动后自动拉起 MCP Server（仅当 transport != stdio） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Launcher")
	bool bAutoStartMcpServer = false;

	/** uv 可执行文件路径；为空则使用系统 PATH 中的 `uv` */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Launcher")
	FString UvExecutable = TEXT("uv");

	/** MCP Server 的工作目录（默认：插件根目录，pyproject.toml 所在位置） */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Launcher")
	FString McpServerDirectory = TEXT("");

	/** 是否将 MCP Server 的输出打印到 UE Output Log */
	UPROPERTY(EditAnywhere, Config, Category="MCP|Launcher")
	bool bCaptureServerOutput = true;

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
};

