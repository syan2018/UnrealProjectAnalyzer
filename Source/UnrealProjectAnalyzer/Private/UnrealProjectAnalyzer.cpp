// Copyright Unreal Project Analyzer Team. All Rights Reserved.

#include "UnrealProjectAnalyzer.h"
#include "HttpServerModule.h"
#include "IHttpRouter.h"
#include "HttpPath.h"
#include "IPythonScriptPlugin.h"
#include "Misc/Paths.h"

#include "UnrealAnalyzerHttpRoutes.h"
#include "UnrealProjectAnalyzerMcpLauncher.h"
#include "UnrealProjectAnalyzerSettings.h"

#include "Interfaces/IPluginManager.h"
#include "ToolMenus.h"
#include "LevelEditor.h"
#include "Framework/MultiBox/MultiBoxBuilder.h"
#include "Framework/Notifications/NotificationManager.h"
#include "Widgets/Notifications/SNotificationList.h"
#include "Misc/MessageDialog.h"
#include "HAL/PlatformApplicationMisc.h"
#include "ISettingsModule.h"

#define LOCTEXT_NAMESPACE "FUnrealProjectAnalyzerModule"

void FUnrealProjectAnalyzerModule::StartupModule()
{
    UE_LOG(LogTemp, Log, TEXT("UnrealProjectAnalyzer: Starting module..."));

    McpLauncher = new FUnrealProjectAnalyzerMcpLauncher();
    
    // Initialize HTTP server
    InitializeHttpServer();
    
    // Initialize Python bridge
    InitializePythonBridge();

    // Editor integration
    RegisterSettings();
    RegisterMenus();

    // Optional auto-start (only for HTTP/SSE transports; stdio is typically Cursor-managed)
    const UUnrealProjectAnalyzerSettings* Settings = GetDefault<UUnrealProjectAnalyzerSettings>();
    if (Settings && Settings->bAutoStartMcpServer && Settings->Transport != EUnrealAnalyzerMcpTransport::Stdio)
    {
        StartMcpServer();
    }
    
    UE_LOG(LogTemp, Log, TEXT("UnrealProjectAnalyzer: Module started successfully. HTTP API available at port %d"), HttpPort);
}

void FUnrealProjectAnalyzerModule::ShutdownModule()
{
    UE_LOG(LogTemp, Log, TEXT("UnrealProjectAnalyzer: Shutting down module..."));

    UnregisterMenus();
    UnregisterSettings();

    StopMcpServer();
    delete McpLauncher;
    McpLauncher = nullptr;
    
    ShutdownPythonBridge();
    ShutdownHttpServer();
    
    UE_LOG(LogTemp, Log, TEXT("UnrealProjectAnalyzer: Module shutdown complete."));
}

FUnrealProjectAnalyzerModule& FUnrealProjectAnalyzerModule::Get()
{
    return FModuleManager::LoadModuleChecked<FUnrealProjectAnalyzerModule>("UnrealProjectAnalyzer");
}

bool FUnrealProjectAnalyzerModule::IsAvailable()
{
    return FModuleManager::Get().IsModuleLoaded("UnrealProjectAnalyzer");
}

void FUnrealProjectAnalyzerModule::InitializeHttpServer()
{
    // Get HTTP server module
    FHttpServerModule& HttpServerModule = FHttpServerModule::Get();
    
    // Start listeners on specified port
    HttpServerModule.StartAllListeners();
    
    // Get router for our port
    HttpRouter = HttpServerModule.GetHttpRouter(HttpPort);
    
    if (HttpRouter.IsValid())
    {
        // Register all routes
        RegisterRoutes(HttpRouter);
        UE_LOG(LogTemp, Log, TEXT("UnrealProjectAnalyzer: HTTP server initialized on port %d"), HttpPort);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealProjectAnalyzer: Failed to initialize HTTP server on port %d"), HttpPort);
    }
}

void FUnrealProjectAnalyzerModule::ShutdownHttpServer()
{
    if (HttpRouter.IsValid())
    {
        // Routes will be automatically cleaned up
        HttpRouter.Reset();
    }
}

