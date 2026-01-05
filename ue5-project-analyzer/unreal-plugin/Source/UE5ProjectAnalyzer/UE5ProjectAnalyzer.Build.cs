// Copyright UE5 Project Analyzer Team. All Rights Reserved.

using UnrealBuildTool;

public class UE5ProjectAnalyzer : ModuleRules
{
    public UE5ProjectAnalyzer(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        
        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
        });

        PrivateDependencyModuleNames.AddRange(new string[]
        {
            // HTTP Server
            "HTTP",
            "HTTPServer",
            
            // JSON
            "Json",
            "JsonUtilities",
            
            // Editor APIs
            "UnrealEd",
            "BlueprintGraph",
            "Kismet",
            
            // Asset Registry
            "AssetRegistry",
            
            // Python integration
            "PythonScriptPlugin",
        });
    }
}
