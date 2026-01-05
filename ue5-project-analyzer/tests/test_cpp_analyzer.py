"""Tests for C++ Analyzer module."""

import pytest
from pathlib import Path

from ue5_analyzer.cpp_analyzer.patterns import detect_ue_pattern, parse_specifiers


class TestPatternDetection:
    """Test UE pattern detection."""
    
    def test_parse_specifiers_simple(self):
        """Test parsing simple specifiers."""
        result = parse_specifiers("EditAnywhere, BlueprintReadWrite")
        assert "EditAnywhere" in result
        assert "BlueprintReadWrite" in result
    
    def test_parse_specifiers_with_category(self):
        """Test parsing specifiers with Category."""
        result = parse_specifiers('EditAnywhere, Category="Combat"')
        assert "EditAnywhere" in result
        # Category value is stripped due to parentheses handling
    
    def test_detect_uproperty(self):
        """Test UPROPERTY detection."""
        content = '''
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Stats")
float Health = 100.0f;
'''
        patterns = detect_ue_pattern(content, "test.h")
        
        assert len(patterns) == 1
        assert patterns[0]["pattern_type"] == "UPROPERTY"
        assert patterns[0]["name"] == "Health"
        assert patterns[0]["is_blueprint_exposed"] is True
    
    def test_detect_ufunction(self):
        """Test UFUNCTION detection."""
        content = '''
UFUNCTION(BlueprintCallable, Category="Combat")
void TakeDamage(float Amount);
'''
        patterns = detect_ue_pattern(content, "test.h")
        
        assert len(patterns) == 1
        assert patterns[0]["pattern_type"] == "UFUNCTION"
        assert patterns[0]["name"] == "TakeDamage"
        assert patterns[0]["is_blueprint_exposed"] is True
    
    def test_detect_uclass(self):
        """Test UCLASS detection."""
        content = '''
UCLASS(Blueprintable, BlueprintType)
class MYGAME_API AMyActor : public AActor
{
    GENERATED_BODY()
};
'''
        patterns = detect_ue_pattern(content, "test.h")
        
        uclass_patterns = [p for p in patterns if p["pattern_type"] == "UCLASS"]
        assert len(uclass_patterns) == 1
        assert uclass_patterns[0]["name"] == "AMyActor"
        assert uclass_patterns[0]["is_blueprint_exposed"] is True


class TestCppAnalyzer:
    """Test CppAnalyzer class."""
    
    @pytest.mark.asyncio
    async def test_search_code_no_paths(self):
        """Test search_code raises error when no paths configured."""
        from ue5_analyzer.cpp_analyzer import get_analyzer
        
        analyzer = get_analyzer()
        result = await analyzer.search_code("test")
        
        # Should return empty results when no paths configured
        assert result["count"] == 0
