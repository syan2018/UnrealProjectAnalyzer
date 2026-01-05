// Copyright Unreal Project Analyzer Team. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "Containers/Ticker.h"

class FHttpServerModule;
class IHttpRouter;

/**
 * Unreal Project Analyzer Module
 * 
 * Provides HTTP API for Blueprint, Asset, and C++ analysis.
 * Also manages the Python Bridge lifecycle.
 */
class FUnrealProjectAnalyzerModule : public IModuleInterface
{
public:
    /** IModuleInterface implementation */
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
    
    /** Get the module instance */
    static FUnrealProjectAnalyzerModule& Get();
    
    /** Check if module is loaded */
    static bool IsAvailable();

private:
    /** Initialize the HTTP server */
    void InitializeHttpServer();
    
    /** Shutdown the HTTP server */
    void ShutdownHttpServer();
    
    /** Initialize the Python bridge */
    void InitializePythonBridge();
    
    /** Shutdown the Python bridge */
    void ShutdownPythonBridge();
    
    /** Register HTTP routes */
    void RegisterRoutes(TSharedPtr<IHttpRouter> Router);

    /** Tick callback - 用于读取 MCP Server 子进程输出 */
    bool Tick(float DeltaTime);

private:
    // =====================================================================
    // Editor integration: Settings + Toolbar
    // =====================================================================

    void RegisterSettings();
    void UnregisterSettings();

    void RegisterMenus();
    void UnregisterMenus();

    void StartMcpServer();
    void StopMcpServer();
    void CopyMcpUrlToClipboard() const;
    void OpenPluginSettings() const;

    bool CanStartMcpServer() const;
    bool CanStopMcpServer() const;

private:
    /** HTTP server port */
    int32 HttpPort = 8080;
    
    /** HTTP router handle */
    TSharedPtr<IHttpRouter> HttpRouter;
    
    /** Whether Python bridge is initialized */
    bool bPythonBridgeInitialized = false;

    /** External MCP Server process manager (uv run ...) */
    class FUnrealProjectAnalyzerMcpLauncher* McpLauncher = nullptr;

    /** Ticker delegate handle - 用于定期读取子进程输出 */
    FTSTicker::FDelegateHandle TickDelegateHandle;
};
