// Copyright Unreal Copilot Team. All Rights Reserved.
//
// HTTP route registration for UnrealCopilot.

#pragma once

#include "CoreMinimal.h"

class IHttpRouter;

namespace UnrealAnalyzerHttpRoutes
{
	/** Bind all HTTP routes to the provided router. */
	void Register(TSharedPtr<IHttpRouter> Router);
}



