// Copyright Unreal Copilot Team. All Rights Reserved.

#include "Skill/CppSkillApiSubsystem.h"

#include "Editor.h"

UCppSkillApiSubsystem* UCppSkillApiSubsystem::Get()
{
    return GEditor ? GEditor->GetEditorSubsystem<UCppSkillApiSubsystem>() : nullptr;
}


