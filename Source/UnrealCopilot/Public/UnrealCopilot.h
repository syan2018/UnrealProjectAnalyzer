// Copyright Unreal Copilot Team. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "Containers/Ticker.h"

class FHttpServerModule;
class IHttpRouter;

/**
 * Unreal Copilot Module
 *
 * Provides HTTP API for Blueprint, Asset, and C++ analysis.
 * The MCP Server runs inside UE's Python environment (managed by McpServerSubsystem).
 */
class FUnrealCopilotModule : public IModuleInterface
{
public:
    /** IModuleInterface implementation */
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;

    /** Get the module instance */
    static FUnrealCopilotModule& Get();

    /** Check if module is loaded */
    static bool IsAvailable();

private:
    /** Initialize the HTTP server */
    void InitializeHttpServer();

    /** Shutdown the HTTP server */
    void ShutdownHttpServer();

    /** Register HTTP routes */
    void RegisterRoutes(TSharedPtr<IHttpRouter> Router);

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

    FString GetMcpUrl() const;

    bool TickMcpStartPoll(float DeltaTime);

private:
    /** HTTP server port */
    int32 HttpPort = 8080;

    /** HTTP router handle */
    TSharedPtr<IHttpRouter> HttpRouter;

    /** Polling handle for MCP startup readiness */
    FTSTicker::FDelegateHandle McpStartPollHandle;

    /** Deadline for MCP startup polling */
    double McpStartPollDeadlineSeconds = 0.0;
};


