"""
Unreal Engine pattern detection.

Detects UPROPERTY, UFUNCTION, UCLASS, and other UE-specific patterns.
"""

import re
from dataclasses import dataclass


@dataclass
class PatternMatch:
    """A matched UE pattern."""
    pattern_type: str
    name: str
    specifiers: list[str]
    line: int
    context: str
    suggestions: list[str]


# Regex patterns for UE macros
UE_PATTERNS = {
    "UPROPERTY": re.compile(
        r"UPROPERTY\s*\(([^)]*)\)\s*\n?\s*([\w\s\*<>:,&]+?)\s+(\w+)\s*(?:=|;)",
        re.MULTILINE
    ),
    "UFUNCTION": re.compile(
        r"UFUNCTION\s*\(([^)]*)\)\s*\n?\s*([\w\s\*<>:&]+?)\s+(\w+)\s*\([^)]*\)",
        re.MULTILINE
    ),
    "UCLASS": re.compile(
        r"UCLASS\s*\(([^)]*)\)\s*class\s+(?:\w+_API\s+)?(\w+)",
        re.MULTILINE
    ),
    "USTRUCT": re.compile(
        r"USTRUCT\s*\(([^)]*)\)\s*struct\s+(?:\w+_API\s+)?(\w+)",
        re.MULTILINE
    ),
    "UENUM": re.compile(
        r"UENUM\s*\(([^)]*)\)\s*enum\s+(?:class\s+)?(\w+)",
        re.MULTILINE
    ),
}

# Blueprint-related specifiers
BLUEPRINT_SPECIFIERS = {
    "BlueprintCallable",
    "BlueprintPure",
    "BlueprintReadOnly",
    "BlueprintReadWrite",
    "BlueprintImplementableEvent",
    "BlueprintNativeEvent",
    "Blueprintable",
    "BlueprintType",
    "EditAnywhere",
    "VisibleAnywhere",
}


def parse_specifiers(specifiers_str: str) -> list[str]:
    """Parse specifiers from a macro argument string."""
    # Remove nested parentheses content for simpler parsing
    cleaned = re.sub(r'\([^)]*\)', '', specifiers_str)
    return [s.strip() for s in cleaned.split(',') if s.strip()]


def detect_ue_pattern(content: str, file_path: str) -> list[dict]:
    """Detect all UE patterns in file content."""
    patterns = []
    lines = content.split('\n')
    
    for pattern_type, regex in UE_PATTERNS.items():
        for match in regex.finditer(content):
            specifiers_str = match.group(1)
            specifiers = parse_specifiers(specifiers_str)
            
            # Get line number
            line_num = content[:match.start()].count('\n') + 1
            
            # Get context (surrounding lines)
            start_line = max(0, line_num - 2)
            end_line = min(len(lines), line_num + 3)
            context = '\n'.join(lines[start_line:end_line])
            
            # Generate suggestions
            suggestions = generate_suggestions(pattern_type, specifiers, context)
            
            # Get the name (different group depending on pattern)
            if pattern_type in ("UCLASS", "USTRUCT", "UENUM"):
                name = match.group(2)
            else:
                name = match.group(3)
            
            patterns.append({
                "pattern_type": pattern_type,
                "name": name,
                "specifiers": specifiers,
                "line": line_num,
                "context": context,
                "suggestions": suggestions,
                "is_blueprint_exposed": any(s in BLUEPRINT_SPECIFIERS for s in specifiers),
            })
    
    return patterns


def generate_suggestions(pattern_type: str, specifiers: list[str], context: str) -> list[str]:
    """Generate improvement suggestions for a pattern."""
    suggestions = []
    
    if pattern_type == "UPROPERTY":
        if not any("Category" in s for s in specifiers):
            suggestions.append("Consider adding a Category for better organization")
        
        if "BlueprintReadWrite" in specifiers and not any("Meta" in s for s in specifiers):
            suggestions.append("Consider adding Meta specifiers for validation")
    
    elif pattern_type == "UFUNCTION":
        if "BlueprintCallable" in specifiers and not any("Category" in s for s in specifiers):
            suggestions.append("Consider adding a Category for Blueprint organization")
    
    elif pattern_type == "UCLASS":
        if "Blueprintable" not in specifiers and "NotBlueprintable" not in specifiers:
            suggestions.append("Consider explicitly specifying Blueprintable or NotBlueprintable")
    
    return suggestions
