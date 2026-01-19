// Copyright Unreal Copilot Team. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "EditorSubsystem.h"
#include "Settings/UnrealCopilotSettings.h"
#include "McpServerSubsystem.generated.h"

/**
 * MCP Server Subsystem
 *
 * Manages the lifecycle of the MCP server running inside UE's Python environment.
 *
 * Design notes:
 * - No per-tick port probing (avoids editor hitches + Windows socket false-positives).
 * - Python bridge actively notifies this subsystem when the server actually starts/stops.
 */
UCLASS()
class UNREALCOPILOT_API UMcpServerSubsystem : public UEditorSubsystem
{
    GENERATED_BODY()

public:
    // ============================================================================
    // UEditorSubsystem interface
    // ============================================================================

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    // ============================================================================
    // Blueprint API
    // ============================================================================

    /**
     * Start the MCP server.
     * The server runs in a background thread inside UE's Python environment.
     */
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|MCP")
    void StartMcpServer();

    /**
     * Stop the MCP server.
     */
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|MCP")
    void StopMcpServer();

    /**
     * Check if the MCP server is running.
     */
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|MCP")
    bool IsMcpServerRunning() const;

    /**
     * Check if the MCP server is starting.
     */
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|MCP")
    bool IsMcpServerStarting() const;

    /**
     * Check if the MCP server is stopping (stop requested, not yet confirmed stopped).
     */
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|MCP")
    bool IsMcpServerStopping() const;

    /**
     * Get the singleton instance of the subsystem.
     */
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|MCP")
    static UMcpServerSubsystem* Get();

    // ============================================================================
    // Python → C++ notification API (called by init_analyzer.py)
    // ============================================================================

    /** Python notifies: server start requested (enter starting state) */
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|MCP")
    void NotifyMcpServerStarting(
        EUnrealAnalyzerMcpTransport Transport,
        const FString& Host,
        int32 Port,
        const FString& Path
    );

    /** Python notifies: server is now running (listening) */
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|MCP")
    void NotifyMcpServerRunning();

    /** Python notifies: server stopped */
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|MCP")
    void NotifyMcpServerStopped();

    /** Python notifies: start failed */
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|MCP")
    void NotifyMcpServerStartFailed(const FString& Error);

private:
    /** Check if Python is available and initialized */
    bool IsPythonAvailable() const;

    /** Initialize the Python bridge (executes init_analyzer.py) */
    void InitializePythonBridge();

private:
    /** Whether the Python bridge has been initialized */
    bool bPythonBridgeInitialized = false;

    /** Whether the MCP server is currently running */
    bool bMcpServerRunning = false;

    /** Whether a start request is in progress */
    bool bMcpServerStarting = false;

    /** Whether a stop request is in progress */
    bool bMcpServerStopRequested = false;

    /** Last MCP transport used */
    EUnrealAnalyzerMcpTransport LastTransport = EUnrealAnalyzerMcpTransport::Http;

    /** Last MCP host used */
    FString LastMcpHost;

    /** Last MCP port used */
    int32 LastMcpPort = 0;

    /** Timestamp (seconds) when start was requested */
    double StartRequestedAtSeconds = 0.0;

    /** Timestamp (seconds) when stop was requested */
    double StopRequestedAtSeconds = 0.0;
};

