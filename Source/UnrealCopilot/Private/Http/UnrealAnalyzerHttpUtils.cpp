// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Http/UnrealAnalyzerHttpUtils.h"

#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

bool FUnrealAnalyzerHttpUtils::GetRequiredQueryParam(const FHttpServerRequest& Request, const FString& Key, FString& OutValue)
{
	const FString* Found = Request.QueryParams.Find(Key);
	if (!Found || Found->IsEmpty())
	{
		return false;
	}
	OutValue = *Found;
	return true;
}

FString FUnrealAnalyzerHttpUtils::GetOptionalQueryParam(const FHttpServerRequest& Request, const FString& Key, const FString& DefaultValue)
{
	const FString* Found = Request.QueryParams.Find(Key);
	return (Found && !Found->IsEmpty()) ? *Found : DefaultValue;
}

TUniquePtr<FHttpServerResponse> FUnrealAnalyzerHttpUtils::JsonResponse(const FString& JsonBody, EHttpServerResponseCodes Code)
{
	TUniquePtr<FHttpServerResponse> Response = FHttpServerResponse::Create(JsonBody, TEXT("application/json"));
	Response->Code = Code;
	return Response;
}

TUniquePtr<FHttpServerResponse> FUnrealAnalyzerHttpUtils::JsonError(const FString& Message, EHttpServerResponseCodes Code, const FString& Detail)
{
	TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetBoolField(TEXT("ok"), false);
	Root->SetStringField(TEXT("error"), Message);
	if (!Detail.IsEmpty())
	{
		Root->SetStringField(TEXT("detail"), Detail);
	}

	FString OutJson;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutJson);
	FJsonSerializer::Serialize(Root, Writer);

	return JsonResponse(OutJson, Code);
}

FString FUnrealAnalyzerHttpUtils::NormalizeToPackagePath(const FString& AnyPath)
{
	// Input may be:
	// - /Game/Blueprints/BP_Player
	// - /Game/Blueprints/BP_Player.BP_Player
	// - /Game/Blueprints/BP_Player.BP_Player_C (rare)
	int32 DotIndex = INDEX_NONE;
	if (AnyPath.FindChar(TEXT('.'), DotIndex))
	{
		return AnyPath.Left(DotIndex);
	}
	return AnyPath;
}

FString FUnrealAnalyzerHttpUtils::NormalizeToObjectPath(const FString& PackageOrObjectPath)
{
	int32 DotIndex = INDEX_NONE;
	if (PackageOrObjectPath.FindChar(TEXT('.'), DotIndex))
	{
		return PackageOrObjectPath;
	}

	FString PackagePath = PackageOrObjectPath;
	FString AssetName;
	if (!PackagePath.Split(TEXT("/"), nullptr, &AssetName, ESearchCase::IgnoreCase, ESearchDir::FromEnd))
	{
		// Unusual, just return as-is
		return PackageOrObjectPath;
	}

	// "/Game/A" -> "/Game/A.A"
	return FString::Printf(TEXT("%s.%s"), *PackagePath, *AssetName);
}


