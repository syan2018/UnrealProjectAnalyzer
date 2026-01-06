// Copyright Unreal Project Analyzer Team. All Rights Reserved.

#include "UnrealAnalyzerHttpRoutes.h"

#include "UnrealAnalyzerHttpUtils.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Async/Async.h"
#include "Dom/JsonObject.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "HAL/CriticalSection.h"
#include "Engine/Blueprint.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "HttpPath.h"
#include "HttpServerRequest.h"
#include "HttpServerResponse.h"
#include "IHttpRouter.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Misc/PackageName.h"
#include "HAL/FileManager.h"

namespace
{
	static FString JsonString(const TSharedRef<FJsonObject>& Obj)
	{
		FString Out;
		TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Out);
		FJsonSerializer::Serialize(Obj, Writer);
		return Out;
	}

	// ============================================================================
	// Health check endpoint
	// ============================================================================
	static bool HandleHealth(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("status"), TEXT("running"));
		Root->SetStringField(TEXT("plugin"), TEXT("UnrealProjectAnalyzer"));
		Root->SetStringField(TEXT("version"), TEXT("0.2.0"));
		
		// Add engine version info
		Root->SetStringField(TEXT("ue_version"), *FEngineVersion::Current().ToString());
		Root->SetNumberField(TEXT("ue_major"), ENGINE_MAJOR_VERSION);
		Root->SetNumberField(TEXT("ue_minor"), ENGINE_MINOR_VERSION);
		
		// Add project info
		Root->SetStringField(TEXT("project_name"), FApp::GetProjectName());
		
		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	static IAssetRegistry& GetAssetRegistry()
	{
		FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
		return AssetRegistryModule.Get();
	}

	static UBlueprint* LoadBlueprintFromPath(const FString& BpPath)
	{
		const FString ObjectPath = FUnrealAnalyzerHttpUtils::NormalizeToObjectPath(BpPath);
		return Cast<UBlueprint>(StaticLoadObject(UBlueprint::StaticClass(), nullptr, *ObjectPath));
	}

	static void AddClassChain(TArray<TSharedPtr<FJsonValue>>& OutHierarchy, UClass* StartClass, FString& OutFirstNativeParent)
	{
		OutFirstNativeParent = TEXT("");
		for (UClass* Cls = StartClass; Cls != nullptr; Cls = Cls->GetSuperClass())
		{
			TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
			Item->SetStringField(TEXT("name"), Cls->GetName());
			Item->SetStringField(TEXT("path"), Cls->GetPathName());
			Item->SetBoolField(TEXT("is_native"), Cls->IsNative());
			OutHierarchy.Add(MakeShared<FJsonValueObject>(Item));

			if (OutFirstNativeParent.IsEmpty() && Cls->IsNative())
			{
				OutFirstNativeParent = Cls->GetName();
			}
		}
	}

	static UEdGraph* FindBlueprintGraph(UBlueprint* Blueprint, const FString& GraphName)
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

	static bool HandleBlueprintSearch(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		const FString PatternRaw = FUnrealAnalyzerHttpUtils::GetOptionalQueryParam(Request, TEXT("pattern"), TEXT("*"));
		const FString ClassFilter = FUnrealAnalyzerHttpUtils::GetOptionalQueryParam(Request, TEXT("class"), TEXT(""));

		// Make a wildcard-friendly pattern: "Foo" -> "*Foo*"
		FString Pattern = PatternRaw;
		if (!Pattern.Contains(TEXT("*")) && !Pattern.Contains(TEXT("?")))
		{
			Pattern = FString::Printf(TEXT("*%s*"), *PatternRaw);
		}

		FARFilter Filter;
		Filter.ClassPaths.Add(UBlueprint::StaticClass()->GetClassPathName());
		Filter.bRecursiveClasses = true;

		TArray<FAssetData> Assets;
		GetAssetRegistry().GetAssets(Filter, Assets);

		TArray<TSharedPtr<FJsonValue>> Matches;
		Matches.Reserve(Assets.Num());

		for (const FAssetData& Asset : Assets)
		{
			const FString Name = Asset.AssetName.ToString();
			if (!Name.MatchesWildcard(Pattern))
			{
				continue;
			}

			const FString PackagePath = Asset.PackageName.ToString();
			if (!ClassFilter.IsEmpty())
			{
				UBlueprint* BP = LoadBlueprintFromPath(PackagePath);
				if (!BP || !BP->ParentClass)
				{
					continue;
				}

			// Very lightweight filter: match against any superclass name.
			bool bMatch = false;
			// 显式获取 UClass* 避免 TSubclassOf 和 UClass* 的三元运算符歧义
			UClass* StartClass = BP->GeneratedClass ? BP->GeneratedClass->GetSuperClass() : BP->ParentClass.Get();
			for (UClass* Cls = StartClass; Cls != nullptr; Cls = Cls->GetSuperClass())
				{
					if (Cls->GetName().Equals(ClassFilter, ESearchCase::IgnoreCase) || Cls->GetName().Contains(ClassFilter))
					{
						bMatch = true;
						break;
					}
				}
				if (!bMatch)
				{
					continue;
				}
			}

			TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
			Item->SetStringField(TEXT("name"), Name);
			Item->SetStringField(TEXT("path"), PackagePath);
			Item->SetStringField(TEXT("type"), TEXT("Blueprint"));
			Matches.Add(MakeShared<FJsonValueObject>(Item));
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetArrayField(TEXT("matches"), Matches);
		Root->SetNumberField(TEXT("count"), Matches.Num());

		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	static bool HandleBlueprintHierarchy(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString BpPath;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("bp_path"), BpPath))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: bp_path")));
			return true;
		}

		UBlueprint* Blueprint = LoadBlueprintFromPath(BpPath);
		if (!Blueprint || !Blueprint->GeneratedClass)
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Failed to load Blueprint"), EHttpServerResponseCodes::NotFound, BpPath));
			return true;
		}

		TArray<TSharedPtr<FJsonValue>> Hierarchy;
		FString FirstNativeParent;
		AddClassChain(Hierarchy, Blueprint->GeneratedClass, FirstNativeParent);

		// Collect blueprint parents (best-effort).
		TArray<TSharedPtr<FJsonValue>> BlueprintParents;
		for (UClass* Cls = Blueprint->GeneratedClass; Cls != nullptr; Cls = Cls->GetSuperClass())
		{
			if (UObject* GeneratedBy = Cls->ClassGeneratedBy)
			{
				TSharedRef<FJsonObject> Parent = MakeShared<FJsonObject>();
				Parent->SetStringField(TEXT("class"), Cls->GetName());
				Parent->SetStringField(TEXT("blueprint"), GeneratedBy->GetPathName());
				BlueprintParents.Add(MakeShared<FJsonValueObject>(Parent));
			}
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("blueprint"), FUnrealAnalyzerHttpUtils::NormalizeToPackagePath(BpPath));
		Root->SetArrayField(TEXT("hierarchy"), Hierarchy);
		Root->SetStringField(TEXT("native_parent"), FirstNativeParent);
		Root->SetArrayField(TEXT("blueprint_parents"), BlueprintParents);

		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	static bool HandleBlueprintDependencies(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString BpPath;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("bp_path"), BpPath))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: bp_path")));
			return true;
		}

		const FString PackagePath = FUnrealAnalyzerHttpUtils::NormalizeToPackagePath(BpPath);
		TArray<FName> Deps;
		GetAssetRegistry().GetDependencies(FName(*PackagePath), Deps, UE::AssetRegistry::EDependencyCategory::All);

		TArray<TSharedPtr<FJsonValue>> Dependencies;
		Dependencies.Reserve(Deps.Num());
		for (const FName& Dep : Deps)
		{
			Dependencies.Add(MakeShared<FJsonValueString>(Dep.ToString()));
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("blueprint"), PackagePath);
		Root->SetArrayField(TEXT("dependencies"), Dependencies);
		Root->SetNumberField(TEXT("count"), Dependencies.Num());

		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	static bool HandleBlueprintReferencers(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString BpPath;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("bp_path"), BpPath))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: bp_path")));
			return true;
		}

		const FString PackagePath = FUnrealAnalyzerHttpUtils::NormalizeToPackagePath(BpPath);
		TArray<FName> Refs;
		GetAssetRegistry().GetReferencers(FName(*PackagePath), Refs, UE::AssetRegistry::EDependencyCategory::All);

		TArray<TSharedPtr<FJsonValue>> Referencers;
		Referencers.Reserve(Refs.Num());
		for (const FName& Ref : Refs)
		{
			Referencers.Add(MakeShared<FJsonValueString>(Ref.ToString()));
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("blueprint"), PackagePath);
		Root->SetArrayField(TEXT("referencers"), Referencers);
		Root->SetNumberField(TEXT("count"), Referencers.Num());

		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	// ----------------------------------------------------------------------------
	// Async JSON job framework (avoid huge single HTTP responses)
	// Must be defined before handlers that use it.
	// ----------------------------------------------------------------------------
	enum class EAsyncJsonJobStatus : uint8
	{
		Pending,
		Running,
		Done,
		Error
	};

	struct FAsyncJsonJob
	{
		EAsyncJsonJobStatus Status = EAsyncJsonJobStatus::Pending;
		FString ResultJson;
		FString Error;
		FDateTime CreatedAt = FDateTime::UtcNow();
	};

	static FCriticalSection GAsyncJobsMutex;
	static TMap<FGuid, TSharedPtr<FAsyncJsonJob>> GAsyncJobs;

	static FString JobStatusToString(EAsyncJsonJobStatus Status)
	{
		switch (Status)
		{
		case EAsyncJsonJobStatus::Pending: return TEXT("pending");
		case EAsyncJsonJobStatus::Running: return TEXT("running");
		case EAsyncJsonJobStatus::Done: return TEXT("done");
		case EAsyncJsonJobStatus::Error: return TEXT("error");
		default: return TEXT("unknown");
		}
	}

	static void CleanupOldJobs_Locked()
	{
		// Best-effort cleanup; keep jobs for 10 minutes.
		const FDateTime Now = FDateTime::UtcNow();
		const FTimespan Ttl = FTimespan::FromMinutes(10);

		for (auto It = GAsyncJobs.CreateIterator(); It; ++It)
		{
			const TSharedPtr<FAsyncJsonJob>& Job = It.Value();
			if (!Job.IsValid())
			{
				It.RemoveCurrent();
				continue;
			}
			if ((Now - Job->CreatedAt) > Ttl)
			{
				It.RemoveCurrent();
			}
		}
	}

	// Helper: Build blueprint graph JSON (shared by sync and async handlers)
	static TSharedRef<FJsonObject> BuildBlueprintGraphJson(
		const FString& BpPath,
		const FString& GraphName,
		UBlueprint* Blueprint,
		UEdGraph* Graph
	)
	{
		TArray<TSharedPtr<FJsonValue>> Nodes;
		TArray<TSharedPtr<FJsonValue>> Connections;

		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (!Node)
			{
				continue;
			}

			const FString NodeId = Node->NodeGuid.ToString(EGuidFormats::Digits);

			TSharedRef<FJsonObject> NodeObj = MakeShared<FJsonObject>();
			NodeObj->SetStringField(TEXT("id"), NodeId);
			NodeObj->SetStringField(TEXT("type"), Node->GetClass()->GetName());
			NodeObj->SetStringField(TEXT("title"), Node->GetNodeTitle(ENodeTitleType::ListView).ToString());

			TArray<TSharedPtr<FJsonValue>> Pins;
			for (UEdGraphPin* Pin : Node->Pins)
			{
				if (!Pin)
				{
					continue;
				}

				TSharedRef<FJsonObject> PinObj = MakeShared<FJsonObject>();
				PinObj->SetStringField(TEXT("name"), Pin->PinName.ToString());
				PinObj->SetStringField(TEXT("direction"), Pin->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
				PinObj->SetStringField(TEXT("default"), Pin->DefaultValue);
				PinObj->SetStringField(TEXT("category"), Pin->PinType.PinCategory.ToString());
				PinObj->SetStringField(TEXT("sub_category"), Pin->PinType.PinSubCategory.ToString());

				TArray<TSharedPtr<FJsonValue>> Linked;
				for (UEdGraphPin* LinkedPin : Pin->LinkedTo)
				{
					if (!LinkedPin || !LinkedPin->GetOwningNode())
					{
						continue;
					}
					TSharedRef<FJsonObject> Link = MakeShared<FJsonObject>();
					Link->SetStringField(TEXT("node_id"), LinkedPin->GetOwningNode()->NodeGuid.ToString(EGuidFormats::Digits));
					Link->SetStringField(TEXT("pin_name"), LinkedPin->PinName.ToString());
					Linked.Add(MakeShared<FJsonValueObject>(Link));

					// Create a flat connection list (from output pins only).
					if (Pin->Direction == EGPD_Output)
					{
						TSharedRef<FJsonObject> Conn = MakeShared<FJsonObject>();
						Conn->SetStringField(TEXT("from_node"), NodeId);
						Conn->SetStringField(TEXT("from_pin"), Pin->PinName.ToString());
						Conn->SetStringField(TEXT("to_node"), LinkedPin->GetOwningNode()->NodeGuid.ToString(EGuidFormats::Digits));
						Conn->SetStringField(TEXT("to_pin"), LinkedPin->PinName.ToString());
						Connections.Add(MakeShared<FJsonValueObject>(Conn));
					}
				}
				PinObj->SetArrayField(TEXT("linked_to"), Linked);

				Pins.Add(MakeShared<FJsonValueObject>(PinObj));
			}
			NodeObj->SetArrayField(TEXT("pins"), Pins);

			Nodes.Add(MakeShared<FJsonValueObject>(NodeObj));
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("blueprint"), FUnrealAnalyzerHttpUtils::NormalizeToPackagePath(BpPath));
		Root->SetStringField(TEXT("graph"), GraphName);
		Root->SetArrayField(TEXT("nodes"), Nodes);
		Root->SetArrayField(TEXT("connections"), Connections);
		Root->SetNumberField(TEXT("node_count"), Nodes.Num());
		Root->SetNumberField(TEXT("connection_count"), Connections.Num());

		return Root;
	}

	static bool HandleBlueprintGraph(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString BpPath;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("bp_path"), BpPath))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: bp_path")));
			return true;
		}
		const FString GraphName = FUnrealAnalyzerHttpUtils::GetOptionalQueryParam(Request, TEXT("graph_name"), TEXT("EventGraph"));

		UBlueprint* Blueprint = LoadBlueprintFromPath(BpPath);
		if (!Blueprint)
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Failed to load Blueprint"), EHttpServerResponseCodes::NotFound, BpPath));
			return true;
		}

		UEdGraph* Graph = FindBlueprintGraph(Blueprint, GraphName);
		if (!Graph)
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Graph not found"), EHttpServerResponseCodes::NotFound, GraphName));
			return true;
		}

		// Check node count - if large, use async mode to avoid socket_send_failure
		const int32 NodeCount = Graph->Nodes.Num();
		const int32 AsyncThreshold = 50;  // Graphs with 50+ nodes go async

		if (NodeCount >= AsyncThreshold)
		{
			// Create async job
			const FGuid JobId = FGuid::NewGuid();
			const FString JobIdStr = JobId.ToString(EGuidFormats::Digits);

			TSharedPtr<FAsyncJsonJob> Job = MakeShared<FAsyncJsonJob>();
			Job->Status = EAsyncJsonJobStatus::Pending;
			Job->CreatedAt = FDateTime::UtcNow();

			{
				FScopeLock Lock(&GAsyncJobsMutex);
				CleanupOldJobs_Locked();
				GAsyncJobs.Add(JobId, Job);
			}

			// Capture values for async task
			const FString CapturedBpPath = BpPath;
			const FString CapturedGraphName = GraphName;

			// NOTE: Blueprint/Graph pointers are not safe to use in background threads.
			// We build the JSON on the game thread but store in job for chunked retrieval.
			Job->Status = EAsyncJsonJobStatus::Running;
			TSharedRef<FJsonObject> ResultJson = BuildBlueprintGraphJson(CapturedBpPath, CapturedGraphName, Blueprint, Graph);
			Job->ResultJson = JsonString(ResultJson);
			Job->Status = EAsyncJsonJobStatus::Done;

			// Return async job envelope
			TSharedRef<FJsonObject> Ack = MakeShared<FJsonObject>();
			Ack->SetBoolField(TEXT("ok"), true);
			Ack->SetStringField(TEXT("mode"), TEXT("async"));
			Ack->SetStringField(TEXT("job_id"), JobIdStr);
			Ack->SetStringField(TEXT("status_url"), FString::Printf(TEXT("/analysis/job/status?id=%s"), *JobIdStr));
			Ack->SetStringField(TEXT("result_url_template"), FString::Printf(TEXT("/analysis/job/result?id=%s&offset={offset}&limit={limit}"), *JobIdStr));
			Ack->SetNumberField(TEXT("estimated_nodes"), NodeCount);

			OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Ack)));
			return true;
		}

		// Small graph - return directly
		TSharedRef<FJsonObject> Root = BuildBlueprintGraphJson(BpPath, GraphName, Blueprint, Graph);
		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	static bool HandleBlueprintDetails(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString BpPath;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("bp_path"), BpPath))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: bp_path")));
			return true;
		}

		UBlueprint* Blueprint = LoadBlueprintFromPath(BpPath);
		if (!Blueprint)
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Failed to load Blueprint"), EHttpServerResponseCodes::NotFound, BpPath));
			return true;
		}

		// Variables - 直接使用 Blueprint->NewVariables (UE5 API)
		TArray<TSharedPtr<FJsonValue>> Variables;
		for (const FBPVariableDescription& Var : Blueprint->NewVariables)
		{
			TSharedRef<FJsonObject> VarObj = MakeShared<FJsonObject>();
			VarObj->SetStringField(TEXT("name"), Var.VarName.ToString());
			VarObj->SetStringField(TEXT("category"), Var.VarType.PinCategory.ToString());
			VarObj->SetStringField(TEXT("sub_category"), Var.VarType.PinSubCategory.ToString());
			VarObj->SetStringField(TEXT("default"), Var.DefaultValue);
			Variables.Add(MakeShared<FJsonValueObject>(VarObj));
		}

		// Functions (graph names)
		TArray<TSharedPtr<FJsonValue>> Functions;
		for (UEdGraph* Graph : Blueprint->FunctionGraphs)
		{
			if (Graph)
			{
				Functions.Add(MakeShared<FJsonValueString>(Graph->GetName()));
			}
		}

		// Components (SCS nodes)
		TArray<TSharedPtr<FJsonValue>> Components;
		if (Blueprint->SimpleConstructionScript)
		{
			const TArray<USCS_Node*>& AllNodes = Blueprint->SimpleConstructionScript->GetAllNodes();
			for (const USCS_Node* Node : AllNodes)
			{
				if (!Node)
				{
					continue;
				}
				TSharedRef<FJsonObject> CompObj = MakeShared<FJsonObject>();
				CompObj->SetStringField(TEXT("name"), Node->GetVariableName().ToString());
				CompObj->SetStringField(TEXT("class"), Node->ComponentClass ? Node->ComponentClass->GetName() : TEXT(""));
				// UE5: 使用 ParentComponentOrVariableName 替代已移除的 GetParent()
				CompObj->SetStringField(TEXT("attach_to"), Node->ParentComponentOrVariableName.ToString());
				Components.Add(MakeShared<FJsonValueObject>(CompObj));
			}
		}

		// Graphs (Ubergraph + function graphs)
		TArray<TSharedPtr<FJsonValue>> Graphs;
		for (UEdGraph* Graph : Blueprint->UbergraphPages)
		{
			if (Graph)
			{
				Graphs.Add(MakeShared<FJsonValueString>(Graph->GetName()));
			}
		}
		for (UEdGraph* Graph : Blueprint->FunctionGraphs)
		{
			if (Graph)
			{
				Graphs.Add(MakeShared<FJsonValueString>(Graph->GetName()));
			}
		}

		TSharedRef<FJsonObject> ParentClassObj = MakeShared<FJsonObject>();
		if (Blueprint->ParentClass)
		{
			ParentClassObj->SetStringField(TEXT("name"), Blueprint->ParentClass->GetName());
			ParentClassObj->SetStringField(TEXT("path"), Blueprint->ParentClass->GetPathName());
			ParentClassObj->SetBoolField(TEXT("is_native"), Blueprint->ParentClass->IsNative());
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("blueprint"), FUnrealAnalyzerHttpUtils::NormalizeToPackagePath(BpPath));
		Root->SetArrayField(TEXT("variables"), Variables);
		Root->SetArrayField(TEXT("functions"), Functions);
		Root->SetArrayField(TEXT("components"), Components);
		Root->SetArrayField(TEXT("graphs"), Graphs);
		Root->SetObjectField(TEXT("parent_class"), ParentClassObj);
		Root->SetNumberField(TEXT("variable_count"), Variables.Num());
		Root->SetNumberField(TEXT("function_count"), Functions.Num());
		Root->SetNumberField(TEXT("component_count"), Components.Num());

		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	// ============================================================================
	// Asset routes
	// ============================================================================

	static bool HandleAssetSearch(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		const FString PatternRaw = FUnrealAnalyzerHttpUtils::GetOptionalQueryParam(Request, TEXT("pattern"), TEXT("*"));
		const FString TypeFilter = FUnrealAnalyzerHttpUtils::GetOptionalQueryParam(Request, TEXT("type"), TEXT(""));

		FString Pattern = PatternRaw;
		if (!Pattern.Contains(TEXT("*")) && !Pattern.Contains(TEXT("?")))
		{
			Pattern = FString::Printf(TEXT("*%s*"), *PatternRaw);
		}

		TArray<FAssetData> Assets;
		if (!TypeFilter.IsEmpty())
		{
			// Try to interpret filter as class name ("SkeletalMesh", "Blueprint", ...)
			// UE5: ANY_PACKAGE 已废弃，使用 FindFirstObject 替代
			UClass* AssetClass = FindFirstObject<UClass>(*TypeFilter, EFindFirstObjectOptions::NativeFirst);
			if (AssetClass)
			{
				GetAssetRegistry().GetAssetsByClass(AssetClass->GetClassPathName(), Assets, true);
			}
			else
			{
				// Fallback: pull everything and filter by class display name later (slower, but robust)
				GetAssetRegistry().GetAllAssets(Assets, true);
			}
		}
		else
		{
			GetAssetRegistry().GetAllAssets(Assets, true);
		}

		TArray<TSharedPtr<FJsonValue>> Matches;
		for (const FAssetData& Asset : Assets)
		{
			const FString Name = Asset.AssetName.ToString();
			if (!Name.MatchesWildcard(Pattern))
			{
				continue;
			}

			const FString AssetTypeName = Asset.AssetClassPath.GetAssetName().ToString();
			if (!TypeFilter.IsEmpty())
			{
				if (!AssetTypeName.Equals(TypeFilter, ESearchCase::IgnoreCase) && !AssetTypeName.Contains(TypeFilter))
				{
					continue;
				}
			}

			TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
			Item->SetStringField(TEXT("name"), Name);
			Item->SetStringField(TEXT("path"), Asset.PackageName.ToString());
			Item->SetStringField(TEXT("type"), AssetTypeName);
			Matches.Add(MakeShared<FJsonValueObject>(Item));
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetArrayField(TEXT("matches"), Matches);
		Root->SetNumberField(TEXT("count"), Matches.Num());
		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	static bool HandleAssetReferences(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString AssetPath;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("asset_path"), AssetPath))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: asset_path")));
			return true;
		}

		const FString PackagePath = FUnrealAnalyzerHttpUtils::NormalizeToPackagePath(AssetPath);
		TArray<FName> Deps;
		GetAssetRegistry().GetDependencies(FName(*PackagePath), Deps, UE::AssetRegistry::EDependencyCategory::All);

		TArray<TSharedPtr<FJsonValue>> References;
		for (const FName& Dep : Deps)
		{
			References.Add(MakeShared<FJsonValueString>(Dep.ToString()));
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("asset"), PackagePath);
		Root->SetArrayField(TEXT("references"), References);
		Root->SetNumberField(TEXT("count"), References.Num());
		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	static bool HandleAssetReferencers(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString AssetPath;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("asset_path"), AssetPath))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: asset_path")));
			return true;
		}

		const FString PackagePath = FUnrealAnalyzerHttpUtils::NormalizeToPackagePath(AssetPath);
		TArray<FName> Refs;
		GetAssetRegistry().GetReferencers(FName(*PackagePath), Refs, UE::AssetRegistry::EDependencyCategory::All);

		TArray<TSharedPtr<FJsonValue>> Referencers;
		for (const FName& Ref : Refs)
		{
			Referencers.Add(MakeShared<FJsonValueString>(Ref.ToString()));
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("asset"), PackagePath);
		Root->SetArrayField(TEXT("referencers"), Referencers);
		Root->SetNumberField(TEXT("count"), Referencers.Num());
		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	static bool HandleAssetMetadata(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString AssetPath;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("asset_path"), AssetPath))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: asset_path")));
			return true;
		}

		const FString PackagePath = FUnrealAnalyzerHttpUtils::NormalizeToPackagePath(AssetPath);

		TArray<FAssetData> Assets;
		GetAssetRegistry().GetAssetsByPackageName(FName(*PackagePath), Assets);

		if (Assets.Num() == 0)
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Asset not found"), EHttpServerResponseCodes::NotFound, PackagePath));
			return true;
		}

		// Pick the first asset in the package.
		const FAssetData& Asset = Assets[0];
		const FString AssetName = Asset.AssetName.ToString();
		const FString AssetTypeName = Asset.AssetClassPath.GetAssetName().ToString();

		// Best-effort file size
		int64 FileSize = -1;
		FString Filename;
		if (FPackageName::TryConvertLongPackageNameToFilename(PackagePath, Filename, FPackageName::GetAssetPackageExtension()))
		{
			FileSize = IFileManager::Get().FileSize(*Filename);
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("name"), AssetName);
		Root->SetStringField(TEXT("path"), PackagePath);
		Root->SetStringField(TEXT("type"), AssetTypeName);
		if (FileSize >= 0)
		{
			Root->SetNumberField(TEXT("size"), static_cast<double>(FileSize));
		}
		Root->SetStringField(TEXT("object_path"), Asset.GetObjectPathString());

		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	// ============================================================================
	// Analysis routes
	// ============================================================================

	struct FRefChainNode
	{
		FString PackagePath;
		int32 Depth = 0;
	};

	static TSharedPtr<FJsonObject> BuildRefChainNodeJson(
		const FString& PackagePath,
		int32 Depth,
		int32 MaxDepth,
		const FString& Direction,
		TSet<FString>& Visited
	)
	{
		TSharedRef<FJsonObject> NodeObj = MakeShared<FJsonObject>();
		NodeObj->SetStringField(TEXT("path"), PackagePath);
		NodeObj->SetNumberField(TEXT("depth"), Depth);

		// Try to get type/name
		TArray<FAssetData> Assets;
		GetAssetRegistry().GetAssetsByPackageName(FName(*PackagePath), Assets);
		if (Assets.Num() > 0)
		{
			NodeObj->SetStringField(TEXT("name"), Assets[0].AssetName.ToString());
			NodeObj->SetStringField(TEXT("type"), Assets[0].AssetClassPath.GetAssetName().ToString());
		}

		if (Depth >= MaxDepth)
		{
			NodeObj->SetArrayField(TEXT("children"), {});
			return NodeObj;
		}

		TArray<FName> NextPackages;
		if (Direction.Equals(TEXT("references"), ESearchCase::IgnoreCase) || Direction.Equals(TEXT("both"), ESearchCase::IgnoreCase))
		{
			GetAssetRegistry().GetDependencies(FName(*PackagePath), NextPackages, UE::AssetRegistry::EDependencyCategory::All);
		}
		if (Direction.Equals(TEXT("referencers"), ESearchCase::IgnoreCase) || Direction.Equals(TEXT("both"), ESearchCase::IgnoreCase))
		{
			TArray<FName> Refs;
			GetAssetRegistry().GetReferencers(FName(*PackagePath), Refs, UE::AssetRegistry::EDependencyCategory::All);
			NextPackages.Append(Refs);
		}

		TArray<TSharedPtr<FJsonValue>> Children;
		for (const FName& Next : NextPackages)
		{
			const FString NextPath = Next.ToString();
			if (Visited.Contains(NextPath))
			{
				continue;
			}
			Visited.Add(NextPath);
			Children.Add(MakeShared<FJsonValueObject>(BuildRefChainNodeJson(NextPath, Depth + 1, MaxDepth, Direction, Visited)));
		}

		NodeObj->SetArrayField(TEXT("children"), Children);
		return NodeObj;
	}

	// Job status/result handlers defined after async framework (moved to earlier in file)
	static bool HandleAnalysisJobStatus(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString JobIdStr;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("id"), JobIdStr))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: id")));
			return true;
		}

		FGuid JobId;
		if (!FGuid::Parse(JobIdStr, JobId))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Invalid job id"), EHttpServerResponseCodes::BadRequest, JobIdStr));
			return true;
		}

		TSharedPtr<FAsyncJsonJob> Job;
		EAsyncJsonJobStatus StatusSnapshot = EAsyncJsonJobStatus::Pending;
		int32 TotalCharsSnapshot = 0;
		FString ErrorSnapshot;
		{
			FScopeLock Lock(&GAsyncJobsMutex);
			CleanupOldJobs_Locked();
			Job = GAsyncJobs.FindRef(JobId);
			if (Job.IsValid())
			{
				StatusSnapshot = Job->Status;
				if (StatusSnapshot == EAsyncJsonJobStatus::Done)
				{
					TotalCharsSnapshot = Job->ResultJson.Len();
				}
				if (StatusSnapshot == EAsyncJsonJobStatus::Error)
				{
					ErrorSnapshot = Job->Error;
				}
			}
		}

		if (!Job.IsValid())
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Job not found"), EHttpServerResponseCodes::NotFound, JobIdStr));
			return true;
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("id"), JobIdStr);
		Root->SetStringField(TEXT("status"), JobStatusToString(StatusSnapshot));
		if (StatusSnapshot == EAsyncJsonJobStatus::Done)
		{
			Root->SetNumberField(TEXT("total_chars"), TotalCharsSnapshot);
		}
		if (StatusSnapshot == EAsyncJsonJobStatus::Error)
		{
			Root->SetStringField(TEXT("error"), ErrorSnapshot);
		}

		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	static bool HandleAnalysisJobResult(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString JobIdStr;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("id"), JobIdStr))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: id")));
			return true;
		}

		FGuid JobId;
		if (!FGuid::Parse(JobIdStr, JobId))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Invalid job id"), EHttpServerResponseCodes::BadRequest, JobIdStr));
			return true;
		}

		const int32 Offset = FMath::Max(0, FCString::Atoi(*FUnrealAnalyzerHttpUtils::GetOptionalQueryParam(Request, TEXT("offset"), TEXT("0"))));
		const int32 Limit = FMath::Clamp(FCString::Atoi(*FUnrealAnalyzerHttpUtils::GetOptionalQueryParam(Request, TEXT("limit"), TEXT("65536"))), 1, 262144);

		TSharedPtr<FAsyncJsonJob> Job;
		EAsyncJsonJobStatus StatusSnapshot = EAsyncJsonJobStatus::Pending;
		FString ResultSnapshot;
		{
			FScopeLock Lock(&GAsyncJobsMutex);
			CleanupOldJobs_Locked();
			Job = GAsyncJobs.FindRef(JobId);
			if (Job.IsValid())
			{
				StatusSnapshot = Job->Status;
				if (StatusSnapshot == EAsyncJsonJobStatus::Done)
				{
					ResultSnapshot = Job->ResultJson;
				}
			}
		}

		if (!Job.IsValid())
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Job not found"), EHttpServerResponseCodes::NotFound, JobIdStr));
			return true;
		}

		if (StatusSnapshot != EAsyncJsonJobStatus::Done)
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Job not ready"), EHttpServerResponseCodes::Accepted, JobStatusToString(StatusSnapshot)));
			return true;
		}

		const int32 Total = ResultSnapshot.Len();
		const int32 SafeOffset = FMath::Clamp(Offset, 0, Total);
		const int32 SafeLen = FMath::Clamp(Limit, 1, FMath::Max(1, Total - SafeOffset));
		const FString Chunk = ResultSnapshot.Mid(SafeOffset, SafeLen);
		const int32 NextOffset = SafeOffset + SafeLen;

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("id"), JobIdStr);
		Root->SetNumberField(TEXT("offset"), SafeOffset);
		Root->SetNumberField(TEXT("limit"), SafeLen);
		Root->SetNumberField(TEXT("total_chars"), Total);
		Root->SetNumberField(TEXT("next_offset"), NextOffset);
		Root->SetBoolField(TEXT("done"), NextOffset >= Total);
		Root->SetStringField(TEXT("chunk"), Chunk);

		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}

	// ----------------------------------------------------------------------------
	// Reference chain (async, chunked retrieval)
	// ----------------------------------------------------------------------------
	static bool HandleReferenceChainAsync(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString Start;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("start"), Start))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: start")));
			return true;
		}

		const FString Direction = FUnrealAnalyzerHttpUtils::GetOptionalQueryParam(Request, TEXT("direction"), TEXT("both"));
		// Keep depth user-controlled but clamp to a reasonable upper bound to avoid pathological requests.
		const int32 MaxDepth = FMath::Clamp(
			FCString::Atoi(*FUnrealAnalyzerHttpUtils::GetOptionalQueryParam(Request, TEXT("depth"), TEXT("3"))),
			0, 10
		);
		const FString StartPackage = FUnrealAnalyzerHttpUtils::NormalizeToPackagePath(Start);

		const FGuid JobId = FGuid::NewGuid();
		const FString JobIdStr = JobId.ToString(EGuidFormats::Digits);

		TSharedPtr<FAsyncJsonJob> Job = MakeShared<FAsyncJsonJob>();
		Job->Status = EAsyncJsonJobStatus::Pending;
		Job->CreatedAt = FDateTime::UtcNow();

		{
			FScopeLock Lock(&GAsyncJobsMutex);
			CleanupOldJobs_Locked();
			GAsyncJobs.Add(JobId, Job);
		}

		Async(EAsyncExecution::ThreadPool, [JobId, Job, StartPackage, Direction, MaxDepth]()
		{
			// IMPORTANT:
			// AssetRegistry in-memory enumeration is not thread-safe.
			// Build the chain on the Game Thread to avoid UE crash:
			//   Assertion failed: IsInGameThread() || IsInAsyncLoadingThread() ...
			AsyncTask(ENamedThreads::GameThread, [JobId, Job, StartPackage, Direction, MaxDepth]()
			{
				{
					FScopeLock Lock(&GAsyncJobsMutex);
					if (Job.IsValid())
					{
						Job->Status = EAsyncJsonJobStatus::Running;
						Job->CreatedAt = FDateTime::UtcNow();
						Job->Error.Empty();
						Job->ResultJson.Empty();
					}
				}

				TSet<FString> Visited;
				Visited.Add(StartPackage);

				// Build chain (GameThread-safe)
				TSharedPtr<FJsonObject> Chain = BuildRefChainNodeJson(StartPackage, 0, FMath::Max(0, MaxDepth), Direction, Visited);

				TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
				Root->SetBoolField(TEXT("ok"), true);
				Root->SetStringField(TEXT("start"), StartPackage);
				Root->SetStringField(TEXT("direction"), Direction);
				Root->SetNumberField(TEXT("max_depth"), MaxDepth);
				Root->SetObjectField(TEXT("chain"), Chain);
				Root->SetNumberField(TEXT("unique_nodes"), Visited.Num());

				const FString Serialized = JsonString(Root);

				{
					FScopeLock Lock(&GAsyncJobsMutex);
					if (Job.IsValid())
					{
						Job->ResultJson = Serialized;
						Job->Status = EAsyncJsonJobStatus::Done;
					}
				}
			});
		});

		TSharedRef<FJsonObject> Ack = MakeShared<FJsonObject>();
		Ack->SetBoolField(TEXT("ok"), true);
		Ack->SetStringField(TEXT("mode"), TEXT("async"));
		Ack->SetStringField(TEXT("job_id"), JobIdStr);
		Ack->SetStringField(TEXT("status_url"), FString::Printf(TEXT("/analysis/job/status?id=%s"), *JobIdStr));
		Ack->SetStringField(TEXT("result_url_template"), FString::Printf(TEXT("/analysis/job/result?id=%s&offset={offset}&limit={limit}"), *JobIdStr));

		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Ack)));
		return true;
	}

	// Backward-compatible entrypoint: keep the old route name but return an async job.
	static bool HandleReferenceChain(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		return HandleReferenceChainAsync(Request, OnComplete);
	}

	static bool HandleCppClassUsage(const FHttpServerRequest& Request, const FHttpResultCallback& OnComplete)
	{
		FString ClassName;
		if (!FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(Request, TEXT("class"), ClassName))
		{
			OnComplete(FUnrealAnalyzerHttpUtils::JsonError(TEXT("Missing required query param: class")));
			return true;
		}

		// Minimal viable implementation: find Blueprints whose parent chain contains the class name.
		FARFilter Filter;
		Filter.ClassPaths.Add(UBlueprint::StaticClass()->GetClassPathName());
		Filter.bRecursiveClasses = true;

		TArray<FAssetData> Assets;
		GetAssetRegistry().GetAssets(Filter, Assets);

		TArray<TSharedPtr<FJsonValue>> AsParentClass;

		for (const FAssetData& Asset : Assets)
		{
			const FString PackagePath = Asset.PackageName.ToString();
			UBlueprint* BP = LoadBlueprintFromPath(PackagePath);
			if (!BP || !BP->GeneratedClass)
			{
				continue;
			}
			bool bMatch = false;
			for (UClass* Cls = BP->GeneratedClass->GetSuperClass(); Cls != nullptr; Cls = Cls->GetSuperClass())
			{
				if (Cls->GetName().Equals(ClassName, ESearchCase::IgnoreCase) || Cls->GetName().Contains(ClassName))
				{
					bMatch = true;
					break;
				}
			}
			if (!bMatch)
			{
				continue;
			}

			TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
			Item->SetStringField(TEXT("name"), Asset.AssetName.ToString());
			Item->SetStringField(TEXT("path"), PackagePath);
			AsParentClass.Add(MakeShared<FJsonValueObject>(Item));
		}

		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetBoolField(TEXT("ok"), true);
		Root->SetStringField(TEXT("class"), ClassName);
		Root->SetArrayField(TEXT("as_parent_class"), AsParentClass);

		// Placeholders for future refinement (components/variables/calls).
		Root->SetArrayField(TEXT("as_component"), {});
		Root->SetArrayField(TEXT("as_variable_type"), {});
		Root->SetArrayField(TEXT("as_function_call"), {});

		OnComplete(FUnrealAnalyzerHttpUtils::JsonResponse(JsonString(Root)));
		return true;
	}
}

