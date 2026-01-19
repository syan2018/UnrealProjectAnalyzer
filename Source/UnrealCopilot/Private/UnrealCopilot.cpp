// Copyright Unreal Copilot Team. All Rights Reserved.

#include "UnrealCopilot.h"
#include "HttpServerModule.h"
#include "IHttpRouter.h"
#include "HttpPath.h"
#include "IPythonScriptPlugin.h"
#include "Misc/Paths.h"

#include "Http/UnrealAnalyzerHttpRoutes.h"
#include "Bridge/McpServerSubsystem.h"
#include "Settings/UnrealCopilotSettings.h"

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

#define LOCTEXT_NAMESPACE "FUnrealCopilotModule"

void FUnrealCopilotModule::StartupModule()
{
    UE_LOG(LogTemp, Log, TEXT("UnrealCopilot: Starting module..."));

    // Initialize HTTP server
    InitializeHttpServer();

    // Editor integration
    RegisterSettings();
    RegisterMenus();

    UE_LOG(LogTemp, Log, TEXT("UnrealCopilot: Module started successfully. HTTP API available at port %d"), HttpPort);
}

void FUnrealCopilotModule::ShutdownModule()
{
    UE_LOG(LogTemp, Log, TEXT("UnrealCopilot: Shutting down module..."));

    // Stop MCP server via Subsystem
    if (UMcpServerSubsystem::Get())
    {
        UMcpServerSubsystem::Get()->StopMcpServer();
    }

    UnregisterMenus();
    UnregisterSettings();

    ShutdownHttpServer();

    UE_LOG(LogTemp, Log, TEXT("UnrealCopilot: Module shutdown complete."));
}

FUnrealCopilotModule& FUnrealCopilotModule::Get()
{
    return FModuleManager::LoadModuleChecked<FUnrealCopilotModule>("UnrealCopilot");
}

bool FUnrealCopilotModule::IsAvailable()
{
    return FModuleManager::Get().IsModuleLoaded("UnrealCopilot");
}

void FUnrealCopilotModule::InitializeHttpServer()
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
        UE_LOG(LogTemp, Log, TEXT("UnrealCopilot: HTTP server initialized on port %d"), HttpPort);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealCopilot: Failed to initialize HTTP server on port %d"), HttpPort);
    }
}

void FUnrealCopilotModule::ShutdownHttpServer()
{
    if (HttpRouter.IsValid())
    {
        // Routes will be automatically cleaned up
        HttpRouter.Reset();
    }
}

void FUnrealCopilotModule::RegisterRoutes(TSharedPtr<IHttpRouter> Router)
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
                TEXT("{\"status\": \"ok\", \"service\": \"UnrealCopilot\"}"),
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
    
    UE_LOG(LogTemp, Log, TEXT("UnrealCopilot: Routes registered."));
}

// ============================================================================
// Settings + Menus
// ============================================================================

void FUnrealCopilotModule::RegisterSettings()
{
    ISettingsModule* SettingsModule = FModuleManager::GetModulePtr<ISettingsModule>("Settings");
    if (!SettingsModule)
    {
        return;
    }

    SettingsModule->RegisterSettings(
        "Project",
        "Plugins",
        "UnrealCopilot",
        LOCTEXT("UnrealCopilotSettingsName", "Unreal Copilot"),
        LOCTEXT("UnrealCopilotSettingsDesc", "Settings for Unreal Copilot (MCP launcher, transport, and analyzer paths)."),
        GetMutableDefault<UUnrealCopilotSettings>()
    );
}

void FUnrealCopilotModule::UnregisterSettings()
{
    ISettingsModule* SettingsModule = FModuleManager::GetModulePtr<ISettingsModule>("Settings");
    if (!SettingsModule)
    {
        return;
    }

    SettingsModule->UnregisterSettings("Project", "Plugins", "UnrealCopilot");
}

