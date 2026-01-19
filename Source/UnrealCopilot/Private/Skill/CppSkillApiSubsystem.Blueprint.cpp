// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Skill/CppSkillApiSubsystem.h"

#include "Engine/Blueprint.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Misc/PackageName.h"

bool UCppSkillApiSubsystem::CreateBlueprint(
    const FString& ParentClassPath,
    const FString& PackagePath,
    const FString& BlueprintName,
    FString& OutBlueprintPath,
    FString& OutError
)
{
    UClass* ParentClass = LoadObject<UClass>(nullptr, *ParentClassPath);
    if (!ParentClass)
    {
        OutError = TEXT("Parent class not found.");
        return false;
    }

    if (PackagePath.IsEmpty() || BlueprintName.IsEmpty())
    {
        OutError = TEXT("Invalid package path or blueprint name.");
        return false;
    }

    const FString FullPackageName = FString::Printf(TEXT("%s/%s"), *PackagePath, *BlueprintName);
    if (FPackageName::DoesPackageExist(FullPackageName))
    {
        OutError = TEXT("Blueprint already exists.");
        return false;
    }

    UPackage* Package = CreatePackage(*FullPackageName);
    if (!Package)
    {
        OutError = TEXT("Failed to create package.");
        return false;
    }

    UBlueprint* NewBlueprint = FKismetEditorUtilities::CreateBlueprint(
        ParentClass,
        Package,
        FName(*BlueprintName),
        BPTYPE_Normal,
        UBlueprint::StaticClass(),
        UBlueprintGeneratedClass::StaticClass()
    );

    if (!NewBlueprint)
    {
        OutError = TEXT("Failed to create blueprint.");
        return false;
    }

    OutBlueprintPath = NewBlueprint->GetPathName();
    return true;
}

bool UCppSkillApiSubsystem::CompileBlueprint(const FString& BlueprintPath, FString& OutError)
{
    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    FKismetEditorUtilities::CompileBlueprint(Blueprint);
    if (Blueprint->Status == BS_Error)
    {
        OutError = TEXT("Blueprint compile failed.");
        return false;
    }
    return true;
}

bool UCppSkillApiSubsystem::SaveBlueprint(const FString& BlueprintPath, FString& OutError)
{
    return SaveAsset(BlueprintPath, OutError);
}

bool UCppSkillApiSubsystem::SetBlueprintCDOPropertyByString(
    const FString& BlueprintPath,
    const FName& PropertyName,
    const FString& ValueAsString,
    FString& OutError
)
{
    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint || !Blueprint->GeneratedClass)
    {
        OutError = TEXT("Blueprint class not generated.");
        return false;
    }

    UObject* CDO = Blueprint->GeneratedClass->GetDefaultObject();
    if (!CDO)
    {
        OutError = TEXT("CDO not available.");
        return false;
    }

    return SetObjectPropertyByString(CDO, PropertyName, ValueAsString, OutError);
}

bool UCppSkillApiSubsystem::AddBlueprintComponent(
    const FString& BlueprintPath,
    const FString& ComponentClassPath,
    const FName& ComponentName,
    FString& OutError
)
{
    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    UClass* ComponentClass = LoadObject<UClass>(nullptr, *ComponentClassPath);
    if (!ComponentClass || !ComponentClass->IsChildOf(UActorComponent::StaticClass()))
    {
        OutError = TEXT("Component class is invalid.");
        return false;
    }

    USimpleConstructionScript* SCS = Blueprint->SimpleConstructionScript;
    if (!SCS)
    {
        Blueprint->SimpleConstructionScript = NewObject<USimpleConstructionScript>(Blueprint, TEXT("SimpleConstructionScript"));
        SCS = Blueprint->SimpleConstructionScript;
    }

    USCS_Node* NewNode = SCS->CreateNode(ComponentClass, ComponentName);
    if (!NewNode)
    {
        OutError = TEXT("Failed to create SCS node.");
        return false;
    }

    SCS->AddNode(NewNode);
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool UCppSkillApiSubsystem::RemoveBlueprintComponent(
    const FString& BlueprintPath,
    const FName& ComponentName,
    FString& OutError
)
{
    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    USimpleConstructionScript* SCS = Blueprint->SimpleConstructionScript;
    if (!SCS)
    {
        OutError = TEXT("Blueprint has no SimpleConstructionScript.");
        return false;
    }

    USCS_Node* Node = SCS->FindSCSNode(ComponentName);
    if (!Node)
    {
        OutError = TEXT("Component not found.");
        return false;
    }

    SCS->RemoveNode(Node);
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}


