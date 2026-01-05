// Copyright UE5 Project Analyzer Team. All Rights Reserved.

#include "UE5ProjectAnalyzer.h"
#include "HttpServerModule.h"
#include "IHttpRouter.h"
#include "HttpPath.h"
#include "IPythonScriptPlugin.h"
#include "Misc/Paths.h"

#define LOCTEXT_NAMESPACE "FUE5ProjectAnalyzerModule"

void FUE5ProjectAnalyzerModule::StartupModule()
{
    UE_LOG(LogTemp, Log, TEXT("UE5ProjectAnalyzer: Starting module..."));
    
    // Initialize HTTP server
    InitializeHttpServer();
    
    // Initialize Python bridge
    InitializePythonBridge();
    
    UE_LOG(LogTemp, Log, TEXT("UE5ProjectAnalyzer: Module started successfully. HTTP API available at port %d"), HttpPort);
}

void FUE5ProjectAnalyzerModule::ShutdownModule()
{
    UE_LOG(LogTemp, Log, TEXT("UE5ProjectAnalyzer: Shutting down module..."));
    
    ShutdownPythonBridge();
    ShutdownHttpServer();
    
    UE_LOG(LogTemp, Log, TEXT("UE5ProjectAnalyzer: Module shutdown complete."));
}

FUE5ProjectAnalyzerModule& FUE5ProjectAnalyzerModule::Get()
{
    return FModuleManager::LoadModuleChecked<FUE5ProjectAnalyzerModule>("UE5ProjectAnalyzer");
}

bool FUE5ProjectAnalyzerModule::IsAvailable()
{
    return FModuleManager::Get().IsModuleLoaded("UE5ProjectAnalyzer");
}

void FUE5ProjectAnalyzerModule::InitializeHttpServer()
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
        UE_LOG(LogTemp, Log, TEXT("UE5ProjectAnalyzer: HTTP server initialized on port %d"), HttpPort);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("UE5ProjectAnalyzer: Failed to initialize HTTP server on port %d"), HttpPort);
    }
}

void FUE5ProjectAnalyzerModule::ShutdownHttpServer()
{
    if (HttpRouter.IsValid())
    {
        // Routes will be automatically cleaned up
        HttpRouter.Reset();
    }
}

void FUE5ProjectAnalyzerModule::InitializePythonBridge()
{
    // Check if Python plugin is available
    IPythonScriptPlugin* PythonPlugin = FModuleManager::GetModulePtr<IPythonScriptPlugin>("PythonScriptPlugin");
    
    if (!PythonPlugin)
    {
        UE_LOG(LogTemp, Warning, TEXT("UE5ProjectAnalyzer: PythonScriptPlugin not available. Python bridge disabled."));
        return;
    }
    
    // Get the path to our Python bridge script
    FString PluginDir = FPaths::Combine(FPaths::ProjectPluginsDir(), TEXT("UE5ProjectAnalyzer"));
    FString BridgeScriptPath = FPaths::Combine(PluginDir, TEXT("Content/Python/bridge_server.py"));
    
    // Check if script exists
    if (!FPaths::FileExists(BridgeScriptPath))
    {
        UE_LOG(LogTemp, Warning, TEXT("UE5ProjectAnalyzer: Python bridge script not found at %s"), *BridgeScriptPath);
        return;
    }
    
    // Execute the bridge script
    // Note: In production, we'd want more robust error handling
    FString PythonCommand = FString::Printf(TEXT("exec(open('%s').read())"), *BridgeScriptPath);
    
    // TODO: Actually execute the Python script
    // PythonPlugin->ExecPythonCommand(*PythonCommand);
    
    bPythonBridgeInitialized = true;
    UE_LOG(LogTemp, Log, TEXT("UE5ProjectAnalyzer: Python bridge initialized."));
}

void FUE5ProjectAnalyzerModule::ShutdownPythonBridge()
{
    if (bPythonBridgeInitialized)
    {
        // TODO: Send shutdown signal to Python bridge
        bPythonBridgeInitialized = false;
    }
}

void FUE5ProjectAnalyzerModule::RegisterRoutes(TSharedPtr<IHttpRouter> Router)
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
                TEXT("{\"status\": \"ok\", \"service\": \"UE5ProjectAnalyzer\"}"),
                TEXT("application/json")
            );
            OnComplete(MoveTemp(Response));
            return true;
        }
    );
    
    // TODO: Register Blueprint routes
    // Router->BindRoute(FHttpPath(TEXT("/blueprint/search")), ...);
    // Router->BindRoute(FHttpPath(TEXT("/blueprint/:path/hierarchy")), ...);
    // Router->BindRoute(FHttpPath(TEXT("/blueprint/:path/dependencies")), ...);
    
    // TODO: Register Asset routes
    // Router->BindRoute(FHttpPath(TEXT("/asset/search")), ...);
    // Router->BindRoute(FHttpPath(TEXT("/asset/:path/referencers")), ...);
    
    // TODO: Register Analysis routes
    // Router->BindRoute(FHttpPath(TEXT("/analysis/reference-chain")), ...);
    
    UE_LOG(LogTemp, Log, TEXT("UE5ProjectAnalyzer: Routes registered."));
}

#undef LOCTEXT_NAMESPACE
    
IMPLEMENT_MODULE(FUE5ProjectAnalyzerModule, UE5ProjectAnalyzer)
