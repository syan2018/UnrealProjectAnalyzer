// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Skill/CppSkillApiSubsystem.h"

#include "Algo/Unique.h"
#include "Editor.h"
#include "FileHelpers.h"

TArray<FString> UCppSkillApiSubsystem::ListDirtyPackages() const
{
    TArray<UPackage*> DirtyPackages;
    TArray<FString> Result;

    FEditorFileUtils::GetDirtyContentPackages(DirtyPackages);
    for (UPackage* Package : DirtyPackages)
    {
        if (Package)
        {
            Result.Add(Package->GetName());
        }
    }

    DirtyPackages.Reset();
    FEditorFileUtils::GetDirtyWorldPackages(DirtyPackages);
    for (UPackage* Package : DirtyPackages)
    {
        if (Package)
        {
            Result.Add(Package->GetName());
        }
    }

    Result.Sort();
    Result.SetNum(Algo::Unique(Result));
    return Result;
}

bool UCppSkillApiSubsystem::SaveDirtyPackages(bool bPromptUser, FString& OutError)
{
    const bool bSaveMapPackages = true;
    const bool bSaveContentPackages = true;
    const bool bFastSave = false;
    const bool bNotifyNoPackagesSaved = false;
    const bool bCanBeDeclined = true;

    const bool bSuccess = FEditorFileUtils::SaveDirtyPackages(
        bPromptUser,
        bSaveMapPackages,
        bSaveContentPackages,
        bFastSave,
        bNotifyNoPackagesSaved,
        bCanBeDeclined
    );
    if (!bSuccess)
    {
        OutError = TEXT("SaveDirtyPackages failed or was cancelled.");
    }
    return bSuccess;
}

bool UCppSkillApiSubsystem::UndoLastTransaction(FString& OutError)
{
    if (!GEditor)
    {
        OutError = TEXT("GEditor is not available.");
        return false;
    }

    if (!GEditor->UndoTransaction())
    {
        OutError = TEXT("Undo failed.");
        return false;
    }
    return true;
}

bool UCppSkillApiSubsystem::RedoLastTransaction(FString& OutError)
{
    if (!GEditor)
    {
        OutError = TEXT("GEditor is not available.");
        return false;
    }

    if (!GEditor->RedoTransaction())
    {
        OutError = TEXT("Redo failed.");
        return false;
    }
    return true;
}


