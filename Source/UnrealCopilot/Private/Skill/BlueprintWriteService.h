// Copyright Unreal Copilot Team. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

class UBlueprint;
class UEdGraph;
class UEdGraphNode;
class UEdGraphPin;
struct FEdGraphPinType;

/**
 * Internal blueprint write helpers used by UCppSkillApiSubsystem.
 * This class centralizes low-level graph/variable write operations.
 */
class FBlueprintWriteService
{
public:
    static bool EnsureWriteContext(FString& OutError);

    static bool AddVariable(
        UBlueprint* Blueprint,
        const FName& VariableName,
        const FString& VariableType,
        const FString& DefaultValue,
        FString& OutError
    );

    static bool RemoveVariable(
        UBlueprint* Blueprint,
        const FName& VariableName,
        FString& OutError
    );

    static bool RenameVariable(
        UBlueprint* Blueprint,
        const FName& OldVariableName,
        const FName& NewVariableName,
        FString& OutError
    );

    static bool SetVariableDefault(
        UBlueprint* Blueprint,
        const FName& VariableName,
        const FString& DefaultValue,
        FString& OutError
    );

    static bool AddGraph(
        UBlueprint* Blueprint,
        const FString& GraphName,
        const FString& GraphType,
        FString& OutError
    );

    static bool RemoveGraph(
        UBlueprint* Blueprint,
        const FString& GraphName,
        FString& OutError
    );

    static bool RenameGraph(
        UBlueprint* Blueprint,
        const FString& OldGraphName,
        const FString& NewGraphName,
        FString& OutError
    );

    static bool AddNode(
        UBlueprint* Blueprint,
        const FString& GraphName,
        const FString& NodeClassPath,
        int32 NodePosX,
        int32 NodePosY,
        FString& OutNodeGuid,
        FString& OutError
    );

    static bool AddFunctionCallNode(
        UBlueprint* Blueprint,
        const FString& GraphName,
        const FString& FunctionPath,
        int32 NodePosX,
        int32 NodePosY,
        FString& OutNodeGuid,
        FString& OutError
    );

    static bool RemoveNode(
        UBlueprint* Blueprint,
        const FString& GraphName,
        const FString& NodeGuid,
        FString& OutError
    );

    static bool ConnectPins(
        UBlueprint* Blueprint,
        const FString& GraphName,
        const FString& FromNodeGuid,
        const FString& FromPinName,
        const FString& ToNodeGuid,
        const FString& ToPinName,
        FString& OutError
    );

    static bool SetPinDefault(
        UBlueprint* Blueprint,
        const FString& GraphName,
        const FString& NodeGuid,
        const FString& PinName,
        const FString& ValueAsString,
        FString& OutError
    );

    static UEdGraph* FindGraph(UBlueprint* Blueprint, const FString& GraphName);

private:
    static bool ResolveVariableType(
        const FString& VariableType,
        FEdGraphPinType& OutPinType,
        FString& OutError
    );

    static UEdGraphNode* FindNodeByGuid(
        UEdGraph* Graph,
        const FString& NodeGuid,
        FString& OutError
    );

    static UEdGraphPin* FindPinByName(UEdGraphNode* Node, const FString& PinName);
};
