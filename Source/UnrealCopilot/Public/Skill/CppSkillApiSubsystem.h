#pragma once

#include "CoreMinimal.h"
#include "EditorSubsystem.h"

#include "CppSkillApiSubsystem.generated.h"

class AActor;
class UBlueprint;
class UWorld;

/**
 * CppSkillApiSubsystem
 *
 * 提供可被 UE Python/Skill 脚本调用的编辑原语集合。
 * 面向通用编辑能力：资产、蓝图、世界、编辑器保存/事务、基础验证。
 */
UCLASS()
class UNREALCOPILOT_API UCppSkillApiSubsystem : public UEditorSubsystem
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill")
    static UCppSkillApiSubsystem* Get();

    // ---------------------------------------------------------------------
    // AssetOps
    // ---------------------------------------------------------------------
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Asset")
    bool RenameAsset(const FString& SourcePath, const FString& DestPath, FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Asset")
    bool DuplicateAsset(const FString& SourcePath, const FString& DestPath, FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Asset")
    bool DeleteAsset(const FString& AssetPath, FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Asset")
    bool SaveAsset(const FString& AssetPath, FString& OutError);

    // ---------------------------------------------------------------------
    // BlueprintOps
    // ---------------------------------------------------------------------
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool CreateBlueprint(
        const FString& ParentClassPath,
        const FString& PackagePath,
        const FString& BlueprintName,
        FString& OutBlueprintPath,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool CompileBlueprint(const FString& BlueprintPath, FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool SaveBlueprint(const FString& BlueprintPath, FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool SetBlueprintCDOPropertyByString(
        const FString& BlueprintPath,
        const FName& PropertyName,
        const FString& ValueAsString,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool AddBlueprintComponent(
        const FString& BlueprintPath,
        const FString& ComponentClassPath,
        const FName& ComponentName,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool RemoveBlueprintComponent(
        const FString& BlueprintPath,
        const FName& ComponentName,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool AddBlueprintVariable(
        const FString& BlueprintPath,
        const FName& VariableName,
        const FString& VariableType,
        const FString& DefaultValue,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool RemoveBlueprintVariable(
        const FString& BlueprintPath,
        const FName& VariableName,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool RenameBlueprintVariable(
        const FString& BlueprintPath,
        const FName& OldVariableName,
        const FName& NewVariableName,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool SetBlueprintVariableDefault(
        const FString& BlueprintPath,
        const FName& VariableName,
        const FString& DefaultValue,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool AddBlueprintGraph(
        const FString& BlueprintPath,
        const FString& GraphName,
        const FString& GraphType,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool RemoveBlueprintGraph(
        const FString& BlueprintPath,
        const FString& GraphName,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool RenameBlueprintGraph(
        const FString& BlueprintPath,
        const FString& OldGraphName,
        const FString& NewGraphName,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool AddBlueprintNode(
        const FString& BlueprintPath,
        const FString& GraphName,
        const FString& NodeClassPath,
        int32 NodePosX,
        int32 NodePosY,
        FString& OutNodeGuid,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool RemoveBlueprintNode(
        const FString& BlueprintPath,
        const FString& GraphName,
        const FString& NodeGuid,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool ConnectBlueprintPins(
        const FString& BlueprintPath,
        const FString& GraphName,
        const FString& FromNodeGuid,
        const FString& FromPinName,
        const FString& ToNodeGuid,
        const FString& ToPinName,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    bool SetBlueprintPinDefault(
        const FString& BlueprintPath,
        const FString& GraphName,
        const FString& NodeGuid,
        const FString& PinName,
        const FString& ValueAsString,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Blueprint")
    FString ExecuteBlueprintCommands(
        const FString& BlueprintPath,
        const FString& CommandsJson,
        bool bAutoCompile,
        bool bAutoSave
    );

    // ---------------------------------------------------------------------
    // WorldOps (Editor)
    // ---------------------------------------------------------------------
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|World")
    bool LoadMap(const FString& MapPath, FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|World")
    AActor* SpawnActorByClassPath(
        const FString& ClassPath,
        const FTransform& Transform,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|World")
    AActor* FindActorByName(const FString& ActorName);

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|World")
    bool DestroyActorByName(const FString& ActorName, FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|World")
    bool SetActorPropertyByString(
        const FString& ActorName,
        const FName& PropertyName,
        const FString& ValueAsString,
        FString& OutError
    );

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|World")
    bool SetActorTransformByName(
        const FString& ActorName,
        const FTransform& Transform,
        FString& OutError
    );

    // ---------------------------------------------------------------------
    // EditorOps
    // ---------------------------------------------------------------------
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Editor")
    TArray<FString> ListDirtyPackages() const;

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Editor")
    bool SaveDirtyPackages(bool bPromptUser, FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Editor")
    bool UndoLastTransaction(FString& OutError);

    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Editor")
    bool RedoLastTransaction(FString& OutError);

    // ---------------------------------------------------------------------
    // ValidationOps
    // ---------------------------------------------------------------------
    UFUNCTION(BlueprintCallable, Category = "UnrealCopilot|Skill|Validation")
    FString CompileAllBlueprintsSummary();

private:
    UObject* LoadAsset(const FString& AssetPath, FString& OutError) const;
    UBlueprint* LoadBlueprint(const FString& BlueprintPath, FString& OutError) const;
    UWorld* GetEditorWorld(FString& OutError) const;
    bool SetObjectPropertyByString(
        UObject* Target,
        const FName& PropertyName,
        const FString& ValueAsString,
        FString& OutError
    ) const;
};