void FUnrealProjectAnalyzerModule::InitializePythonBridge()
{
    // Check if Python plugin is available
    IPythonScriptPlugin* PythonPlugin = FModuleManager::GetModulePtr<IPythonScriptPlugin>("PythonScriptPlugin");
    
    if (!PythonPlugin)
    {
        UE_LOG(LogTemp, Warning, TEXT("UnrealProjectAnalyzer: PythonScriptPlugin not available. Python bridge disabled."));
        return;
    }
    
    // Get the path to our Python bridge script (do NOT hardcode ProjectPluginsDir / plugin folder name)
    TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("UnrealProjectAnalyzer"));
    const FString PluginDir = Plugin.IsValid() ? Plugin->GetBaseDir() : FPaths::ProjectPluginsDir();
    FString BridgeScriptPath = FPaths::Combine(PluginDir, TEXT("Content/Python/bridge_server.py"));
    
    // Check if script exists
    if (!FPaths::FileExists(BridgeScriptPath))
    {
        UE_LOG(LogTemp, Warning, TEXT("UnrealProjectAnalyzer: Python bridge script not found at %s"), *BridgeScriptPath);
        return;
    }
    
    // Execute the bridge script
    // Note: In production, we'd want more robust error handling
    // Windows paths contain backslashes; escape them for Python string literal.
    BridgeScriptPath.ReplaceInline(TEXT("\\"), TEXT("\\\\"));
    FString PythonCommand = FString::Printf(TEXT("exec(open(r'%s').read())"), *BridgeScriptPath);
    
    // Execute the Python script (best-effort)
    PythonPlugin->ExecPythonCommand(*PythonCommand);
    
    bPythonBridgeInitialized = true;
    UE_LOG(LogTemp, Log, TEXT("UnrealProjectAnalyzer: Python bridge initialized."));
}

void FUnrealProjectAnalyzerModule::ShutdownPythonBridge()
{
    if (bPythonBridgeInitialized)
    {
        // TODO: Send shutdown signal to Python bridge
        bPythonBridgeInitialized = false;
    }
}

void FUnrealProjectAnalyzerModule::RegisterRoutes(TSharedPtr<IHttpRouter> Router)
{
    if (!Router.IsValid())
    {
        return;
    }
    
    // Health check endpoint
    Router->BindRoute(
        FHttpPath(TEXT("/health")),
        EHttpServerRequestVerbs::VERB_GET,
        [](const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
        {
            TUniquePtr<FHttpServerResponse> Response = FHttpServerResponse::Create(
                TEXT("{\"status\": \"ok\", \"service\": \"UnrealProjectAnalyzer\"}"),
                TEXT("application/json")
            );
            OnComplete(MoveTemp(Response));
            return true;
        }
    );

    // Register analyzer API routes.
    // NOTE: For any parameter that contains "/Game/...", we use query params (e.g. ?bp_path=...),
    // to avoid router path-segment matching issues.
    UnrealAnalyzerHttpRoutes::Register(Router);
    
    UE_LOG(LogTemp, Log, TEXT("UnrealProjectAnalyzer: Routes registered."));
}

// ============================================================================
// Settings + Menus
// ============================================================================

void FUnrealProjectAnalyzerModule::RegisterSettings()
{
    ISettingsModule* SettingsModule = FModuleManager::GetModulePtr<ISettingsModule>("Settings");
    if (!SettingsModule)
    {
        return;
    }

    SettingsModule->RegisterSettings(
        "Project",
        "Plugins",
        "UnrealProjectAnalyzer",
        LOCTEXT("UnrealProjectAnalyzerSettingsName", "Unreal Project Analyzer"),
        LOCTEXT("UnrealProjectAnalyzerSettingsDesc", "Settings for Unreal Project Analyzer (MCP launcher, transport, and analyzer paths)."),
        GetMutableDefault<UUnrealProjectAnalyzerSettings>()
    );
}

void FUnrealProjectAnalyzerModule::UnregisterSettings()
{
    ISettingsModule* SettingsModule = FModuleManager::GetModulePtr<ISettingsModule>("Settings");
    if (!SettingsModule)
    {
        return;
    }

    SettingsModule->UnregisterSettings("Project", "Plugins", "UnrealProjectAnalyzer");
}

void FUnrealProjectAnalyzerModule::RegisterMenus()
{
    if (!UToolMenus::IsToolMenusAvailable())
    {
        return;
    }

    UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateLambda([this]()
    {
        FToolMenuOwnerScoped OwnerScoped(this);

        UToolMenu* Menu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar");
        if (!Menu)
        {
            return;
        }

        FToolMenuSection& Section = Menu->FindOrAddSection("UnrealProjectAnalyzer");

        // Start
        Section.AddEntry(FToolMenuEntry::InitToolBarButton(
            "UnrealProjectAnalyzer.StartMcp",
            FUIAction(
                FExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::StartMcpServer),
                FCanExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::CanStartMcpServer)
            ),
            LOCTEXT("StartMcp_Label", "Start MCP"),
            LOCTEXT("StartMcp_Tooltip", "Start MCP Server via uv (HTTP/SSE transport recommended for quick connect)."),
            FSlateIcon()
        ));

        // Stop
        Section.AddEntry(FToolMenuEntry::InitToolBarButton(
            "UnrealProjectAnalyzer.StopMcp",
            FUIAction(
                FExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::StopMcpServer),
                FCanExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::CanStopMcpServer)
            ),
            LOCTEXT("StopMcp_Label", "Stop MCP"),
            LOCTEXT("StopMcp_Tooltip", "Stop MCP Server process."),
            FSlateIcon()
        ));

        // Copy URL
        Section.AddEntry(FToolMenuEntry::InitToolBarButton(
            "UnrealProjectAnalyzer.CopyMcpUrl",
            FUIAction(
                FExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::CopyMcpUrlToClipboard),
                FCanExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::CanStopMcpServer) // running => can copy
            ),
            LOCTEXT("CopyMcpUrl_Label", "Copy MCP URL"),
            LOCTEXT("CopyMcpUrl_Tooltip", "Copy MCP URL to clipboard (HTTP/SSE only)."),
            FSlateIcon()
        ));

        // Settings
        Section.AddEntry(FToolMenuEntry::InitToolBarButton(
            "UnrealProjectAnalyzer.OpenSettings",
            FUIAction(FExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::OpenPluginSettings)),
            LOCTEXT("OpenSettings_Label", "MCP Settings"),
            LOCTEXT("OpenSettings_Tooltip", "Open Unreal Project Analyzer settings."),
            FSlateIcon()
        ));
    }));
}

