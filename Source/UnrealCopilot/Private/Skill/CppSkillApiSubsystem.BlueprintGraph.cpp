// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Skill/CppSkillApiSubsystem.h"

#include "Skill/BlueprintWriteService.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "Editor.h"
#include "Engine/Blueprint.h"
#include "ScopedTransaction.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
    static FString SerializeJsonObject(const TSharedRef<FJsonObject>& Obj)
    {
        FString Out;
        TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Out);
        FJsonSerializer::Serialize(Obj, Writer);
        return Out;
    }

    static bool ParseCommandsJson(
        const FString& CommandsJson,
        TArray<TSharedPtr<FJsonValue>>& OutCommands,
        FString& OutError
    )
    {
        OutCommands.Reset();
        if (CommandsJson.IsEmpty())
        {
            OutError = TEXT("CommandsJson is empty.");
            return false;
        }

        TSharedPtr<FJsonValue> RootValue;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(CommandsJson);
        if (!FJsonSerializer::Deserialize(Reader, RootValue) || !RootValue.IsValid())
        {
            OutError = TEXT("Failed to parse CommandsJson.");
            return false;
        }

        if (RootValue->Type == EJson::Array)
        {
            OutCommands = RootValue->AsArray();
            return true;
        }

        if (RootValue->Type == EJson::Object)
        {
            TSharedPtr<FJsonObject> RootObject = RootValue->AsObject();
            if (!RootObject.IsValid())
            {
                OutError = TEXT("CommandsJson root object is invalid.");
                return false;
            }

            if (RootObject->HasTypedField<EJson::Array>(TEXT("commands")))
            {
                OutCommands = RootObject->GetArrayField(TEXT("commands"));
                return true;
            }
        }

        OutError = TEXT("CommandsJson must be an array or {\"commands\": [...]} object.");
        return false;
    }

    static bool TryGetStringFieldAny(
        const TSharedPtr<FJsonObject>& Object,
        const TArray<FString>& Keys,
        FString& OutValue
    )
    {
        if (!Object.IsValid())
        {
            return false;
        }

        for (const FString& Key : Keys)
        {
            if (Object->TryGetStringField(Key, OutValue))
            {
                return true;
            }
        }
        return false;
    }

    static bool TryGetIntFieldAny(
        const TSharedPtr<FJsonObject>& Object,
        const TArray<FString>& Keys,
        int32& OutValue
    )
    {
        if (!Object.IsValid())
        {
            return false;
        }

        for (const FString& Key : Keys)
        {
            double NumericValue = 0.0;
            if (Object->TryGetNumberField(Key, NumericValue))
            {
                OutValue = static_cast<int32>(NumericValue);
                return true;
            }
        }
        return false;
    }

    static bool TryGetValueAsStringAny(
        const TSharedPtr<FJsonObject>& Object,
        const TArray<FString>& Keys,
        FString& OutValue
    )
    {
        if (!Object.IsValid())
        {
            return false;
        }

        for (const FString& Key : Keys)
        {
            const TSharedPtr<FJsonValue> Value = Object->TryGetField(Key);
            if (!Value.IsValid())
            {
                continue;
            }

            switch (Value->Type)
            {
            case EJson::String:
                OutValue = Value->AsString();
                return true;
            case EJson::Number:
                OutValue = FString::SanitizeFloat(Value->AsNumber());
                return true;
            case EJson::Boolean:
                OutValue = Value->AsBool() ? TEXT("true") : TEXT("false");
                return true;
            case EJson::Null:
                OutValue = TEXT("");
                return true;
            default:
                break;
            }
        }

        return false;
    }

    static bool RunBlueprintWriteTransaction(
        UBlueprint* Blueprint,
        const FText& TransactionText,
        const TFunctionRef<bool()>& Operation,
        FString& OutError
    )
    {
        if (!Blueprint)
        {
            OutError = TEXT("Blueprint is null.");
            return false;
        }

        bool bSuccess = false;
        {
            FScopedTransaction Transaction(TransactionText);
            Blueprint->Modify();
            bSuccess = Operation();
        }
        if (!bSuccess && GEditor)
        {
            GEditor->UndoTransaction();
        }
        return bSuccess;
    }

    static UEdGraphNode* FindNodeByGuidInGraph(
        UEdGraph* Graph,
        const FString& NodeGuid,
        FString& OutError
    )
    {
        if (!Graph)
        {
            OutError = TEXT("Graph is null.");
            return nullptr;
        }

        FGuid ParsedGuid;
        if (!FGuid::Parse(NodeGuid, ParsedGuid))
        {
            OutError = FString::Printf(TEXT("NodeGuid format is invalid: %s"), *NodeGuid);
            return nullptr;
        }

        for (UEdGraphNode* Node : Graph->Nodes)
        {
            if (Node && Node->NodeGuid == ParsedGuid)
            {
                return Node;
            }
        }

        OutError = FString::Printf(TEXT("Node not found. graph=%s node_guid=%s"), *Graph->GetName(), *NodeGuid);
        return nullptr;
    }

    static FString PinDirectionToTextForReport(const EEdGraphPinDirection Direction)
    {
        return Direction == EGPD_Input ? TEXT("input") : TEXT("output");
    }
}

