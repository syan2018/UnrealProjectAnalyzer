// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Skill/CppSkillApiSubsystem.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Engine/Blueprint.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Modules/ModuleManager.h"

FString UCppSkillApiSubsystem::CompileAllBlueprintsSummary()
{
    FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
    TArray<FAssetData> Assets;
    AssetRegistryModule.Get().GetAssetsByClass(UBlueprint::StaticClass()->GetClassPathName(), Assets, true);

    int32 Total = 0;
    int32 Errors = 0;
    int32 Warnings = 0;

    for (const FAssetData& Asset : Assets)
    {
        UBlueprint* Blueprint = Cast<UBlueprint>(Asset.GetAsset());
        if (!Blueprint)
        {
            continue;
        }

        Total++;
        FKismetEditorUtilities::CompileBlueprint(Blueprint);
        if (Blueprint->Status == BS_Error)
        {
            Errors++;
        }
        else if (Blueprint->Status == BS_UpToDateWithWarnings)
        {
            Warnings++;
        }
    }

    return FString::Printf(
        TEXT("Compiled %d blueprints. Errors=%d, Warnings=%d"),
        Total,
        Errors,
        Warnings
    );
}


