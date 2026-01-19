// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Bridge/McpServerSubsystem.h"
#include "Settings/UnrealCopilotSettings.h"

#include "Interfaces/IPluginManager.h"
#include "IPythonScriptPlugin.h"
#include "Misc/Paths.h"

// Define logging category
DEFINE_LOG_CATEGORY_STATIC(LogMcpServerSubsystem, Log, All);

void UMcpServerSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    UE_LOG(LogMcpServerSubsystem, Log, TEXT("UnrealCopilot MCP subsystem initialized"));

    // Check if Python is available
    if (!IsPythonAvailable())
    {
        UE_LOG(LogMcpServerSubsystem, Warning, TEXT("Python is not available. UnrealCopilot will not work."));
        return;
    }

    // Wait for Python to be initialized, then set up the bridge
#if ENGINE_MINOR_VERSION >= 7
    if (IPythonScriptPlugin::Get()->IsPythonInitialized())
    {
        InitializePythonBridge();
    }
    else
    {
        IPythonScriptPlugin::Get()->OnPythonInitialized().AddUObject(this, &UMcpServerSubsystem::InitializePythonBridge);
    }
#else
    // For older engine versions, we need to use the editor initialized delegate
    FEditorDelegates::OnEditorInitialized.AddLambda([this](double)
    {
        InitializePythonBridge();
    });
#endif

    // Auto-start if enabled in settings
    const UUnrealCopilotSettings* Settings = GetDefault<UUnrealCopilotSettings>();
    if (Settings && Settings->bAutoStartMcpServer)
    {
        StartMcpServer();
    }
}

void UMcpServerSubsystem::Deinitialize()
{
    StopMcpServer();
    Super::Deinitialize();
}

void UMcpServerSubsystem::StartMcpServer()
{
    if (!IsPythonAvailable())
    {
        UE_LOG(LogMcpServerSubsystem, Error, TEXT("Cannot start MCP server: Python is not available"));
        return;
    }

    if (bMcpServerStarting)
    {
        UE_LOG(LogMcpServerSubsystem, Warning, TEXT("MCP server is already starting"));
        return;
    }

    if (bMcpServerStopRequested)
    {
        UE_LOG(LogMcpServerSubsystem, Warning, TEXT("MCP server stop is still in progress."));
        return;
    }

    if (bMcpServerRunning)
    {
        UE_LOG(LogMcpServerSubsystem, Warning, TEXT("MCP server is already running"));
        return;
    }

    if (!bPythonBridgeInitialized)
    {
        UE_LOG(LogMcpServerSubsystem, Warning, TEXT("Python bridge not initialized. Attempting to initialize..."));
        InitializePythonBridge();

        if (!bPythonBridgeInitialized)
        {
            UE_LOG(LogMcpServerSubsystem, Error, TEXT("Failed to initialize Python bridge. Cannot start MCP server."));
            return;
        }
    }

    // Get settings
    const UUnrealCopilotSettings* Settings = GetDefault<UUnrealCopilotSettings>();
    if (!Settings)
    {
        UE_LOG(LogMcpServerSubsystem, Error, TEXT("Failed to get UnrealCopilot settings"));
        return;
    }

    // Build Python command to start the server
    FString TransportStr;
    switch (Settings->Transport)
    {
    case EUnrealAnalyzerMcpTransport::Stdio:
        TransportStr = TEXT("stdio");
        break;
    case EUnrealAnalyzerMcpTransport::Sse:
        TransportStr = TEXT("sse");
        break;
    case EUnrealAnalyzerMcpTransport::Http:
    default:
        TransportStr = TEXT("http");
        break;
    }

    // Prepare paths
    FString CppSourcePath = Settings->CppSourcePath;
    if (CppSourcePath.IsEmpty())
    {
        CppSourcePath = FPaths::Combine(FPaths::ProjectDir(), TEXT("Source"));
    }

    FString EngineSourcePath = Settings->UnrealEngineSourcePath;
    if (EngineSourcePath.IsEmpty())
    {
        EngineSourcePath = FPaths::EngineSourceDir();
    }

    // Execute Python command to start the server
    FString PythonCommand = FString::Printf(
        TEXT("import init_analyzer; init_analyzer.start_analyzer_server("
             "transport='%s', host='%s', port=%d, path='%s', "
             "cpp_source_path='%s', unreal_engine_path='%s')"),
        *TransportStr,
        *Settings->McpHost,
        Settings->McpPort,
        *Settings->McpPath,
        *CppSourcePath,
        *EngineSourcePath
    );

    UE_LOG(LogMcpServerSubsystem, Log, TEXT("Starting MCP server..."));
    UE_LOG(LogMcpServerSubsystem, Log, TEXT("Transport: %s, Host: %s, Port: %d"),
        *TransportStr, *Settings->McpHost, Settings->McpPort);

    IPythonScriptPlugin::Get()->ExecPythonCommand(*PythonCommand);

    // Track state for UI feedback (final states are driven by Python notifications).
    LastTransport = Settings->Transport;
    LastMcpHost = Settings->McpHost;
    LastMcpPort = Settings->McpPort;
    StartRequestedAtSeconds = FPlatformTime::Seconds();

    if (Settings->Transport == EUnrealAnalyzerMcpTransport::Stdio)
    {
        bMcpServerRunning = true;
        bMcpServerStarting = false;
    }
    else
    {
        bMcpServerRunning = false;
        bMcpServerStarting = true;
    }

    UE_LOG(LogMcpServerSubsystem, Log, TEXT("MCP server start requested (check Python log for result)"));
}

