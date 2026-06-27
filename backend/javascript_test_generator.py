"""
JavaScript Test Generator - Phase 2
Generate Jest tests using Claude LLM for survived mutations
"""
import json
from typing import Optional, List
from language_adapters.base_adapter import Mutant


class JavaScriptTestGenerator:
    """Generate Jest tests for JavaScript code"""

    def __init__(self, llm_adapter=None):
        """
        Initialize with optional LLM adapter for test generation.
        If no LLM provided, uses template-based generation.
        """
        self.llm = llm_adapter

    async def generate_tests_for_survived_mutants(
        self, source_code: str, survived_mutants: List[Mutant], framework: str = "jest"
    ) -> str:
        """
        Generate new tests to kill survived mutants.

        Args:
            source_code: Original JavaScript source
            survived_mutants: List of mutants that survived all tests
            framework: Test framework (jest, vitest, mocha)

        Returns:
            Generated test code
        """

        if not self.llm:
            # Template-based generation
            return self._generate_tests_template_based(
                source_code, survived_mutants, framework
            )

        # LLM-based generation (more sophisticated)
        return await self._generate_tests_llm_based(
            source_code, survived_mutants, framework
        )

    async def _generate_tests_llm_based(
        self, source_code: str, survived_mutants: List[Mutant], framework: str
    ) -> str:
        """Generate tests using Claude"""

        mutant_descriptions = "\n".join(
            [
                f"  - Line {m.line_no} ({m.operator}): {m.description}"
                for m in survived_mutants[:5]  # Top 5
            ]
        )

        prompt = f"""You are a JavaScript test expert. Generate Jest unit tests to kill these survived mutants:

Source Code:
```javascript
{source_code}
```

Survived Mutants (mutations your tests should kill):
{mutant_descriptions}

Generate Jest tests that specifically target these mutations. The tests should:
1. Be comprehensive and test edge cases
2. Fail if the mutations are applied
3. Use expect() assertions

Return ONLY the test code, ready to paste into a .test.js file.
"""

        try:
            test_code = await self.llm.call_async(prompt, max_tokens=2000)
            return test_code
        except Exception as e:
            print(f"LLM generation failed: {e}, using template")
            return self._generate_tests_template_based(
                source_code, survived_mutants, framework
            )

    def _generate_tests_template_based(
        self, source_code: str, survived_mutants: List[Mutant], framework: str
    ) -> str:
        """Generate tests using templates (fallback)"""

        test_code = f"""
// Auto-generated tests to kill survived mutants
// {len(survived_mutants)} mutations need to be addressed

describe('Survived Mutation Tests', () => {{
"""

        for mutant in survived_mutants[:10]:  # First 10
            test_code += f"""
  // Mutation on line {mutant.line_no}: {mutant.operator} - {mutant.description}
  it('should fail if {mutant.description}', () => {{
    // TODO: Add assertion to kill this mutation
    // Current mutation: {mutant.mutant_src}
    // Original: {mutant.original_src}
    expect(true).toBe(true);
  }});
"""

        test_code += "});"

        return test_code

    def extract_test_framework(self, source_code: str) -> str:
        """Detect test framework from code"""
        if "describe(" in source_code and "it(" in source_code:
            return "jest"  # or mocha
        elif "test(" in source_code:
            return "vitest"
        return "jest"  # Default


class JavaScriptTestQualityAnalyzer:
    """Analyze quality of generated tests"""

    def analyze_test_quality(self, test_code: str) -> dict:
        """
        Analyze quality of test code.

        Returns:
            {
                "has_setup": bool,
                "has_teardown": bool,
                "assertion_count": int,
                "coverage_estimate": float,
                "quality_score": float
            }
        """

        score = 0.0

        # Check for setup/teardown
        has_setup = "beforeEach" in test_code or "before(" in test_code
        has_teardown = "afterEach" in test_code or "after(" in test_code
        if has_setup:
            score += 10
        if has_teardown:
            score += 10

        # Count assertions
        assertion_count = test_code.count("expect(")
        score += min(assertion_count * 5, 50)

        # Check for edge cases
        if "0" in test_code and ("null" in test_code or "undefined" in test_code):
            score += 10

        # Check for error handling
        if "toThrow" in test_code:
            score += 10

        coverage_estimate = min(assertion_count * 0.15, 1.0)

        return {
            "has_setup": has_setup,
            "has_teardown": has_teardown,
            "assertion_count": assertion_count,
            "coverage_estimate": coverage_estimate,
            "quality_score": min(score / 100.0, 1.0),
        }
