// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Skill/CppSkillApiSubsystem.h"

#include "Editor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"

bool UCppSkillApiSubsystem::LoadMap(const FString& MapPath, FString& OutError)
{
    FString MapFilename;
    if (!FPackageName::TryConvertLongPackageNameToFilename(
        MapPath,
        MapFilename,
        FPackageName::GetMapPackageExtension()
    ))
    {
        OutError = TEXT("Invalid map path.");
        return false;
    }

    if (!FEditorFileUtils::LoadMap(MapFilename, /*bLoadAsTemplate*/ false, /*bShowProgress*/ true))
    {
        OutError = TEXT("Failed to load map.");
        return false;
    }
    return true;
}

AActor* UCppSkillApiSubsystem::SpawnActorByClassPath(
    const FString& ClassPath,
    const FTransform& Transform,
    FString& OutError
)
{
    UWorld* World = GetEditorWorld(OutError);
    if (!World)
    {
        return nullptr;
    }

    UClass* SpawnClass = LoadObject<UClass>(nullptr, *ClassPath);
    if (!SpawnClass)
    {
        OutError = TEXT("Spawn class not found.");
        return nullptr;
    }

    FActorSpawnParameters Params;
    AActor* Actor = World->SpawnActor<AActor>(SpawnClass, Transform, Params);
    if (!Actor)
    {
        OutError = TEXT("Failed to spawn actor.");
    }
    return Actor;
}

AActor* UCppSkillApiSubsystem::FindActorByName(const FString& ActorName)
{
    FString DummyError;
    UWorld* World = GetEditorWorld(DummyError);
    if (!World)
    {
        return nullptr;
    }

    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            return *It;
        }
    }
    return nullptr;
}

bool UCppSkillApiSubsystem::DestroyActorByName(const FString& ActorName, FString& OutError)
{
    AActor* Actor = FindActorByName(ActorName);
    if (!Actor)
    {
        OutError = TEXT("Actor not found.");
        return false;
    }

    Actor->Destroy();
    return true;
}

bool UCppSkillApiSubsystem::SetActorPropertyByString(
    const FString& ActorName,
    const FName& PropertyName,
    const FString& ValueAsString,
    FString& OutError
)
{
    AActor* Actor = FindActorByName(ActorName);
    if (!Actor)
    {
        OutError = TEXT("Actor not found.");
        return false;
    }

    return SetObjectPropertyByString(Actor, PropertyName, ValueAsString, OutError);
}

bool UCppSkillApiSubsystem::SetActorTransformByName(
    const FString& ActorName,
    const FTransform& Transform,
    FString& OutError
)
{
    AActor* Actor = FindActorByName(ActorName);
    if (!Actor)
    {
        OutError = TEXT("Actor not found.");
        return false;
    }

    Actor->SetActorTransform(Transform);
    return true;
}