bool UCppSkillApiSubsystem::AddBlueprintVariable(
    const FString& BlueprintPath,
    const FName& VariableName,
    const FString& VariableType,
    const FString& DefaultValue,
    FString& OutError
)
{
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "AddBlueprintVariable", "Add Blueprint Variable"),
        [&]()
        {
            return FBlueprintWriteService::AddVariable(
                Blueprint,
                VariableName,
                VariableType,
                DefaultValue,
                OutError
            );
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::RemoveBlueprintVariable(
    const FString& BlueprintPath,
    const FName& VariableName,
    FString& OutError
)
{
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "RemoveBlueprintVariable", "Remove Blueprint Variable"),
        [&]()
        {
            return FBlueprintWriteService::RemoveVariable(Blueprint, VariableName, OutError);
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::RenameBlueprintVariable(
    const FString& BlueprintPath,
    const FName& OldVariableName,
    const FName& NewVariableName,
    FString& OutError
)
{
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "RenameBlueprintVariable", "Rename Blueprint Variable"),
        [&]()
        {
            return FBlueprintWriteService::RenameVariable(
                Blueprint,
                OldVariableName,
                NewVariableName,
                OutError
            );
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::SetBlueprintVariableDefault(
    const FString& BlueprintPath,
    const FName& VariableName,
    const FString& DefaultValue,
    FString& OutError
)
{
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "SetBlueprintVariableDefault", "Set Blueprint Variable Default"),
        [&]()
        {
            return FBlueprintWriteService::SetVariableDefault(
                Blueprint,
                VariableName,
                DefaultValue,
                OutError
            );
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::AddBlueprintGraph(
    const FString& BlueprintPath,
    const FString& GraphName,
    const FString& GraphType,
    FString& OutError
)
{
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "AddBlueprintGraph", "Add Blueprint Graph"),
        [&]()
        {
            return FBlueprintWriteService::AddGraph(Blueprint, GraphName, GraphType, OutError);
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::RemoveBlueprintGraph(
    const FString& BlueprintPath,
    const FString& GraphName,
    FString& OutError
)
{
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "RemoveBlueprintGraph", "Remove Blueprint Graph"),
        [&]()
        {
            return FBlueprintWriteService::RemoveGraph(Blueprint, GraphName, OutError);
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::RenameBlueprintGraph(
    const FString& BlueprintPath,
    const FString& OldGraphName,
    const FString& NewGraphName,
    FString& OutError
)
{
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "RenameBlueprintGraph", "Rename Blueprint Graph"),
        [&]()
        {
            return FBlueprintWriteService::RenameGraph(
                Blueprint,
                OldGraphName,
                NewGraphName,
                OutError
            );
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::AddBlueprintNode(
    const FString& BlueprintPath,
    const FString& GraphName,
    const FString& NodeClassPath,
    int32 NodePosX,
    int32 NodePosY,
    FString& OutNodeGuid,
    FString& OutError
)
{
    OutNodeGuid.Empty();
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "AddBlueprintNode", "Add Blueprint Node"),
        [&]()
        {
            return FBlueprintWriteService::AddNode(
                Blueprint,
                GraphName,
                NodeClassPath,
                NodePosX,
                NodePosY,
                OutNodeGuid,
                OutError
            );
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::AddBlueprintFunctionCallNode(
    const FString& BlueprintPath,
    const FString& GraphName,
    const FString& FunctionPath,
    int32 NodePosX,
    int32 NodePosY,
    FString& OutNodeGuid,
    FString& OutError
)
{
    OutNodeGuid.Empty();
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "AddBlueprintFunctionCallNode", "Add Blueprint Function Call Node"),
        [&]()
        {
            return FBlueprintWriteService::AddFunctionCallNode(
                Blueprint,
                GraphName,
                FunctionPath,
                NodePosX,
                NodePosY,
                OutNodeGuid,
                OutError
            );
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::RemoveBlueprintNode(
    const FString& BlueprintPath,
    const FString& GraphName,
    const FString& NodeGuid,
    FString& OutError
)
{
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "RemoveBlueprintNode", "Remove Blueprint Node"),
        [&]()
        {
            return FBlueprintWriteService::RemoveNode(Blueprint, GraphName, NodeGuid, OutError);
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::ConnectBlueprintPins(
    const FString& BlueprintPath,
    const FString& GraphName,
    const FString& FromNodeGuid,
    const FString& FromPinName,
    const FString& ToNodeGuid,
    const FString& ToPinName,
    FString& OutError
)
{
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "ConnectBlueprintPins", "Connect Blueprint Pins"),
        [&]()
        {
            return FBlueprintWriteService::ConnectPins(
                Blueprint,
                GraphName,
                FromNodeGuid,
                FromPinName,
                ToNodeGuid,
                ToPinName,
                OutError
            );
        },
        OutError
    );
}

bool UCppSkillApiSubsystem::SetBlueprintPinDefault(
    const FString& BlueprintPath,
    const FString& GraphName,
    const FString& NodeGuid,
    const FString& PinName,
    const FString& ValueAsString,
    FString& OutError
)
{
    if (!FBlueprintWriteService::EnsureWriteContext(OutError))
    {
        return false;
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, OutError);
    if (!Blueprint)
    {
        return false;
    }

    return RunBlueprintWriteTransaction(
        Blueprint,
        NSLOCTEXT("UnrealCopilot", "SetBlueprintPinDefault", "Set Blueprint Pin Default"),
        [&]()
        {
            return FBlueprintWriteService::SetPinDefault(
                Blueprint,
                GraphName,
                NodeGuid,
                PinName,
                ValueAsString,
                OutError
            );
        },
        OutError
    );
}

FString UCppSkillApiSubsystem::ExecuteBlueprintOperation(
    const FString& BlueprintPath,
    const FString& OperationJson,
    bool bAutoCompile,
    bool bAutoSave
)
{
    TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("blueprint_path"), BlueprintPath);

    if (OperationJson.IsEmpty())
    {
        Report->SetBoolField(TEXT("ok"), false);
        Report->SetStringField(TEXT("error"), TEXT("OperationJson is empty."));
        return SerializeJsonObject(Report);
    }

    TSharedPtr<FJsonValue> RootValue;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(OperationJson);
    if (!FJsonSerializer::Deserialize(Reader, RootValue) || !RootValue.IsValid())
    {
        Report->SetBoolField(TEXT("ok"), false);
        Report->SetStringField(TEXT("error"), TEXT("Failed to parse OperationJson."));
        return SerializeJsonObject(Report);
    }

    FString CommandsJson;
    if (RootValue->Type == EJson::Object)
    {
        TArray<TSharedPtr<FJsonValue>> Commands;
        Commands.Add(RootValue);
        TSharedRef<FJsonObject> Wrapper = MakeShared<FJsonObject>();
        Wrapper->SetArrayField(TEXT("commands"), Commands);
        CommandsJson = SerializeJsonObject(Wrapper);
    }
    else if (RootValue->Type == EJson::Array)
    {
        CommandsJson = OperationJson;
    }
    else
    {
        Report->SetBoolField(TEXT("ok"), false);
        Report->SetStringField(TEXT("error"), TEXT("OperationJson must be an object or array."));
        return SerializeJsonObject(Report);
    }

    return ExecuteBlueprintCommands(BlueprintPath, CommandsJson, bAutoCompile, bAutoSave);
}

FString UCppSkillApiSubsystem::GetBlueprintNodePins(
    const FString& BlueprintPath,
    const FString& GraphName,
    const FString& NodeGuid
)
{
    TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("blueprint_path"), BlueprintPath);
    Report->SetStringField(TEXT("graph_name"), GraphName);
    Report->SetStringField(TEXT("node_guid"), NodeGuid);

    FString Error;
    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, Error);
    if (!Blueprint)
    {
        Report->SetBoolField(TEXT("ok"), false);
        Report->SetStringField(TEXT("error"), Error);
        return SerializeJsonObject(Report);
    }

    UEdGraph* Graph = FBlueprintWriteService::FindGraph(Blueprint, GraphName);
    if (!Graph)
    {
        Report->SetBoolField(TEXT("ok"), false);
        Report->SetStringField(TEXT("error"), FString::Printf(TEXT("Graph not found: %s"), *GraphName));
        return SerializeJsonObject(Report);
    }

    UEdGraphNode* Node = FindNodeByGuidInGraph(Graph, NodeGuid, Error);
    if (!Node)
    {
        Report->SetBoolField(TEXT("ok"), false);
        Report->SetStringField(TEXT("error"), Error);
        return SerializeJsonObject(Report);
    }

    TArray<TSharedPtr<FJsonValue>> Pins;
    Pins.Reserve(Node->Pins.Num());
    for (UEdGraphPin* Pin : Node->Pins)
    {
        if (!Pin)
        {
            continue;
        }

        TSharedRef<FJsonObject> PinObj = MakeShared<FJsonObject>();
        PinObj->SetStringField(TEXT("name"), Pin->PinName.ToString());
        PinObj->SetStringField(TEXT("direction"), PinDirectionToTextForReport(Pin->Direction));
        PinObj->SetStringField(TEXT("category"), Pin->PinType.PinCategory.ToString());
        PinObj->SetStringField(TEXT("sub_category"), Pin->PinType.PinSubCategory.ToString());
        PinObj->SetStringField(TEXT("default_value"), Pin->DefaultValue);
        PinObj->SetNumberField(TEXT("linked_to_count"), Pin->LinkedTo.Num());
        if (Pin->PinType.PinSubCategoryObject != nullptr)
        {
            PinObj->SetStringField(TEXT("sub_category_object"), Pin->PinType.PinSubCategoryObject->GetPathName());
        }
        Pins.Add(MakeShared<FJsonValueObject>(PinObj));
    }

    Report->SetBoolField(TEXT("ok"), true);
    Report->SetStringField(TEXT("graph"), Graph->GetName());
    Report->SetStringField(TEXT("node_title"), Node->GetNodeTitle(ENodeTitleType::ListView).ToString());
    Report->SetArrayField(TEXT("pins"), Pins);
    Report->SetNumberField(TEXT("pin_count"), Pins.Num());
    return SerializeJsonObject(Report);
}

FString UCppSkillApiSubsystem::ExecuteBlueprintCommands(
    const FString& BlueprintPath,
    const FString& CommandsJson,
    bool bAutoCompile,
    bool bAutoSave
)
{
    TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("blueprint_path"), BlueprintPath);
    Report->SetBoolField(TEXT("auto_compile"), bAutoCompile);
    Report->SetBoolField(TEXT("auto_save"), bAutoSave);

    FString Error;
    if (!FBlueprintWriteService::EnsureWriteContext(Error))
    {
        Report->SetBoolField(TEXT("ok"), false);
        Report->SetStringField(TEXT("error"), Error);
        return SerializeJsonObject(Report);
    }

    UBlueprint* Blueprint = LoadBlueprint(BlueprintPath, Error);
    if (!Blueprint)
    {
        Report->SetBoolField(TEXT("ok"), false);
        Report->SetStringField(TEXT("error"), Error);
        return SerializeJsonObject(Report);
    }

    TArray<TSharedPtr<FJsonValue>> Commands;
    if (!ParseCommandsJson(CommandsJson, Commands, Error))
    {
        Report->SetBoolField(TEXT("ok"), false);
        Report->SetStringField(TEXT("error"), Error);
        return SerializeJsonObject(Report);
    }

    TArray<TSharedPtr<FJsonValue>> StepReports;
    StepReports.Reserve(Commands.Num());

    bool bSuccess = true;
    bool bMutatingFailure = false;
    bool bRolledBack = false;
    bool bCompiled = false;
    bool bSaved = false;
    FString FinalError;
    int32 FailedIndex = INDEX_NONE;
    FString FailedOp;

    {
        FScopedTransaction Transaction(NSLOCTEXT("UnrealCopilot", "ExecuteBlueprintCommands", "Execute Blueprint Commands"));
        Blueprint->Modify();

        for (int32 Index = 0; Index < Commands.Num(); ++Index)
        {
            TSharedRef<FJsonObject> Step = MakeShared<FJsonObject>();
            Step->SetNumberField(TEXT("index"), Index);

            const TSharedPtr<FJsonValue>& CommandValue = Commands[Index];
            TSharedPtr<FJsonObject> CommandObject =
                CommandValue.IsValid() ? CommandValue->AsObject() : nullptr;

            bool bStepSuccess = false;
            FString StepError;
            FString Op;
            FString OpLower;

            if (!CommandObject.IsValid())
            {
                StepError = TEXT("Command item must be an object.");
            }
            else if (!TryGetStringFieldAny(
                CommandObject,
                { TEXT("op"), TEXT("operation"), TEXT("type") },
                Op
            ))
            {
                StepError = TEXT("Missing operation field (op).");
            }
            else
            {
                OpLower = Op.TrimStartAndEnd().ToLower();
                Step->SetStringField(TEXT("op"), OpLower);

                FString ContextGraph;
                if (TryGetStringFieldAny(CommandObject, { TEXT("graph_name"), TEXT("graph") }, ContextGraph))
                {
                    Step->SetStringField(TEXT("graph_name"), ContextGraph);
                }

                FString ContextNodeGuid;
                if (TryGetStringFieldAny(CommandObject, { TEXT("node_guid"), TEXT("guid") }, ContextNodeGuid))
                {
                    Step->SetStringField(TEXT("node_guid"), ContextNodeGuid);
                }

                FString ContextPinName;
                if (TryGetStringFieldAny(CommandObject, { TEXT("pin_name"), TEXT("pin") }, ContextPinName))
                {
                    Step->SetStringField(TEXT("pin_name"), ContextPinName);
                }

                if (OpLower == TEXT("add_variable") || OpLower == TEXT("add_blueprint_variable"))
                {
                    FString VariableName;
                    FString VariableType;
                    FString DefaultValue;

                    if (!TryGetStringFieldAny(CommandObject, { TEXT("variable_name"), TEXT("name") }, VariableName))
                    {
                        StepError = TEXT("Missing variable_name.");
                    }
                    else if (!TryGetStringFieldAny(CommandObject, { TEXT("variable_type"), TEXT("type") }, VariableType))
                    {
                        StepError = TEXT("Missing variable_type.");
                    }
                    else
                    {
                        TryGetValueAsStringAny(CommandObject, { TEXT("default_value"), TEXT("default") }, DefaultValue);
                        bStepSuccess = FBlueprintWriteService::AddVariable(
                            Blueprint,
                            FName(*VariableName),
                            VariableType,
                            DefaultValue,
                            StepError
                        );
                    }
                }
                else if (OpLower == TEXT("remove_variable") || OpLower == TEXT("remove_blueprint_variable"))
                {
                    FString VariableName;
                    if (!TryGetStringFieldAny(CommandObject, { TEXT("variable_name"), TEXT("name") }, VariableName))
                    {
                        StepError = TEXT("Missing variable_name.");
                    }
                    else
                    {
                        bStepSuccess = FBlueprintWriteService::RemoveVariable(
                            Blueprint,
                            FName(*VariableName),
                            StepError
                        );
                    }
                }
                else if (OpLower == TEXT("rename_variable") || OpLower == TEXT("rename_blueprint_variable"))
                {
                    FString OldName;
                    FString NewName;
                    if (!TryGetStringFieldAny(CommandObject, { TEXT("old_variable_name"), TEXT("old_name") }, OldName))
                    {
                        StepError = TEXT("Missing old_variable_name.");
                    }
                    else if (!TryGetStringFieldAny(CommandObject, { TEXT("new_variable_name"), TEXT("new_name") }, NewName))
                    {
                        StepError = TEXT("Missing new_variable_name.");
                    }
                    else
                    {
                        bStepSuccess = FBlueprintWriteService::RenameVariable(
                            Blueprint,
                            FName(*OldName),
                            FName(*NewName),
                            StepError
                        );
                    }
                }
                else if (OpLower == TEXT("set_variable_default") || OpLower == TEXT("set_blueprint_variable_default"))
                {
                    FString VariableName;
                    FString DefaultValue;
                    if (!TryGetStringFieldAny(CommandObject, { TEXT("variable_name"), TEXT("name") }, VariableName))
                    {
                        StepError = TEXT("Missing variable_name.");
                    }
                    else if (!TryGetValueAsStringAny(
                        CommandObject,
                        { TEXT("default_value"), TEXT("default"), TEXT("value"), TEXT("value_as_string") },
                        DefaultValue
                    ))
                    {
                        StepError = TEXT("Missing default value.");
                    }
                    else
                    {
                        bStepSuccess = FBlueprintWriteService::SetVariableDefault(
                            Blueprint,
                            FName(*VariableName),
                            DefaultValue,
                            StepError
                        );
                    }
                }
                else if (OpLower == TEXT("add_graph") || OpLower == TEXT("add_blueprint_graph"))
                {
                    FString GraphName;
                    FString GraphType = TEXT("function");
                    if (!TryGetStringFieldAny(CommandObject, { TEXT("graph_name"), TEXT("name") }, GraphName))
                    {
                        StepError = TEXT("Missing graph_name.");
                    }
                    else
                    {
                        TryGetStringFieldAny(CommandObject, { TEXT("graph_type"), TEXT("type") }, GraphType);
                        bStepSuccess = FBlueprintWriteService::AddGraph(
                            Blueprint,
                            GraphName,
                            GraphType,
                            StepError
                        );
                    }
                }
                else if (OpLower == TEXT("remove_graph") || OpLower == TEXT("remove_blueprint_graph"))
                {
                    FString GraphName;
                    if (!TryGetStringFieldAny(CommandObject, { TEXT("graph_name"), TEXT("name") }, GraphName))
                    {
                        StepError = TEXT("Missing graph_name.");
                    }
                    else
                    {
                        bStepSuccess = FBlueprintWriteService::RemoveGraph(Blueprint, GraphName, StepError);
                    }
                }
                else if (OpLower == TEXT("rename_graph") || OpLower == TEXT("rename_blueprint_graph"))
                {
                    FString OldName;
                    FString NewName;
                    if (!TryGetStringFieldAny(CommandObject, { TEXT("old_graph_name"), TEXT("old_name") }, OldName))
                    {
                        StepError = TEXT("Missing old_graph_name.");
                    }
                    else if (!TryGetStringFieldAny(CommandObject, { TEXT("new_graph_name"), TEXT("new_name") }, NewName))
                    {
                        StepError = TEXT("Missing new_graph_name.");
                    }
                    else
                    {
                        bStepSuccess = FBlueprintWriteService::RenameGraph(
                            Blueprint,
                            OldName,
                            NewName,
                            StepError
                        );
                    }
                }
                else if (OpLower == TEXT("add_node") || OpLower == TEXT("add_blueprint_node"))
                {
                    FString GraphName = TEXT("EventGraph");
                    FString NodeClassPath;
                    FString NodeGuid;
                    int32 NodePosX = 0;
                    int32 NodePosY = 0;

                    TryGetStringFieldAny(CommandObject, { TEXT("graph_name"), TEXT("graph") }, GraphName);
                    TryGetIntFieldAny(CommandObject, { TEXT("node_pos_x"), TEXT("x") }, NodePosX);
                    TryGetIntFieldAny(CommandObject, { TEXT("node_pos_y"), TEXT("y") }, NodePosY);

                    if (!TryGetStringFieldAny(
                        CommandObject,
                        { TEXT("node_class_path"), TEXT("class_path"), TEXT("node_class") },
                        NodeClassPath
                    ))
                    {
                        StepError = TEXT("Missing node_class_path.");
                    }
                    else
                    {
                        bStepSuccess = FBlueprintWriteService::AddNode(
                            Blueprint,
                            GraphName,
                            NodeClassPath,
                            NodePosX,
                            NodePosY,
                            NodeGuid,
                            StepError
                        );
                        if (bStepSuccess)
                        {
                            Step->SetStringField(TEXT("node_guid"), NodeGuid);
                        }
                    }
                }
                else if (OpLower == TEXT("add_call_function_node") || OpLower == TEXT("add_blueprint_function_call_node"))
                {
                    FString GraphName = TEXT("EventGraph");
                    FString FunctionPath;
                    FString NodeGuid;
                    int32 NodePosX = 0;
                    int32 NodePosY = 0;

                    TryGetStringFieldAny(CommandObject, { TEXT("graph_name"), TEXT("graph") }, GraphName);
                    TryGetIntFieldAny(CommandObject, { TEXT("node_pos_x"), TEXT("x") }, NodePosX);
                    TryGetIntFieldAny(CommandObject, { TEXT("node_pos_y"), TEXT("y") }, NodePosY);

                    if (!TryGetStringFieldAny(
                        CommandObject,
                        { TEXT("function_path"), TEXT("function"), TEXT("target_function") },
                        FunctionPath
                    ))
                    {
                        StepError = TEXT("Missing function_path.");
                    }
                    else
                    {
                        bStepSuccess = FBlueprintWriteService::AddFunctionCallNode(
                            Blueprint,
                            GraphName,
                            FunctionPath,
                            NodePosX,
                            NodePosY,
                            NodeGuid,
                            StepError
                        );
                        if (bStepSuccess)
                        {
                            Step->SetStringField(TEXT("node_guid"), NodeGuid);
                            Step->SetStringField(TEXT("function_path"), FunctionPath);
                        }
                    }
                }
                else if (OpLower == TEXT("remove_node") || OpLower == TEXT("remove_blueprint_node"))
                {
                    FString GraphName = TEXT("EventGraph");
                    FString NodeGuid;
                    TryGetStringFieldAny(CommandObject, { TEXT("graph_name"), TEXT("graph") }, GraphName);
                    if (!TryGetStringFieldAny(CommandObject, { TEXT("node_guid"), TEXT("guid") }, NodeGuid))
                    {
                        StepError = TEXT("Missing node_guid.");
                    }
                    else
                    {
                        bStepSuccess = FBlueprintWriteService::RemoveNode(
                            Blueprint,
                            GraphName,
                            NodeGuid,
                            StepError
                        );
                    }
                }
                else if (OpLower == TEXT("connect_pins") || OpLower == TEXT("connect_blueprint_pins"))
                {
                    FString GraphName = TEXT("EventGraph");
                    FString FromNodeGuid;
                    FString FromPinName;
                    FString ToNodeGuid;
                    FString ToPinName;

                    TryGetStringFieldAny(CommandObject, { TEXT("graph_name"), TEXT("graph") }, GraphName);

                    const bool bHasFromNode =
                        TryGetStringFieldAny(CommandObject, { TEXT("from_node_guid"), TEXT("from_guid") }, FromNodeGuid);
                    const bool bHasFromPin =
                        TryGetStringFieldAny(CommandObject, { TEXT("from_pin_name"), TEXT("from_pin") }, FromPinName);
                    const bool bHasToNode =
                        TryGetStringFieldAny(CommandObject, { TEXT("to_node_guid"), TEXT("to_guid") }, ToNodeGuid);
                    const bool bHasToPin =
                        TryGetStringFieldAny(CommandObject, { TEXT("to_pin_name"), TEXT("to_pin") }, ToPinName);

                    if (!bHasFromNode || !bHasFromPin || !bHasToNode || !bHasToPin)
                    {
                        StepError = TEXT("connect_pins requires from_node_guid/from_pin_name/to_node_guid/to_pin_name.");
                    }
                    else
                    {
                        Step->SetStringField(TEXT("from_node_guid"), FromNodeGuid);
                        Step->SetStringField(TEXT("from_pin_name"), FromPinName);
                        Step->SetStringField(TEXT("to_node_guid"), ToNodeGuid);
                        Step->SetStringField(TEXT("to_pin_name"), ToPinName);
                        bStepSuccess = FBlueprintWriteService::ConnectPins(
                            Blueprint,
                            GraphName,
                            FromNodeGuid,
                            FromPinName,
                            ToNodeGuid,
                            ToPinName,
                            StepError
                        );
                    }
                }
                else if (OpLower == TEXT("set_pin_default") || OpLower == TEXT("set_blueprint_pin_default"))
                {
                    FString GraphName = TEXT("EventGraph");
                    FString NodeGuid;
                    FString PinName;
                    FString ValueAsString;
                    TryGetStringFieldAny(CommandObject, { TEXT("graph_name"), TEXT("graph") }, GraphName);

                    const bool bHasGuid = TryGetStringFieldAny(CommandObject, { TEXT("node_guid"), TEXT("guid") }, NodeGuid);
                    const bool bHasPin = TryGetStringFieldAny(CommandObject, { TEXT("pin_name"), TEXT("pin") }, PinName);
                    const bool bHasValue = TryGetValueAsStringAny(
                        CommandObject,
                        { TEXT("value_as_string"), TEXT("value"), TEXT("default_value") },
                        ValueAsString
                    );

                    if (!bHasGuid || !bHasPin || !bHasValue)
                    {
                        StepError = TEXT("set_pin_default requires node_guid/pin_name/value.");
                    }
                    else
                    {
                        bStepSuccess = FBlueprintWriteService::SetPinDefault(
                            Blueprint,
                            GraphName,
                            NodeGuid,
                            PinName,
                            ValueAsString,
                            StepError
                        );
                    }
                }
                else
                {
                    StepError = FString::Printf(TEXT("Unsupported operation: %s"), *OpLower);
                }
            }

            Step->SetBoolField(TEXT("ok"), bStepSuccess);
            if (!OpLower.IsEmpty() && !Step->HasField(TEXT("op")))
            {
                Step->SetStringField(TEXT("op"), OpLower);
            }
            if (!bStepSuccess)
            {
                Step->SetStringField(TEXT("error"), StepError);
                bSuccess = false;
                bMutatingFailure = true;
                FinalError = StepError;
                FailedIndex = Index;
                FailedOp = OpLower;
            }
            StepReports.Add(MakeShared<FJsonValueObject>(Step));

            if (!bStepSuccess)
            {
                break;
            }
        }
    }

    if (bSuccess && bAutoCompile)
    {
        FString CompileError;
        bCompiled = CompileBlueprint(BlueprintPath, CompileError);
        if (!bCompiled)
        {
            bSuccess = false;
            bMutatingFailure = true;
            FinalError = CompileError.IsEmpty() ? TEXT("CompileBlueprint failed.") : CompileError;
        }
    }

    if (bMutatingFailure && GEditor)
    {
        bRolledBack = GEditor->UndoTransaction();
    }

    if (bSuccess && bAutoSave)
    {
        FString SaveError;
        bSaved = SaveBlueprint(BlueprintPath, SaveError);
        if (!bSaved)
        {
            bSuccess = false;
            FinalError = SaveError.IsEmpty() ? TEXT("SaveBlueprint failed.") : SaveError;
        }
    }

    Report->SetBoolField(TEXT("ok"), bSuccess);
    Report->SetNumberField(TEXT("total_commands"), Commands.Num());
    Report->SetNumberField(TEXT("executed_commands"), StepReports.Num());
    Report->SetBoolField(TEXT("rolled_back"), bRolledBack);
    Report->SetBoolField(TEXT("compiled"), bAutoCompile ? bCompiled : false);
    Report->SetBoolField(TEXT("saved"), bAutoSave ? bSaved : false);
    Report->SetArrayField(TEXT("steps"), StepReports);

    if (!FinalError.IsEmpty())
    {
        Report->SetStringField(TEXT("error"), FinalError);
        if (FailedIndex != INDEX_NONE)
        {
            Report->SetNumberField(TEXT("failed_index"), FailedIndex);
        }
        if (!FailedOp.IsEmpty())
        {
            Report->SetStringField(TEXT("failed_op"), FailedOp);
        }
    }

    return SerializeJsonObject(Report);
}
