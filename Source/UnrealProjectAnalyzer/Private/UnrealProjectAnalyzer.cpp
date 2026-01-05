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
#include "Styling/AppStyle.h"
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

    // 注册 Ticker 用于读取 MCP Server 子进程输出（每 0.1 秒一次）
    TickDelegateHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateRaw(this, &FUnrealProjectAnalyzerModule::Tick),
        0.1f
    );

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

    // 取消注册 Ticker
    if (TickDelegateHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TickDelegateHandle);
        TickDelegateHandle.Reset();
    }

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
    
    // Health check endpoint - 使用 FHttpRequestHandler::CreateLambda 创建处理器
    Router->BindRoute(
        FHttpPath(TEXT("/health")),
        EHttpServerRequestVerbs::VERB_GET,
        FHttpRequestHandler::CreateLambda([](const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
        {
            TUniquePtr<FHttpServerResponse> Response = FHttpServerResponse::Create(
                TEXT("{\"status\": \"ok\", \"service\": \"UnrealProjectAnalyzer\"}"),
                TEXT("application/json")
            );
            OnComplete(MoveTemp(Response));
            return true;
        })
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
    // UE5: IsToolMenusAvailable() 已移除，使用 TryGet() 替代
    if (!UToolMenus::TryGet())
    {
        return;
    }

    UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateLambda([this]()
    {
        FToolMenuOwnerScoped OwnerScoped(this);

        // ====================================================================
        // 方案1: 添加到 Tools 菜单（最可靠，推荐）
        // 路径：Tools → Unreal Project Analyzer → ...
        // ====================================================================
        UToolMenu* ToolsMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Tools");
        if (ToolsMenu)
        {
            FToolMenuSection& Section = ToolsMenu->FindOrAddSection("UnrealProjectAnalyzer");
            Section.Label = LOCTEXT("UnrealProjectAnalyzer_MenuLabel", "Unreal Project Analyzer");

            // Start MCP
            Section.AddMenuEntry(
                "UnrealProjectAnalyzer.StartMcp",
                LOCTEXT("StartMcp_Label", "Start MCP Server"),
                LOCTEXT("StartMcp_Tooltip", "Start MCP Server via uv (HTTP/SSE transport recommended)."),
                FSlateIcon(FAppStyle::GetAppStyleSetName(), "Icons.Play"),
                FUIAction(
                    FExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::StartMcpServer),
                    FCanExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::CanStartMcpServer)
                )
            );

            // Stop MCP
            Section.AddMenuEntry(
                "UnrealProjectAnalyzer.StopMcp",
                LOCTEXT("StopMcp_Label", "Stop MCP Server"),
                LOCTEXT("StopMcp_Tooltip", "Stop MCP Server process."),
                FSlateIcon(FAppStyle::GetAppStyleSetName(), "Icons.Stop"),
                FUIAction(
                    FExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::StopMcpServer),
                    FCanExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::CanStopMcpServer)
                )
            );

            // Copy URL
            Section.AddMenuEntry(
                "UnrealProjectAnalyzer.CopyMcpUrl",
                LOCTEXT("CopyMcpUrl_Label", "Copy MCP URL"),
                LOCTEXT("CopyMcpUrl_Tooltip", "Copy MCP URL to clipboard (HTTP/SSE only)."),
                FSlateIcon(FAppStyle::GetAppStyleSetName(), "Icons.Clipboard"),
                FUIAction(
                    FExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::CopyMcpUrlToClipboard),
                    FCanExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::CanStopMcpServer)
                )
            );

            Section.AddSeparator("SettingsSeparator");

            // Settings
            Section.AddMenuEntry(
                "UnrealProjectAnalyzer.OpenSettings",
                LOCTEXT("OpenSettings_Label", "MCP Settings..."),
                LOCTEXT("OpenSettings_Tooltip", "Open Unreal Project Analyzer settings."),
                FSlateIcon(FAppStyle::GetAppStyleSetName(), "Icons.Settings"),
                FUIAction(FExecuteAction::CreateRaw(this, &FUnrealProjectAnalyzerModule::OpenPluginSettings))
            );
        }
    }));
}

void FUnrealProjectAnalyzerModule::UnregisterMenus()
{
    // UE5: IsToolMenusAvailable() 已移除，使用 TryGet() 替代
    if (UToolMenus::TryGet())
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

bool FUnrealProjectAnalyzerModule::Tick(float DeltaTime)
{
    // 调用 McpLauncher 的 Tick 来读取子进程输出
    if (McpLauncher)
    {
        McpLauncher->Tick();
    }
    return true;  // 返回 true 表示继续 tick
}

#undef LOCTEXT_NAMESPACE
    
IMPLEMENT_MODULE(FUnrealProjectAnalyzerModule, UnrealProjectAnalyzer)
