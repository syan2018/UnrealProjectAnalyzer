// Copyright UE5 Project Analyzer Team. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class FHttpServerModule;
class IHttpRouter;

/**
 * UE5 Project Analyzer Module
 * 
 * Provides HTTP API for Blueprint, Asset, and C++ analysis.
 * Also manages the Python Bridge lifecycle.
 */
class FUE5ProjectAnalyzerModule : public IModuleInterface
{
public:
    /** IModuleInterface implementation */
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
    
    /** Get the module instance */
    static FUE5ProjectAnalyzerModule& Get();
    
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

private:
    /** HTTP server port */
    int32 HttpPort = 8080;
    
    /** HTTP router handle */
    TSharedPtr<IHttpRouter> HttpRouter;
    
    /** Whether Python bridge is initialized */
    bool bPythonBridgeInitialized = false;
};
