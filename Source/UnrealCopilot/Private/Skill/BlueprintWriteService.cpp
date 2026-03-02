// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Skill/BlueprintWriteService.h"

#include "Editor.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraph/EdGraphSchema.h"
#include "EdGraphSchema_K2.h"
#include "Engine/Blueprint.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "UObject/NoExportTypes.h"

bool FBlueprintWriteService::EnsureWriteContext(FString& OutError)
{
    if (!GEditor)
    {
        OutError = TEXT("GEditor is not available.");
        return false;
    }

    if (!IsInGameThread())
    {
        OutError = TEXT("Blueprint write operations must run on game thread.");
        return false;
    }

    if (GEditor->PlayWorld != nullptr)
    {
        OutError = TEXT("Blueprint write operations are blocked during PIE.");
        return false;
    }

    return true;
}

bool FBlueprintWriteService::AddVariable(
    UBlueprint* Blueprint,
    const FName& VariableName,
    const FString& VariableType,
    const FString& DefaultValue,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    if (VariableName.IsNone())
    {
        OutError = TEXT("VariableName is empty.");
        return false;
    }

    if (FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, VariableName) != INDEX_NONE)
    {
        OutError = TEXT("Variable already exists.");
        return false;
    }

    FEdGraphPinType PinType;
    if (!ResolveVariableType(VariableType, PinType, OutError))
    {
        return false;
    }

    Blueprint->Modify();
    FBlueprintEditorUtils::AddMemberVariable(Blueprint, VariableName, PinType, DefaultValue);

    if (FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, VariableName) == INDEX_NONE)
    {
        OutError = TEXT("Failed to add variable.");
        return false;
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool FBlueprintWriteService::RemoveVariable(
    UBlueprint* Blueprint,
    const FName& VariableName,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    if (FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, VariableName) == INDEX_NONE)
    {
        OutError = TEXT("Variable not found.");
        return false;
    }

    Blueprint->Modify();
    FBlueprintEditorUtils::RemoveMemberVariable(Blueprint, VariableName);

    if (FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, VariableName) != INDEX_NONE)
    {
        OutError = TEXT("Failed to remove variable.");
        return false;
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool FBlueprintWriteService::RenameVariable(
    UBlueprint* Blueprint,
    const FName& OldVariableName,
    const FName& NewVariableName,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    if (OldVariableName.IsNone() || NewVariableName.IsNone())
    {
        OutError = TEXT("Variable names must not be empty.");
        return false;
    }

    if (FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, OldVariableName) == INDEX_NONE)
    {
        OutError = TEXT("Source variable not found.");
        return false;
    }

    if (FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, NewVariableName) != INDEX_NONE)
    {
        OutError = TEXT("Target variable already exists.");
        return false;
    }

    Blueprint->Modify();
    FBlueprintEditorUtils::RenameMemberVariable(Blueprint, OldVariableName, NewVariableName);

    if (FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, OldVariableName) != INDEX_NONE ||
        FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, NewVariableName) == INDEX_NONE)
    {
        OutError = TEXT("Failed to rename variable.");
        return false;
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool FBlueprintWriteService::SetVariableDefault(
    UBlueprint* Blueprint,
    const FName& VariableName,
    const FString& DefaultValue,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    const int32 VarIndex = FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, VariableName);
    if (VarIndex == INDEX_NONE || !Blueprint->NewVariables.IsValidIndex(VarIndex))
    {
        OutError = TEXT("Variable not found.");
        return false;
    }

    Blueprint->Modify();
    Blueprint->NewVariables[VarIndex].DefaultValue = DefaultValue;
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool FBlueprintWriteService::AddGraph(
    UBlueprint* Blueprint,
    const FString& GraphName,
    const FString& GraphType,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    if (GraphName.IsEmpty())
    {
        OutError = TEXT("GraphName is empty.");
        return false;
    }

    if (FindGraph(Blueprint, GraphName) != nullptr)
    {
        OutError = TEXT("Graph already exists.");
        return false;
    }

    const FString TypeLower = GraphType.IsEmpty() ? TEXT("function") : GraphType.ToLower();
    UEdGraph* NewGraph = FBlueprintEditorUtils::CreateNewGraph(
        Blueprint,
        FName(*GraphName),
        UEdGraph::StaticClass(),
        UEdGraphSchema_K2::StaticClass()
    );
    if (!NewGraph)
    {
        OutError = TEXT("Failed to create graph object.");
        return false;
    }

    Blueprint->Modify();
    if (TypeLower == TEXT("function"))
    {
        FBlueprintEditorUtils::AddFunctionGraph(
            Blueprint,
            NewGraph,
            true,
            static_cast<UClass*>(nullptr)
        );
    }
    else if (TypeLower == TEXT("macro"))
    {
        FBlueprintEditorUtils::AddMacroGraph(
            Blueprint,
            NewGraph,
            true,
            static_cast<UClass*>(nullptr)
        );
    }
    else if (TypeLower == TEXT("event") || TypeLower == TEXT("eventgraph") || TypeLower == TEXT("ubergraph"))
    {
        FBlueprintEditorUtils::AddUbergraphPage(Blueprint, NewGraph);
    }
    else
    {
        OutError = TEXT("Unsupported GraphType. Use function/macro/eventgraph.");
        return false;
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool FBlueprintWriteService::RemoveGraph(
    UBlueprint* Blueprint,
    const FString& GraphName,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    UEdGraph* Graph = FindGraph(Blueprint, GraphName);
    if (!Graph)
    {
        OutError = TEXT("Graph not found.");
        return false;
    }

    Blueprint->Modify();
    Graph->Modify();

    int32 RemovedCount = 0;
    RemovedCount += Blueprint->UbergraphPages.Remove(Graph);
    RemovedCount += Blueprint->FunctionGraphs.Remove(Graph);
    RemovedCount += Blueprint->MacroGraphs.Remove(Graph);
    if (RemovedCount <= 0)
    {
        OutError = TEXT("Failed to remove graph.");
        return false;
    }

    Graph->Rename(nullptr, GetTransientPackage(), REN_DontCreateRedirectors);
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool FBlueprintWriteService::RenameGraph(
    UBlueprint* Blueprint,
    const FString& OldGraphName,
    const FString& NewGraphName,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    if (OldGraphName.IsEmpty() || NewGraphName.IsEmpty())
    {
        OutError = TEXT("Graph names must not be empty.");
        return false;
    }

    UEdGraph* Graph = FindGraph(Blueprint, OldGraphName);
    if (!Graph)
    {
        OutError = TEXT("Source graph not found.");
        return false;
    }

    if (FindGraph(Blueprint, NewGraphName) != nullptr)
    {
        OutError = TEXT("Target graph already exists.");
        return false;
    }

    Graph->Modify();
    if (!Graph->Rename(*NewGraphName, Blueprint, REN_DontCreateRedirectors))
    {
        OutError = TEXT("Failed to rename graph.");
        return false;
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool FBlueprintWriteService::AddNode(
    UBlueprint* Blueprint,
    const FString& GraphName,
    const FString& NodeClassPath,
    int32 NodePosX,
    int32 NodePosY,
    FString& OutNodeGuid,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    UEdGraph* Graph = FindGraph(Blueprint, GraphName);
    if (!Graph)
    {
        OutError = TEXT("Graph not found.");
        return false;
    }

    UClass* NodeClass = LoadObject<UClass>(nullptr, *NodeClassPath);
    if (!NodeClass || !NodeClass->IsChildOf(UEdGraphNode::StaticClass()))
    {
        OutError = TEXT("Node class is invalid.");
        return false;
    }

    Blueprint->Modify();
    Graph->Modify();

    UEdGraphNode* NewNode = NewObject<UEdGraphNode>(Graph, NodeClass, NAME_None, RF_Transactional);
    if (!NewNode)
    {
        OutError = TEXT("Failed to create node.");
        return false;
    }

    NewNode->CreateNewGuid();
    NewNode->PostPlacedNewNode();
    NewNode->AllocateDefaultPins();
    Graph->AddNode(NewNode, true, false);
    NewNode->NodePosX = NodePosX;
    NewNode->NodePosY = NodePosY;

    OutNodeGuid = NewNode->NodeGuid.ToString(EGuidFormats::DigitsWithHyphensLower);
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool FBlueprintWriteService::RemoveNode(
    UBlueprint* Blueprint,
    const FString& GraphName,
    const FString& NodeGuid,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    UEdGraph* Graph = FindGraph(Blueprint, GraphName);
    if (!Graph)
    {
        OutError = TEXT("Graph not found.");
        return false;
    }

    UEdGraphNode* Node = FindNodeByGuid(Graph, NodeGuid, OutError);
    if (!Node)
    {
        return false;
    }

    Blueprint->Modify();
    Graph->Modify();
    Node->Modify();

    Graph->RemoveNode(Node);
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool FBlueprintWriteService::ConnectPins(
    UBlueprint* Blueprint,
    const FString& GraphName,
    const FString& FromNodeGuid,
    const FString& FromPinName,
    const FString& ToNodeGuid,
    const FString& ToPinName,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    UEdGraph* Graph = FindGraph(Blueprint, GraphName);
    if (!Graph)
    {
        OutError = TEXT("Graph not found.");
        return false;
    }

    UEdGraphNode* FromNode = FindNodeByGuid(Graph, FromNodeGuid, OutError);
    if (!FromNode)
    {
        return false;
    }
    UEdGraphNode* ToNode = FindNodeByGuid(Graph, ToNodeGuid, OutError);
    if (!ToNode)
    {
        return false;
    }

    UEdGraphPin* FromPin = FindPinByName(FromNode, FromPinName);
    if (!FromPin)
    {
        OutError = TEXT("From pin not found.");
        return false;
    }

    UEdGraphPin* ToPin = FindPinByName(ToNode, ToPinName);
    if (!ToPin)
    {
        OutError = TEXT("To pin not found.");
        return false;
    }

    const UEdGraphSchema* Schema = Graph->GetSchema();
    if (!Schema)
    {
        OutError = TEXT("Graph schema is not available.");
        return false;
    }

    Blueprint->Modify();
    Graph->Modify();

    if (!Schema->TryCreateConnection(FromPin, ToPin))
    {
        OutError = TEXT("Failed to connect pins.");
        return false;
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

bool FBlueprintWriteService::SetPinDefault(
    UBlueprint* Blueprint,
    const FString& GraphName,
    const FString& NodeGuid,
    const FString& PinName,
    const FString& ValueAsString,
    FString& OutError
)
{
    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null.");
        return false;
    }

    UEdGraph* Graph = FindGraph(Blueprint, GraphName);
    if (!Graph)
    {
        OutError = TEXT("Graph not found.");
        return false;
    }

    UEdGraphNode* Node = FindNodeByGuid(Graph, NodeGuid, OutError);
    if (!Node)
    {
        return false;
    }

    UEdGraphPin* Pin = FindPinByName(Node, PinName);
    if (!Pin)
    {
        OutError = TEXT("Pin not found.");
        return false;
    }

    if (Pin->Direction != EGPD_Input)
    {
        OutError = TEXT("Only input pins can set default value.");
        return false;
    }

    const UEdGraphSchema* Schema = Graph->GetSchema();
    Blueprint->Modify();
    Graph->Modify();
    Node->Modify();
    Pin->Modify();

    bool bSetBySchema = false;
    if (Schema)
    {
        Schema->TrySetDefaultValue(*Pin, ValueAsString);
        bSetBySchema = true;
    }

    if (!bSetBySchema)
    {
        Pin->DefaultValue = ValueAsString;
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    return true;
}

UEdGraph* FBlueprintWriteService::FindGraph(UBlueprint* Blueprint, const FString& GraphName)
{
    if (!Blueprint)
    {
        return nullptr;
    }

    auto MatchByName = [&GraphName](UEdGraph* Graph)
    {
        return Graph && Graph->GetName().Equals(GraphName, ESearchCase::IgnoreCase);
    };

    for (UEdGraph* Graph : Blueprint->UbergraphPages)
    {
        if (MatchByName(Graph))
        {
            return Graph;
        }
    }

    for (UEdGraph* Graph : Blueprint->FunctionGraphs)
    {
        if (MatchByName(Graph))
        {
            return Graph;
        }
    }

    for (UEdGraph* Graph : Blueprint->MacroGraphs)
    {
        if (MatchByName(Graph))
        {
            return Graph;
        }
    }

    return nullptr;
}

bool FBlueprintWriteService::ResolveVariableType(
    const FString& VariableType,
    FEdGraphPinType& OutPinType,
    FString& OutError
)
{
    const FString TypeRaw = VariableType.TrimStartAndEnd();
    if (TypeRaw.IsEmpty())
    {
        OutError = TEXT("VariableType is empty.");
        return false;
    }

    FString TypeName = TypeRaw;
    FString SubTypePath;
    TypeRaw.Split(TEXT(":"), &TypeName, &SubTypePath);
    TypeName = TypeName.TrimStartAndEnd().ToLower();
    SubTypePath = SubTypePath.TrimStartAndEnd();

    auto SetStructType = [&OutPinType](UScriptStruct* ScriptStruct)
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
        OutPinType.PinSubCategoryObject = ScriptStruct;
    };

    if (TypeName == TEXT("bool") || TypeName == TEXT("boolean"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
        return true;
    }
    if (TypeName == TEXT("int") || TypeName == TEXT("int32"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Int;
        return true;
    }
    if (TypeName == TEXT("int64"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Int64;
        return true;
    }
    if (TypeName == TEXT("float"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Float;
        return true;
    }
    if (TypeName == TEXT("double"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Double;
        return true;
    }
    if (TypeName == TEXT("name"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Name;
        return true;
    }
    if (TypeName == TEXT("string"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_String;
        return true;
    }
    if (TypeName == TEXT("text"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Text;
        return true;
    }
    if (TypeName == TEXT("vector"))
    {
        SetStructType(TBaseStructure<FVector>::Get());
        return true;
    }
    if (TypeName == TEXT("rotator"))
    {
        SetStructType(TBaseStructure<FRotator>::Get());
        return true;
    }
    if (TypeName == TEXT("transform"))
    {
        SetStructType(TBaseStructure<FTransform>::Get());
        return true;
    }
    if (TypeName == TEXT("object") || TypeName == TEXT("class") ||
        TypeName == TEXT("softobject") || TypeName == TEXT("softclass"))
    {
        if (SubTypePath.IsEmpty())
        {
            OutError = TEXT("Object/Class variable type requires subtype path, e.g. object:/Script/Engine.Texture2D");
            return false;
        }

        UClass* SubClass = LoadObject<UClass>(nullptr, *SubTypePath);
        if (!SubClass)
        {
            OutError = TEXT("Failed to load class from subtype path.");
            return false;
        }

        if (TypeName == TEXT("object"))
        {
            OutPinType.PinCategory = UEdGraphSchema_K2::PC_Object;
        }
        else if (TypeName == TEXT("class"))
        {
            OutPinType.PinCategory = UEdGraphSchema_K2::PC_Class;
        }
        else if (TypeName == TEXT("softobject"))
        {
            OutPinType.PinCategory = UEdGraphSchema_K2::PC_SoftObject;
        }
        else
        {
            OutPinType.PinCategory = UEdGraphSchema_K2::PC_SoftClass;
        }
        OutPinType.PinSubCategoryObject = SubClass;
        return true;
    }
    if (TypeName == TEXT("struct"))
    {
        if (SubTypePath.IsEmpty())
        {
            OutError = TEXT("Struct variable type requires subtype path, e.g. struct:/Script/CoreUObject.Vector");
            return false;
        }

        UScriptStruct* ScriptStruct = LoadObject<UScriptStruct>(nullptr, *SubTypePath);
        if (!ScriptStruct)
        {
            OutError = TEXT("Failed to load struct from subtype path.");
            return false;
        }

        SetStructType(ScriptStruct);
        return true;
    }

    OutError = TEXT("Unsupported VariableType.");
    return false;
}

UEdGraphNode* FBlueprintWriteService::FindNodeByGuid(
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
        OutError = TEXT("NodeGuid format is invalid.");
        return nullptr;
    }

    for (UEdGraphNode* Node : Graph->Nodes)
    {
        if (Node && Node->NodeGuid == ParsedGuid)
        {
            return Node;
        }
    }

    OutError = TEXT("Node not found.");
    return nullptr;
}

UEdGraphPin* FBlueprintWriteService::FindPinByName(UEdGraphNode* Node, const FString& PinName)
{
    if (!Node)
    {
        return nullptr;
    }

    for (UEdGraphPin* Pin : Node->Pins)
    {
        if (Pin && Pin->PinName.ToString().Equals(PinName, ESearchCase::IgnoreCase))
        {
            return Pin;
        }
    }
    return nullptr;
}
