// Copyright Unreal Project Analyzer Team. All Rights Reserved.

#include "UnrealProjectAnalyzerMcpLauncher.h"

#include "UnrealProjectAnalyzerSettings.h"

#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "Misc/FeedbackContext.h"

// 定义专用日志类别
DEFINE_LOG_CATEGORY_STATIC(LogMcpServer, Log, All);

namespace
{
	/**
	 * 规范化路径：转换为绝对路径 + 修正斜杠方向
	 * 这对于 CreateProc 传递参数给外部进程至关重要
	 */
	static FString NormalizePath(const FString& InPath)
	{
		FString P = InPath;
		// 转换为绝对路径（避免相对路径在子进程中解析失败）
		P = FPaths::ConvertRelativePathToFull(P);
		FPaths::NormalizeDirectoryName(P);
		return P;
	}
}

FUnrealProjectAnalyzerMcpLauncher::~FUnrealProjectAnalyzerMcpLauncher()
{
	Stop();
}

FString FUnrealProjectAnalyzerMcpLauncher::GetDefaultMcpServerDir()
{
	// uv project lives at plugin root (pyproject.toml at root), so run from <PluginDir>
	TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("UnrealProjectAnalyzer"));
	if (Plugin.IsValid())
	{
		return NormalizePath(Plugin->GetBaseDir());
	}
	return TEXT("");
}

FString FUnrealProjectAnalyzerMcpLauncher::GetDefaultEngineSourceDir()
{
	// 尝试获取引擎源码目录
	FString EngineSourceDir = FPaths::EngineSourceDir();
	if (FPaths::DirectoryExists(EngineSourceDir))
	{
		return NormalizePath(EngineSourceDir);
	}
	// 回退：尝试 Engine/Source 相对路径
	FString EnginePath = FPaths::EngineDir();
	FString SourcePath = FPaths::Combine(EnginePath, TEXT("Source"));
	if (FPaths::DirectoryExists(SourcePath))
	{
		return NormalizePath(SourcePath);
	}
	return TEXT("");
}

FString FUnrealProjectAnalyzerMcpLauncher::Quote(const FString& S)
{
	// Minimal quoting for CreateProc command line.
	if (S.Contains(TEXT(" ")) || S.Contains(TEXT("\t")) || S.Contains(TEXT("\"")))
	{
		FString Escaped = S;
		Escaped.ReplaceInline(TEXT("\""), TEXT("\\\""));
		return FString::Printf(TEXT("\"%s\""), *Escaped);
	}
	return S;
}

FString FUnrealProjectAnalyzerMcpLauncher::TransportToArg(const UUnrealProjectAnalyzerSettings& Settings)
{
	switch (Settings.Transport)
	{
	case EUnrealAnalyzerMcpTransport::Stdio:
		return TEXT("stdio");
	case EUnrealAnalyzerMcpTransport::Sse:
		return TEXT("sse");
	case EUnrealAnalyzerMcpTransport::Http:
	default:
		return TEXT("http");
	}
}

