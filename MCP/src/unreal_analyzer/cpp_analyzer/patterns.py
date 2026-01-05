"""
Unreal Engine pattern detection.

Detects UPROPERTY, UFUNCTION, UCLASS, and other UE-specific patterns
to understand Blueprint ↔ C++ boundaries.
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


# ============================================================================
# Regex Patterns for UE Macros
# ============================================================================

UE_PATTERNS = {
    # UPROPERTY - handles UE_API and other macros between UPROPERTY and type
    "UPROPERTY": re.compile(
        r"UPROPERTY\s*\(([^)]*)\)\s*\n?\s*(?:\w+_API\s+)?([\w\s\*<>:,&]+?)\s+(\w+)\s*(?:=|;|\[)",
        re.MULTILINE
    ),
    # UFUNCTION - handles UE_API and other export macros
    "UFUNCTION": re.compile(
        r"UFUNCTION\s*\(([^)]*)\)\s*\n?\s*(?:\w+_API\s+)?([\w\s\*<>:&]+?)\s+(\w+)\s*\([^)]*\)",
        re.MULTILINE
    ),
    # UCLASS - handles various API export macros
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
    "UINTERFACE": re.compile(
        r"UINTERFACE\s*\(([^)]*)\)\s*class\s+(?:\w+_API\s+)?(\w+)",
        re.MULTILINE
    ),
    "GENERATED_BODY": re.compile(
        r"GENERATED_(?:BODY|UCLASS_BODY|USTRUCT_BODY)\s*\(\s*\)",
        re.MULTILINE
    ),
}


# ============================================================================
# Blueprint-Related Specifiers
# ============================================================================

BLUEPRINT_SPECIFIERS = {
    # Function specifiers
    "BlueprintCallable",
    "BlueprintPure",
    "BlueprintImplementableEvent",
    "BlueprintNativeEvent",
    "BlueprintAuthorityOnly",
    "BlueprintCosmetic",
    
    # Property specifiers
    "BlueprintReadOnly",
    "BlueprintReadWrite",
    "BlueprintGetter",
    "BlueprintSetter",
    
    # Class specifiers
    "Blueprintable",
    "BlueprintType",
    "NotBlueprintable",
    
    # Editor specifiers
    "EditAnywhere",
    "EditDefaultsOnly",
    "EditInstanceOnly",
    "VisibleAnywhere",
    "VisibleDefaultsOnly",
    "VisibleInstanceOnly",
}


# ============================================================================
# Replication Specifiers
# ============================================================================

REPLICATION_SPECIFIERS = {
    "Replicated",
    "ReplicatedUsing",
    "NotReplicated",
    "Server",
    "Client",
    "NetMulticast",
    "Reliable",
    "Unreliable",
}


# ============================================================================
# Pattern Detection Functions
# ============================================================================

def parse_specifiers(specifiers_str: str) -> list[str]:
    """
    Parse specifiers from a macro argument string.
    
    Args:
        specifiers_str: The string inside macro parentheses
    
    Returns:
        List of individual specifiers
    """
    result = []
    depth = 0
    current = ""
    
    for char in specifiers_str:
        if char == '(':
            depth += 1
            current += char
        elif char == ')':
            depth -= 1
            current += char
        elif char == ',' and depth == 0:
            if current.strip():
                result.append(current.strip())
            current = ""
        else:
            current += char
    
    if current.strip():
        result.append(current.strip())
    
    return result


def detect_ue_pattern(content: str, file_path: str) -> list[dict]:
    """
    Detect all UE patterns in file content.
    
    Identifies UPROPERTY, UFUNCTION, UCLASS, USTRUCT, UENUM patterns
    and extracts their specifiers to determine Blueprint exposure.
    
    Args:
        content: File content to analyze
        file_path: Path to the file (for reporting)
    
    Returns:
        List of detected patterns with details including:
        - pattern_type: UPROPERTY, UFUNCTION, UCLASS, etc.
        - name: Name of the item
        - specifiers: List of specifiers
        - line: Line number
        - context: Surrounding code
        - is_blueprint_exposed: Whether exposed to Blueprints
        - is_replicated: Whether marked for replication
    """
    patterns = []
    lines = content.split('\n')
    
    for pattern_type, regex in UE_PATTERNS.items():
        if pattern_type == "GENERATED_BODY":
            continue
            
        for match in regex.finditer(content):
            specifiers_str = match.group(1) if match.lastindex >= 1 else ""
            specifiers = parse_specifiers(specifiers_str)
            
            # Get line number
            line_num = content[:match.start()].count('\n') + 1
            
            # Get context (surrounding lines)
            start_line = max(0, line_num - 2)
            end_line = min(len(lines), line_num + 3)
            context = '\n'.join(lines[start_line:end_line])
            
            # Get the name
            if pattern_type in ("UCLASS", "USTRUCT", "UENUM", "UINTERFACE"):
                name = match.group(2)
            else:
                name = match.group(3) if match.lastindex >= 3 else ""
            
            # Check Blueprint and replication exposure
            specifier_names = {s.split("=")[0].strip() for s in specifiers}
            is_blueprint_exposed = bool(specifier_names & BLUEPRINT_SPECIFIERS)
            is_replicated = bool(specifier_names & REPLICATION_SPECIFIERS)
            
            patterns.append({
                "pattern_type": pattern_type,
                "name": name,
                "specifiers": specifiers,
                "line": line_num,
                "context": context,
                "is_blueprint_exposed": is_blueprint_exposed,
                "is_replicated": is_replicated,
            })
    
    return patterns
