// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Skill/CppSkillApiSubsystem.h"

#include "AssetToolsModule.h"
#include "Misc/PackageName.h"
#include "Modules/ModuleManager.h"
#include "ObjectTools.h"
#include "UObject/SavePackage.h"

bool UCppSkillApiSubsystem::RenameAsset(const FString& SourcePath, const FString& DestPath, FString& OutError)
{
    UObject* Asset = LoadAsset(SourcePath, OutError);
    if (!Asset)
    {
        return false;
    }

    const FString NewPackagePath = FPackageName::GetLongPackagePath(DestPath);
    const FString NewName = FPackageName::GetShortName(DestPath);
    if (NewPackagePath.IsEmpty() || NewName.IsEmpty())
    {
        OutError = TEXT("Invalid destination path.");
        return false;
    }

    FAssetRenameData RenameData(Asset, NewPackagePath, NewName);
    TArray<FAssetRenameData> RenameDataList;
    RenameDataList.Add(RenameData);

    FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
    const bool bSuccess = AssetToolsModule.Get().RenameAssets(RenameDataList);
    if (!bSuccess)
    {
        OutError = TEXT("Rename failed.");
    }
    return bSuccess;
}

bool UCppSkillApiSubsystem::DuplicateAsset(const FString& SourcePath, const FString& DestPath, FString& OutError)
{
    UObject* Asset = LoadAsset(SourcePath, OutError);
    if (!Asset)
    {
        return false;
    }

    const FString NewPackagePath = FPackageName::GetLongPackagePath(DestPath);
    const FString NewName = FPackageName::GetShortName(DestPath);
    if (NewPackagePath.IsEmpty() || NewName.IsEmpty())
    {
        OutError = TEXT("Invalid destination path.");
        return false;
    }

    TArray<FString> Names;
    TArray<FString> PackagePaths;
    TArray<UObject*> Assets;
    Names.Add(NewName);
    PackagePaths.Add(NewPackagePath);
    Assets.Add(Asset);

    FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
    UObject* NewAsset = AssetToolsModule.Get().DuplicateAsset(NewName, NewPackagePath, Asset);
    if (!NewAsset)
    {
        OutError = TEXT("Duplicate failed.");
        return false;
    }

    return true;
}

bool UCppSkillApiSubsystem::DeleteAsset(const FString& AssetPath, FString& OutError)
{
    UObject* Asset = LoadAsset(AssetPath, OutError);
    if (!Asset)
    {
        return false;
    }

    TArray<UObject*> AssetsToDelete;
    AssetsToDelete.Add(Asset);

    FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
    const int32 DeletedCount = ObjectTools::DeleteObjects(AssetsToDelete, /*bShowConfirmation*/ false);
    if (DeletedCount <= 0)
    {
        OutError = TEXT("Delete failed or was cancelled.");
        return false;
    }
    return true;
}

bool UCppSkillApiSubsystem::SaveAsset(const FString& AssetPath, FString& OutError)
{
    UObject* Asset = LoadAsset(AssetPath, OutError);
    if (!Asset)
    {
        return false;
    }

    UPackage* Package = Asset->GetOutermost();
    if (!Package)
    {
        OutError = TEXT("Asset has no package.");
        return false;
    }

    FString Filename;
    if (!FPackageName::TryConvertLongPackageNameToFilename(
        Package->GetName(),
        Filename,
        FPackageName::GetAssetPackageExtension()
    ))
    {
        OutError = TEXT("Failed to resolve package filename.");
        return false;
    }

    FSavePackageArgs SaveArgs;
    SaveArgs.TopLevelFlags = RF_Standalone;
    SaveArgs.SaveFlags = SAVE_None;
    SaveArgs.Error = GError;

    const bool bSuccess = UPackage::SavePackage(Package, Asset, *Filename, SaveArgs);
    if (!bSuccess)
    {
        OutError = TEXT("Failed to save package.");
    }
    return bSuccess;
}