void FUnrealCopilotModule::RegisterMenus()
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
        // 路径：Tools → Unreal Copilot → ...
        // ====================================================================
        UToolMenu* ToolsMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Tools");
        if (ToolsMenu)
        {
            FToolMenuSection& Section = ToolsMenu->FindOrAddSection("UnrealCopilot");
            Section.Label = LOCTEXT("UnrealCopilot_MenuLabel", "Unreal Copilot");

            // Start MCP
            Section.AddMenuEntry(
                "UnrealCopilot.StartMcp",
                LOCTEXT("StartMcp_Label", "Start MCP Server"),
                LOCTEXT("StartMcp_Tooltip", "Start MCP Server in UE's Python environment (HTTP/SSE transport recommended)."),
                FSlateIcon(FAppStyle::GetAppStyleSetName(), "Icons.Play"),
                FUIAction(
                    FExecuteAction::CreateRaw(this, &FUnrealCopilotModule::StartMcpServer),
                    FCanExecuteAction::CreateRaw(this, &FUnrealCopilotModule::CanStartMcpServer)
                )
            );

            // Stop MCP
            Section.AddMenuEntry(
                "UnrealCopilot.StopMcp",
                LOCTEXT("StopMcp_Label", "Stop MCP Server"),
                LOCTEXT("StopMcp_Tooltip", "Stop MCP Server running in UE's Python environment."),
                FSlateIcon(FAppStyle::GetAppStyleSetName(), "Icons.Stop"),
                FUIAction(
                    FExecuteAction::CreateRaw(this, &FUnrealCopilotModule::StopMcpServer),
                    FCanExecuteAction::CreateRaw(this, &FUnrealCopilotModule::CanStopMcpServer)
                )
            );

            // Copy URL
            Section.AddMenuEntry(
                "UnrealCopilot.CopyMcpUrl",
                LOCTEXT("CopyMcpUrl_Label", "Copy MCP URL"),
                LOCTEXT("CopyMcpUrl_Tooltip", "Copy MCP URL to clipboard (HTTP/SSE only)."),
                FSlateIcon(FAppStyle::GetAppStyleSetName(), "Icons.Clipboard"),
                FUIAction(
                    FExecuteAction::CreateRaw(this, &FUnrealCopilotModule::CopyMcpUrlToClipboard),
                    FCanExecuteAction::CreateRaw(this, &FUnrealCopilotModule::CanStopMcpServer)
                )
            );

            Section.AddSeparator("SettingsSeparator");

            // Settings
            Section.AddMenuEntry(
                "UnrealCopilot.OpenSettings",
                LOCTEXT("OpenSettings_Label", "MCP Settings..."),
                LOCTEXT("OpenSettings_Tooltip", "Open Unreal Copilot settings."),
                FSlateIcon(FAppStyle::GetAppStyleSetName(), "Icons.Settings"),
                FUIAction(FExecuteAction::CreateRaw(this, &FUnrealCopilotModule::OpenPluginSettings))
            );
        }
    }));
}

void FUnrealCopilotModule::UnregisterMenus()
{
    // UE5: IsToolMenusAvailable() 已移除，使用 TryGet() 替代
    if (UToolMenus::TryGet())
    {
        UToolMenus::UnregisterOwner(this);
    }
}

bool FUnrealCopilotModule::CanStartMcpServer() const
{
    UMcpServerSubsystem* Subsystem = UMcpServerSubsystem::Get();
    return Subsystem && !Subsystem->IsMcpServerRunning() && !Subsystem->IsMcpServerStarting() && !Subsystem->IsMcpServerStopping();
}

bool FUnrealCopilotModule::CanStopMcpServer() const
{
    UMcpServerSubsystem* Subsystem = UMcpServerSubsystem::Get();
    return Subsystem && (Subsystem->IsMcpServerRunning() || Subsystem->IsMcpServerStarting() || Subsystem->IsMcpServerStopping());
}

void FUnrealCopilotModule::StartMcpServer()
{
    UMcpServerSubsystem* Subsystem = UMcpServerSubsystem::Get();
    if (!Subsystem)
    {
        UE_LOG(LogTemp, Error, TEXT("UnrealCopilot: McpServerSubsystem not available"));
        return;
    }

    // Heuristic: first start may need to install/sync dependencies, which can take minutes.
    bool bMayNeedDependencySync = false;
    if (IPluginManager::Get().FindPlugin(TEXT("UnrealCopilot")))
    {
        const FString PluginDir = IPluginManager::Get().FindPlugin(TEXT("UnrealCopilot"))->GetBaseDir();
        const FString PythonDir = FPaths::Combine(PluginDir, TEXT("Content/Python"));
        const FString VenvDir = FPaths::Combine(PythonDir, TEXT(".venv"));

        if (!FPaths::DirectoryExists(VenvDir))
        {
            bMayNeedDependencySync = true;
        }
    }

    Subsystem->StartMcpServer();

    const FString Url = GetMcpUrl();
    UE_LOG(LogTemp, Log, TEXT("UnrealCopilot: MCP server start requested"));
    // NOTE: Don't log the URL here. We only log/show it after the server is confirmed running.

    // Immediate user feedback: starting
    FNotificationInfo Info(
        bMayNeedDependencySync
            ? LOCTEXT("McpStartingFirstTime", "MCP Server starting... (first start may sync Python deps; check Output Log)")
            : LOCTEXT("McpStarting", "MCP Server starting... (check Output Log)")
    );
    Info.ExpireDuration = 5.0f;
    FSlateNotificationManager::Get().AddNotification(Info);

    // Start polling for readiness to provide accurate status
    if (McpStartPollHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(McpStartPollHandle);
        McpStartPollHandle.Reset();
    }
    McpStartPollDeadlineSeconds = FPlatformTime::Seconds() + (bMayNeedDependencySync ? 180.0 : 12.0);
    McpStartPollHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateRaw(this, &FUnrealCopilotModule::TickMcpStartPoll),
        0.25f
    );
}

