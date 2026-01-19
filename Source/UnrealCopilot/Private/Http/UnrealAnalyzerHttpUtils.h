// Copyright Unreal Copilot Team. All Rights Reserved.
//
// Small HTTP/JSON helpers for UnrealCopilot routes.

#pragma once

#include "CoreMinimal.h"
#include "HttpServerResponse.h"
#include "HttpServerRequest.h"

class FUnrealAnalyzerHttpUtils
{
public:
	/** Read a required query parameter. Returns false if missing/empty. */
	static bool GetRequiredQueryParam(const FHttpServerRequest& Request, const FString& Key, FString& OutValue);

	/** Read an optional query parameter. Returns default if missing. */
	static FString GetOptionalQueryParam(const FHttpServerRequest& Request, const FString& Key, const FString& DefaultValue = TEXT(""));

	/** Create a JSON response { ... } with code. */
	static TUniquePtr<FHttpServerResponse> JsonResponse(const FString& JsonBody, EHttpServerResponseCodes Code = EHttpServerResponseCodes::Ok);

	/** Create a structured JSON error response. */
	static TUniquePtr<FHttpServerResponse> JsonError(
		const FString& Message,
		EHttpServerResponseCodes Code = EHttpServerResponseCodes::BadRequest,
		const FString& Detail = TEXT("")
	);

	/** Best-effort normalization: convert object path "/Game/A.B" to package path "/Game/A". */
	static FString NormalizeToPackagePath(const FString& AnyPath);

	/** Build an object path from package path if needed: "/Game/A" -> "/Game/A.A". */
	static FString NormalizeToObjectPath(const FString& PackageOrObjectPath);
};