void UnrealAnalyzerHttpRoutes::Register(TSharedPtr<IHttpRouter> Router)
{
	if (!Router.IsValid())
	{
		return;
	}

	// Health check endpoint (for MCP client connectivity verification).
	Router->BindRoute(
		FHttpPath(TEXT("/health")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleHealth)
	);

	// Blueprint tools (query-param based, to avoid path segment issues with "/Game/...").
	Router->BindRoute(
		FHttpPath(TEXT("/blueprint/search")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleBlueprintSearch)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/blueprint/hierarchy")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleBlueprintHierarchy)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/blueprint/dependencies")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleBlueprintDependencies)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/blueprint/referencers")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleBlueprintReferencers)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/blueprint/graph")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleBlueprintGraph)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/blueprint/details")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleBlueprintDetails)
	);

	// Asset tools (query-param based).
	Router->BindRoute(
		FHttpPath(TEXT("/asset/search")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleAssetSearch)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/asset/references")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleAssetReferences)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/asset/referencers")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleAssetReferencers)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/asset/metadata")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleAssetMetadata)
	);

	// Analysis tools.
	Router->BindRoute(
		FHttpPath(TEXT("/analysis/reference-chain")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleReferenceChain)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/analysis/reference-chain/async")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleReferenceChainAsync)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/analysis/job/status")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleAnalysisJobStatus)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/analysis/job/result")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleAnalysisJobResult)
	);
	Router->BindRoute(
		FHttpPath(TEXT("/analysis/cpp-class-usage")),
		EHttpServerRequestVerbs::VERB_GET,
		FHttpRequestHandler::CreateStatic(&HandleCppClassUsage)
	);
}