void UMcpServerSubsystem::StopMcpServer()
{
    if (!bMcpServerRunning && !bMcpServerStarting && !bMcpServerStopRequested)
    {
        return;
    }

    UE_LOG(LogMcpServerSubsystem, Log, TEXT("Stopping MCP server..."));

    // Execute Python command to stop the server
    FString PythonCommand = TEXT("import init_analyzer; init_analyzer.stop_analyzer_server()");
    IPythonScriptPlugin::Get()->ExecPythonCommand(*PythonCommand);

    bMcpServerStarting = false;
    bMcpServerRunning = false;
    bMcpServerStopRequested = true;
    StopRequestedAtSeconds = FPlatformTime::Seconds();

    UE_LOG(LogMcpServerSubsystem, Log, TEXT("MCP server stop requested"));
}

bool UMcpServerSubsystem::IsMcpServerRunning() const
{
    return bMcpServerRunning;
}

bool UMcpServerSubsystem::IsMcpServerStarting() const
{
    return bMcpServerStarting;
}

bool UMcpServerSubsystem::IsMcpServerStopping() const
{
    return bMcpServerStopRequested;
}

UMcpServerSubsystem* UMcpServerSubsystem::Get()
{
    return GEditor ? GEditor->GetEditorSubsystem<UMcpServerSubsystem>() : nullptr;
}

bool UMcpServerSubsystem::IsPythonAvailable() const
{
#if ENGINE_MINOR_VERSION >= 7
    return IPythonScriptPlugin::Get() != nullptr;
#else
    // For older engine versions, check if the plugin is available
    return FModuleManager::Get().IsModuleLoaded("PythonScriptPlugin");
#endif
}

void UMcpServerSubsystem::InitializePythonBridge()
{
    if (!IsPythonAvailable())
    {
        UE_LOG(LogMcpServerSubsystem, Error, TEXT("Python is not available"));
        return;
    }

    if (bPythonBridgeInitialized)
    {
        return;
    }

    UE_LOG(LogMcpServerSubsystem, Log, TEXT("Initializing Python bridge..."));

    // Get the plugin directory
    FString PluginDir = FPaths::ConvertRelativePathToFull(
        FPaths::Combine(FPaths::ProjectPluginsDir(), TEXT("UnrealCopilot"))
    );

    // Check if we're in a development build (plugin might be in a different location)
    if (!FPaths::DirectoryExists(PluginDir))
    {
        // Try to find the plugin via the plugin manager
        if (IPluginManager::Get().FindPlugin(TEXT("UnrealCopilot")))
        {
            PluginDir = IPluginManager::Get().FindPlugin(TEXT("UnrealCopilot"))->GetBaseDir();
        }
        else
        {
            UE_LOG(LogMcpServerSubsystem, Error, TEXT("Failed to locate UnrealCopilot plugin directory"));
            return;
        }
    }

    // Add the Content/Python directory to sys.path
    FString PythonInitScript = FPaths::Combine(PluginDir, TEXT("Content/Python"));

    // Execute the initialization script
    FString PythonCommand = FString::Printf(
        TEXT("import sys; sys.path.insert(0, r'%s'); import init_analyzer"),
        *PythonInitScript
    );

    IPythonScriptPlugin::Get()->ExecPythonCommand(*PythonCommand);

    bPythonBridgeInitialized = true;

    UE_LOG(LogMcpServerSubsystem, Log, TEXT("Python bridge initialized"));
}

void UMcpServerSubsystem::NotifyMcpServerStarting(EUnrealAnalyzerMcpTransport Transport, const FString& Host, int32 Port, const FString& Path)
{
    LastTransport = Transport;
    LastMcpHost = Host;
    LastMcpPort = Port;
    StartRequestedAtSeconds = FPlatformTime::Seconds();

    bMcpServerStarting = (Transport != EUnrealAnalyzerMcpTransport::Stdio);
    bMcpServerRunning = (Transport == EUnrealAnalyzerMcpTransport::Stdio);
    bMcpServerStopRequested = false;

    UE_LOG(LogMcpServerSubsystem, Log, TEXT("MCP server starting (%s://%s:%d%s)"),
        Transport == EUnrealAnalyzerMcpTransport::Http ? TEXT("http") :
        (Transport == EUnrealAnalyzerMcpTransport::Sse ? TEXT("sse") : TEXT("stdio")),
        *Host, Port, *Path);
}

void UMcpServerSubsystem::NotifyMcpServerRunning()
{
    bMcpServerStarting = false;
    bMcpServerRunning = true;
    bMcpServerStopRequested = false;
    UE_LOG(LogMcpServerSubsystem, Log, TEXT("MCP server is now running on %s:%d"), *LastMcpHost, LastMcpPort);
}

void UMcpServerSubsystem::NotifyMcpServerStopped()
{
    bMcpServerStarting = false;
    bMcpServerRunning = false;
    bMcpServerStopRequested = false;
    StopRequestedAtSeconds = FPlatformTime::Seconds();
    UE_LOG(LogMcpServerSubsystem, Log, TEXT("MCP server stopped"));
}

void UMcpServerSubsystem::NotifyMcpServerStartFailed(const FString& Error)
{
    bMcpServerStarting = false;
    bMcpServerRunning = false;
    bMcpServerStopRequested = false;
    UE_LOG(LogMcpServerSubsystem, Error, TEXT("MCP server start failed: %s"), *Error);
}