bool FUnrealProjectAnalyzerMcpLauncher::Start(const UUnrealProjectAnalyzerSettings& Settings)
{
	if (IsRunning())
	{
		return true;
	}

	const FString UvExe = Settings.UvExecutable.IsEmpty() ? TEXT("uv") : Settings.UvExecutable;

	FString ServerDir = Settings.McpServerDirectory;
	if (ServerDir.IsEmpty())
	{
		ServerDir = GetDefaultMcpServerDir();
	}
	ServerDir = NormalizePath(ServerDir);

	// Default cpp source path: <Project>/Source
	FString CppSource = Settings.CppSourcePath;
	if (CppSource.IsEmpty())
	{
		CppSource = FPaths::Combine(FPaths::ProjectDir(), TEXT("Source"));
	}
	CppSource = NormalizePath(CppSource);

	// Unreal Engine source path（用于分析引擎类）
	FString EngineSource = Settings.UnrealEngineSourcePath;
	if (EngineSource.IsEmpty())
	{
		EngineSource = GetDefaultEngineSourceDir();
	}
	else
	{
		EngineSource = NormalizePath(EngineSource);
	}

	const FString Transport = TransportToArg(Settings);
	McpUrl = TEXT("");
	if (Transport == TEXT("http"))
	{
		McpUrl = FString::Printf(TEXT("http://%s:%d%s"), *Settings.McpHost, Settings.McpPort, *Settings.McpPath);
	}
	else if (Transport == TEXT("sse"))
	{
		McpUrl = FString::Printf(TEXT("http://%s:%d"), *Settings.McpHost, Settings.McpPort);
	}

	// Build command line:
	// uv run --directory <ServerDir> -- unreal-analyzer --transport http ...
	FString Args;
	Args += TEXT("run");
	if (!ServerDir.IsEmpty())
	{
		Args += TEXT(" --directory ");
		Args += Quote(ServerDir);
	}
	Args += TEXT(" -- unreal-analyzer ");  // `--` 分隔 uv 参数和脚本名
	Args += TEXT("--transport ");
	Args += Transport;

	if (Transport != TEXT("stdio"))
	{
		Args += TEXT(" --mcp-host ");
		Args += Quote(Settings.McpHost);
		Args += TEXT(" --mcp-port ");
		Args += FString::FromInt(Settings.McpPort);

		if (Transport == TEXT("http"))
		{
			Args += TEXT(" --mcp-path ");
			Args += Quote(Settings.McpPath);
		}
	}

	Args += TEXT(" --cpp-source-path ");
	Args += Quote(CppSource);

	// 添加引擎源码路径（如果存在）
	if (!EngineSource.IsEmpty())
	{
		Args += TEXT(" --unreal-engine-path ");
		Args += Quote(EngineSource);
	}

	Args += TEXT(" --ue-plugin-host ");
	Args += Quote(Settings.UePluginHost);
	Args += TEXT(" --ue-plugin-port ");
	Args += FString::FromInt(Settings.UePluginPort);

	if (!Settings.ExtraArgs.IsEmpty())
	{
		Args += TEXT(" ");
		Args += Settings.ExtraArgs;
	}

	LastCommandLine = FString::Printf(TEXT("%s %s"), *UvExe, *Args);

	// 是否捕获输出
	bCaptureOutput = Settings.bCaptureServerOutput;

	// 如果需要捕获输出，创建管道
	if (bCaptureOutput)
	{
		FPlatformProcess::CreatePipe(ReadPipe, WritePipe);
	}

	// CreateProc 参数
	// 注意：bLaunchDetached=false 且传入 WritePipe 才能正确捕获输出
	const bool bLaunchDetached = !bCaptureOutput;  // 捕获输出时不能 detach
	const bool bLaunchHidden = true;
	const bool bLaunchReallyHidden = true;

	ProcHandle = FPlatformProcess::CreateProc(
		*UvExe,
		*Args,
		bLaunchDetached,
		bLaunchHidden,
		bLaunchReallyHidden,
		&ProcId,
		0,
		nullptr,
		WritePipe,  // 重定向 stdout/stderr 到管道
		nullptr
	);

	if (!ProcHandle.IsValid())
	{
		ProcId = 0;
		// 清理管道
		if (ReadPipe)
		{
			FPlatformProcess::ClosePipe(ReadPipe, WritePipe);
			ReadPipe = nullptr;
			WritePipe = nullptr;
		}
		return false;
	}

	UE_LOG(LogMcpServer, Log, TEXT("MCP Server process started (PID: %u)"), ProcId);
	return true;
}

void FUnrealProjectAnalyzerMcpLauncher::Stop()
{
	// 读取剩余输出
	if (bCaptureOutput && ReadPipe)
	{
		ReadPipeOutput();
	}

	if (IsRunning())
	{
		UE_LOG(LogMcpServer, Log, TEXT("Stopping MCP Server (PID: %u)..."), ProcId);
		FPlatformProcess::TerminateProc(ProcHandle, true);
	}

	if (ProcHandle.IsValid())
	{
		FPlatformProcess::CloseProc(ProcHandle);
		ProcHandle.Reset();
	}

	// 清理管道
	if (ReadPipe)
	{
		FPlatformProcess::ClosePipe(ReadPipe, WritePipe);
		ReadPipe = nullptr;
		WritePipe = nullptr;
	}

	ProcId = 0;
	LineBuffer.Empty();
}

bool FUnrealProjectAnalyzerMcpLauncher::IsRunning() const
{
	return ProcHandle.IsValid() && FPlatformProcess::IsProcRunning(ProcHandle);
}

void FUnrealProjectAnalyzerMcpLauncher::Tick()
{
	if (!bCaptureOutput || !ReadPipe)
	{
		return;
	}

	// 检查进程是否还在运行
	if (!IsRunning())
	{
		// 进程结束，读取最后的输出
		ReadPipeOutput();
		return;
	}

	// 读取管道输出
	ReadPipeOutput();
}

void FUnrealProjectAnalyzerMcpLauncher::ReadPipeOutput()
{
	if (!ReadPipe)
	{
		return;
	}

	FString Output = FPlatformProcess::ReadPipe(ReadPipe);
	if (Output.IsEmpty())
	{
		return;
	}

	// 将新输出添加到行缓冲
	LineBuffer += Output;

	// 按行处理输出
	FString Line;
	while (LineBuffer.Split(TEXT("\n"), &Line, &LineBuffer))
	{
		// 去除行尾的 \r（Windows 换行）
		Line.TrimEndInline();

		if (Line.IsEmpty())
		{
			continue;
		}

		// 根据内容选择日志级别
		if (Line.Contains(TEXT("ERROR")) || Line.Contains(TEXT("Error")))
		{
			UE_LOG(LogMcpServer, Error, TEXT("%s"), *Line);
		}
		else if (Line.Contains(TEXT("WARNING")) || Line.Contains(TEXT("Warning")))
		{
			UE_LOG(LogMcpServer, Warning, TEXT("%s"), *Line);
		}
		else
		{
			UE_LOG(LogMcpServer, Log, TEXT("%s"), *Line);
		}
	}
}