void FUnrealProjectAnalyzerModule::UnregisterMenus()
{
    if (UToolMenus::IsToolMenusAvailable())
    {
        UToolMenus::UnregisterOwner(this);
    }
}

bool FUnrealProjectAnalyzerModule::CanStartMcpServer() const
{
    return McpLauncher && !McpLauncher->IsRunning();
}

bool FUnrealProjectAnalyzerModule::CanStopMcpServer() const
{
    return McpLauncher && McpLauncher->IsRunning();
}

void FUnrealProjectAnalyzerModule::StartMcpServer()
{
    if (!McpLauncher)
    {
        return;
    }

    const UUnrealProjectAnalyzerSettings* Settings = GetDefault<UUnrealProjectAnalyzerSettings>();
    if (!Settings)
    {
        return;
    }

    const bool bOk = McpLauncher->Start(*Settings);
    if (!bOk)
    {
        const FText Msg = LOCTEXT("McpStartFailed", "Failed to start MCP Server. Please ensure `uv` is installed and configured in settings.");
        FMessageDialog::Open(EAppMsgType::Ok, Msg);
        UE_LOG(LogTemp, Error, TEXT("UnrealProjectAnalyzer: Failed to start MCP server. cmd=%s"), *McpLauncher->GetLastCommandLine());
        return;
    }

    const FString Url = McpLauncher->GetMcpUrl();
    UE_LOG(LogTemp, Log, TEXT("UnrealProjectAnalyzer: MCP server started. %s"), *McpLauncher->GetLastCommandLine());
    if (!Url.IsEmpty())
    {
        UE_LOG(LogTemp, Log, TEXT("UnrealProjectAnalyzer: MCP URL: %s"), *Url);
    }

    FNotificationInfo Info(LOCTEXT("McpStarted", "MCP Server started"));
    Info.ExpireDuration = 3.0f;
    FSlateNotificationManager::Get().AddNotification(Info);
}

void FUnrealProjectAnalyzerModule::StopMcpServer()
{
    if (!McpLauncher)
    {
        return;
    }

    if (McpLauncher->IsRunning())
    {
        McpLauncher->Stop();
        UE_LOG(LogTemp, Log, TEXT("UnrealProjectAnalyzer: MCP server stopped."));

        FNotificationInfo Info(LOCTEXT("McpStopped", "MCP Server stopped"));
        Info.ExpireDuration = 3.0f;
        FSlateNotificationManager::Get().AddNotification(Info);
    }
}

void FUnrealProjectAnalyzerModule::CopyMcpUrlToClipboard() const
{
    if (!McpLauncher || !McpLauncher->IsRunning())
    {
        return;
    }

    const FString Url = McpLauncher->GetMcpUrl();
    if (Url.IsEmpty())
    {
        FNotificationInfo Info(LOCTEXT("McpUrlEmpty", "MCP URL is empty (transport is likely stdio)."));
        Info.ExpireDuration = 3.0f;
        FSlateNotificationManager::Get().AddNotification(Info);
        return;
    }

    FPlatformApplicationMisc::ClipboardCopy(*Url);
    FNotificationInfo Info(LOCTEXT("McpUrlCopied", "MCP URL copied to clipboard"));
    Info.ExpireDuration = 2.0f;
    FSlateNotificationManager::Get().AddNotification(Info);
}

void FUnrealProjectAnalyzerModule::OpenPluginSettings() const
{
    ISettingsModule* SettingsModule = FModuleManager::GetModulePtr<ISettingsModule>("Settings");
    if (SettingsModule)
    {
        SettingsModule->ShowViewer("Project", "Plugins", "UnrealProjectAnalyzer");
    }
}

#undef LOCTEXT_NAMESPACE
    
IMPLEMENT_MODULE(FUnrealProjectAnalyzerModule, UnrealProjectAnalyzer)
