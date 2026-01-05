// Copyright Unreal Project Analyzer Team. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

class UUnrealProjectAnalyzerSettings;

/**
 * Manage external MCP Server process (uv run ...).
 *
 * 设计目标：
 * - UE 内一键启动/停止 MCP Server
 * - 通过 uv 管理 Python 依赖，不污染 Unreal 自带 Python
 * - 默认只监听 127.0.0.1，避免对局域网暴露
 * - 支持捕获子进程 stdout/stderr 输出到 UE Log
 */
class FUnrealProjectAnalyzerMcpLauncher
{
public:
	~FUnrealProjectAnalyzerMcpLauncher();

	bool Start(const UUnrealProjectAnalyzerSettings& Settings);
	void Stop();
	bool IsRunning() const;

	/** 每帧调用，读取子进程输出并打印到 UE Log */
	void Tick();

	FString GetMcpUrl() const { return McpUrl; }
	FString GetLastCommandLine() const { return LastCommandLine; }

private:
	static FString GetDefaultMcpServerDir();
	static FString GetDefaultEngineSourceDir();
	static FString Quote(const FString& S);
	static FString TransportToArg(const UUnrealProjectAnalyzerSettings& Settings);

	/** 读取管道中的所有可用输出并打印到日志 */
	void ReadPipeOutput();

private:
	// mutable 允许在 const 方法中传递给 IsProcRunning（它需要非 const 引用）
	mutable FProcHandle ProcHandle;
	uint32 ProcId = 0;
	FString McpUrl;
	FString LastCommandLine;

	// 用于捕获子进程 stdout/stderr 的管道
	void* ReadPipe = nullptr;
	void* WritePipe = nullptr;
	bool bCaptureOutput = false;

	// 累积的行缓冲（处理不完整行）
	FString LineBuffer;
};