void FUnrealCopilotModule::StopMcpServer()
{
    UMcpServerSubsystem* Subsystem = UMcpServerSubsystem::Get();
    if (!Subsystem)
    {
        return;
    }

    Subsystem->StopMcpServer();

    UE_LOG(LogTemp, Log, TEXT("UnrealCopilot: MCP server stop requested"));

    FNotificationInfo Info(LOCTEXT("McpStopRequested", "MCP Server stop requested (check Output Log)"));
    Info.ExpireDuration = 4.0f;
    FSlateNotificationManager::Get().AddNotification(Info);
}

void FUnrealCopilotModule::CopyMcpUrlToClipboard() const
{
    const FString Url = GetMcpUrl();
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

FString FUnrealCopilotModule::GetMcpUrl() const
{
    const UUnrealCopilotSettings* Settings = GetDefault<UUnrealCopilotSettings>();
    if (!Settings)
    {
        return TEXT("");
    }

    if (Settings->Transport == EUnrealAnalyzerMcpTransport::Stdio)
    {
        return TEXT("");
    }

    return FString::Printf(TEXT("http://%s:%d%s"),
        *Settings->McpHost,
        Settings->McpPort,
        Settings->Transport == EUnrealAnalyzerMcpTransport::Http ? *Settings->McpPath : TEXT(""));
}

void FUnrealCopilotModule::OpenPluginSettings() const
{
    ISettingsModule* SettingsModule = FModuleManager::GetModulePtr<ISettingsModule>("Settings");
    if (SettingsModule)
    {
        SettingsModule->ShowViewer("Project", "Plugins", "UnrealCopilot");
    }
}

bool FUnrealCopilotModule::TickMcpStartPoll(float DeltaTime)
{
    UMcpServerSubsystem* Subsystem = UMcpServerSubsystem::Get();
    const double Now = FPlatformTime::Seconds();

    if (!Subsystem)
    {
        McpStartPollHandle.Reset();
        return false;
    }

    if (Subsystem->IsMcpServerRunning())
    {
        const FString Url = GetMcpUrl();
        if (!Url.IsEmpty())
        {
            UE_LOG(LogTemp, Log, TEXT("UnrealCopilot: MCP server ready at %s"), *Url);
        }

        FNotificationInfo Info(LOCTEXT("McpReady", "MCP Server is running"));
        Info.ExpireDuration = 3.0f;
        FSlateNotificationManager::Get().AddNotification(Info);

        McpStartPollHandle.Reset();
        return false;
    }

    if (!Subsystem->IsMcpServerStarting())
    {
        FNotificationInfo Info(LOCTEXT("McpStartFailed", "MCP Server failed to start. Check Output Log."));
        Info.ExpireDuration = 6.0f;
        FSlateNotificationManager::Get().AddNotification(Info);

        McpStartPollHandle.Reset();
        return false;
    }

    if (Now > McpStartPollDeadlineSeconds)
    {
        FNotificationInfo Info(LOCTEXT("McpStartTimeout", "MCP Server not ready yet (startup timed out). Check Output Log."));
        Info.ExpireDuration = 6.0f;
        FSlateNotificationManager::Get().AddNotification(Info);

        McpStartPollHandle.Reset();
        return false;
    }

    // keep polling
    return true;
}

#undef LOCTEXT_NAMESPACE
    
IMPLEMENT_MODULE(FUnrealCopilotModule, UnrealCopilot)


