// Copyright Unreal Project Analyzer Team. All Rights Reserved.

using UnrealBuildTool;

public class UnrealProjectAnalyzer : ModuleRules
{
    public UnrealProjectAnalyzer(ReadOnlyTargetRules Target) : base(Target)
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

            // UI / Editor integration (toolbar + settings)
            "ToolMenus",
            "LevelEditor",
            "Slate",
            "SlateCore",
            "Projects",
            "Settings",
            "ApplicationCore",
        });
    }
}
