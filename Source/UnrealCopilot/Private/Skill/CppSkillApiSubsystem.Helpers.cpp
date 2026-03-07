// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Skill/CppSkillApiSubsystem.h"

#include "Editor.h"
#include "Engine/World.h"
#include "UObject/PropertyPortFlags.h"
#include "UObject/UnrealType.h"

UObject* UCppSkillApiSubsystem::LoadAsset(const FString& AssetPath, FString& OutError) const
{
    if (AssetPath.IsEmpty())
    {
        OutError = TEXT("Asset path is empty.");
        return nullptr;
    }

    UObject* Asset = LoadObject<UObject>(nullptr, *AssetPath);
    if (!Asset)
    {
        OutError = TEXT("Asset not found.");
        return nullptr;
    }
    return Asset;
}

UBlueprint* UCppSkillApiSubsystem::LoadBlueprint(const FString& BlueprintPath, FString& OutError) const
{
    UObject* Asset = LoadAsset(BlueprintPath, OutError);
    UBlueprint* Blueprint = Cast<UBlueprint>(Asset);
    if (!Blueprint)
    {
        OutError = TEXT("Asset is not a Blueprint.");
        return nullptr;
    }
    return Blueprint;
}

UWorld* UCppSkillApiSubsystem::GetEditorWorld(FString& OutError) const
{
    if (!GEditor)
    {
        OutError = TEXT("GEditor is not available.");
        return nullptr;
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
    {
        OutError = TEXT("Editor world not available.");
    }
    return World;
}

bool UCppSkillApiSubsystem::SetObjectPropertyByString(
    UObject* Target,
    const FName& PropertyName,
    const FString& ValueAsString,
    FString& OutError
) const
{
    if (!Target)
    {
        OutError = TEXT("Target is null.");
        return false;
    }

    FProperty* Property = FindFProperty<FProperty>(Target->GetClass(), PropertyName);
    if (!Property)
    {
        OutError = TEXT("Property not found.");
        return false;
    }

    // 使用 ImportText_InContainer 而非 ImportText_Direct，
    // 前者通过 Container 指针寻址属性，对 TMap/TArray/TSet 等容器类型支持更完整
    const TCHAR* Result = Property->ImportText_InContainer(*ValueAsString, Target, Target, PPF_None);
    if (!Result)
    {
        OutError = TEXT("Failed to import property value.");
        return false;
    }

    Target->Modify();
    return true;
}


