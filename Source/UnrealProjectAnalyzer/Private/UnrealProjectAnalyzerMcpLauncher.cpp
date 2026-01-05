// Copyright Unreal Project Analyzer Team. All Rights Reserved.

#include "UnrealProjectAnalyzerMcpLauncher.h"

#include "UnrealProjectAnalyzerSettings.h"

#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "Misc/FeedbackContext.h"

namespace
{
	static FString NormalizePath(const FString& InPath)
	{
		FString P = InPath;
		FPaths::NormalizeDirectoryName(P);
		return P;
	}
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
		CppSource = NormalizePath(FPaths::Combine(FPaths::ProjectDir(), TEXT("Source")));
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

	// Build:
	// uv run --directory <ServerDir> unreal-analyzer -- --transport http --mcp-host ... --mcp-port ... --mcp-path ...
	//   --cpp-source-path ... --ue-plugin-host ... --ue-plugin-port ...
	FString Args;
	Args += TEXT("run");
	if (!ServerDir.IsEmpty())
	{
		Args += TEXT(" --directory ");
		Args += Quote(ServerDir);
	}
	Args += TEXT(" unreal-analyzer -- ");
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

	// CreateProc parameters
	const bool bLaunchDetached = true;
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
		nullptr,
		nullptr
	);

	if (!ProcHandle.IsValid())
	{
		ProcId = 0;
		return false;
	}

	return true;
}

void FUnrealProjectAnalyzerMcpLauncher::Stop()
{
	if (!IsRunning())
	{
		ProcId = 0;
		ProcHandle.Reset();
		return;
	}

	FPlatformProcess::TerminateProc(ProcHandle, true);
	FPlatformProcess::CloseProc(ProcHandle);
	ProcHandle.Reset();
	ProcId = 0;
}

bool FUnrealProjectAnalyzerMcpLauncher::IsRunning() const
{
	return ProcHandle.IsValid() && FPlatformProcess::IsProcRunning(ProcHandle);
}

