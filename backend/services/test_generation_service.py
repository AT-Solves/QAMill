"""
AI-Powered Test Generation Service
Generates comprehensive test cases from survived mutations and code analysis

Capabilities:
- Unit test generation (pytest, Jest)
- Edge case generation
- BDD scenario generation
- Error condition testing
- Boundary value testing
- Manual QA test case generation
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json


class TestFramework(Enum):
    """Supported test frameworks"""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    JEST = "jest"
    VITEST = "vitest"
    MOCHA = "mocha"
    JASMINE = "jasmine"


class TestFormat(Enum):
    """Supported output formats"""
    PYTEST_CODE = "pytest_code"
    JEST_CODE = "jest_code"
    GHERKIN = "gherkin"
    MARKDOWN = "markdown"
    JSON = "json"
    MANUAL_QA = "manual_qa"


@dataclass
class GeneratedTest:
    """A generated test case"""
    id: str
    name: str
    code: str
    framework: TestFramework
    description: str
    test_type: str  # unit, edge_case, error, boundary, integration
    affected_mutations: List[str]
    estimated_coverage_improvement: float
    priority: str  # high, medium, low


class TestGenerationService:
    """Service for generating tests from mutations and code analysis"""

    def __init__(self, llm_service):
        """
        Initialize test generation service

        Args:
            llm_service: LLM service for AI-powered generation
        """
        self.llm_service = llm_service
        self.generated_tests: List[GeneratedTest] = []

    async def generate_tests_for_mutations(
        self,
        survived_mutations: List[Dict[str, Any]],
        source_code: str,
        language: str,
        framework: TestFramework,
        existing_tests: str = None
    ) -> List[GeneratedTest]:
        """
        Generate tests to cover survived mutations

        Args:
            survived_mutations: List of mutations that weren't caught
            source_code: Source code being tested
            language: Programming language (python, javascript)
            framework: Test framework to use
            existing_tests: Existing test code for context

        Returns:
            List of generated tests
        """

        generated = []

        # Group mutations by type
        mutation_groups = self._group_mutations(survived_mutations)

        for mutation_type, mutations in mutation_groups.items():
            # Generate targeted tests for each mutation type
            tests = await self._generate_tests_for_mutation_type(
                mutation_type,
                mutations,
                source_code,
                language,
                framework,
                existing_tests
            )
            generated.extend(tests)

        # Generate edge case tests
        edge_tests = await self._generate_edge_case_tests(
            source_code,
            language,
            framework
        )
        generated.extend(edge_tests)

        # Generate error condition tests
        error_tests = await self._generate_error_condition_tests(
            source_code,
            language,
            framework
        )
        generated.extend(error_tests)

        # Generate boundary value tests
        boundary_tests = await self._generate_boundary_value_tests(
            source_code,
            language,
            framework
        )
        generated.extend(boundary_tests)

        self.generated_tests = generated
        return generated

    async def _generate_tests_for_mutation_type(
        self,
        mutation_type: str,
        mutations: List[Dict],
        source_code: str,
        language: str,
        framework: TestFramework,
        existing_tests: Optional[str]
    ) -> List[GeneratedTest]:
        """Generate tests for specific mutation type"""

        prompt = f"""
You are an expert {language} test engineer. Generate comprehensive test cases to catch these mutations:

Mutation Type: {mutation_type}
Mutations to catch: {json.dumps([m['description'] for m in mutations[:3]])}

Source code:
{source_code[:1000]}

Existing tests (for context):
{existing_tests or 'None'}

Generate {framework.value} test code that:
1. Catches all these mutations
2. Tests edge cases
3. Tests boundary values
4. Has clear assertions
5. Is well-commented

Return ONLY the test code, no explanations.
"""

        response = await self.llm_service.generate(
            prompt=prompt,
            model="claude",
            temperature=0.5,
            max_tokens=2000
        )

        # Parse and create test object
        test = GeneratedTest(
            id=f"gen_test_{len(self.generated_tests):04d}",
            name=f"test_{mutation_type.lower()}",
            code=response,
            framework=framework,
            description=f"Auto-generated tests for {mutation_type} mutations",
            test_type="mutation_catch",
            affected_mutations=[m['id'] for m in mutations],
            estimated_coverage_improvement=0.05 * len(mutations),
            priority="high"
        )

        return [test]

    async def _generate_edge_case_tests(
        self,
        source_code: str,
        language: str,
        framework: TestFramework
    ) -> List[GeneratedTest]:
        """Generate edge case tests"""

        prompt = f"""
Generate comprehensive edge case tests for this {language} code:

{source_code[:1000]}

Test framework: {framework.value}

Include tests for:
1. Empty/null inputs
2. Single element inputs
3. Maximum values
4. Negative values
5. Type boundaries

Return ONLY {framework.value} test code.
"""

        response = await self.llm_service.generate(
            prompt=prompt,
            model="claude",
            temperature=0.7,
            max_tokens=1500
        )

        return [GeneratedTest(
            id=f"gen_test_{len(self.generated_tests):04d}",
            name="test_edge_cases",
            code=response,
            framework=framework,
            description="Auto-generated edge case tests",
            test_type="edge_case",
            affected_mutations=[],
            estimated_coverage_improvement=0.1,
            priority="high"
        )]

    async def _generate_error_condition_tests(
        self,
        source_code: str,
        language: str,
        framework: TestFramework
    ) -> List[GeneratedTest]:
        """Generate error condition tests"""

        prompt = f"""
Generate error condition and exception handling tests for:

{source_code[:1000]}

Framework: {framework.value}

Include tests for:
1. Invalid inputs
2. Type errors
3. Division by zero
4. Index out of bounds
5. Null/undefined errors

Return ONLY {framework.value} test code.
"""

        response = await self.llm_service.generate(
            prompt=prompt,
            model="claude",
            temperature=0.7,
            max_tokens=1500
        )

        return [GeneratedTest(
            id=f"gen_test_{len(self.generated_tests):04d}",
            name="test_error_conditions",
            code=response,
            framework=framework,
            description="Auto-generated error condition tests",
            test_type="error",
            affected_mutations=[],
            estimated_coverage_improvement=0.08,
            priority="high"
        )]

    async def _generate_boundary_value_tests(
        self,
        source_code: str,
        language: str,
        framework: TestFramework
    ) -> List[GeneratedTest]:
        """Generate boundary value tests"""

        prompt = f"""
Generate boundary value analysis tests for:

{source_code[:1000]}

Framework: {framework.value}

Include tests for:
1. Minimum and maximum valid values
2. Just above/below boundaries
3. Comparison boundaries
4. Loop boundaries
5. Array/string boundaries

Return ONLY {framework.value} test code.
"""

        response = await self.llm_service.generate(
            prompt=prompt,
            model="claude",
            temperature=0.7,
            max_tokens=1500
        )

        return [GeneratedTest(
            id=f"gen_test_{len(self.generated_tests):04d}",
            name="test_boundary_values",
            code=response,
            framework=framework,
            description="Auto-generated boundary value tests",
            test_type="boundary",
            affected_mutations=[],
            estimated_coverage_improvement=0.08,
            priority="high"
        )]

    async def generate_bdd_scenarios(
        self,
        feature_description: str,
        source_code: str
    ) -> str:
        """Generate BDD/Gherkin scenarios"""

        prompt = f"""
Generate Gherkin BDD scenarios for:

Feature: {feature_description}

Code:
{source_code[:1000]}

Create scenarios with:
1. Given-When-Then format
2. Multiple scenarios (happy path, edge cases, errors)
3. Clear step definitions
4. Test data examples

Return ONLY Gherkin format scenarios.
"""

        response = await self.llm_service.generate(
            prompt=prompt,
            model="claude",
            temperature=0.7,
            max_tokens=2000
        )

        return response

    async def generate_manual_qa_tests(
        self,
        feature_description: str,
        source_code: str,
        user_flows: List[str] = None
    ) -> str:
        """Generate manual QA test cases"""

        flows = "\n".join(user_flows) if user_flows else "User interactions with the feature"

        prompt = f"""
Generate detailed manual QA test cases for:

Feature: {feature_description}

Code:
{source_code[:1000]}

User Flows:
{flows}

Create test cases with:
1. Test ID and name
2. Prerequisites
3. Step-by-step instructions
4. Expected results
5. Edge cases
6. Error scenarios

Format as markdown table.
"""

        response = await self.llm_service.generate(
            prompt=prompt,
            model="claude",
            temperature=0.7,
            max_tokens=2500
        )

        return response

    def export_tests(
        self,
        tests: List[GeneratedTest],
        format: TestFormat
    ) -> str:
        """Export generated tests in requested format"""

        if format == TestFormat.PYTEST_CODE:
            return self._export_pytest(tests)
        elif format == TestFormat.JEST_CODE:
            return self._export_jest(tests)
        elif format == TestFormat.GHERKIN:
            return self._export_gherkin(tests)
        elif format == TestFormat.MARKDOWN:
            return self._export_markdown(tests)
        elif format == TestFormat.JSON:
            return self._export_json(tests)
        else:
            return str(tests)

    def _export_pytest(self, tests: List[GeneratedTest]) -> str:
        """Export as pytest format"""
        output = "import pytest\n\n"

        for test in tests:
            output += f"# {test.description}\n"
            output += test.code + "\n\n"

        return output

    def _export_jest(self, tests: List[GeneratedTest]) -> str:
        """Export as Jest format"""
        output = ""

        for test in tests:
            output += f"// {test.description}\n"
            output += test.code + "\n\n"

        return output

    def _export_gherkin(self, tests: List[GeneratedTest]) -> str:
        """Export as Gherkin format"""
        return "\n\n".join([t.code for t in tests])

    def _export_markdown(self, tests: List[GeneratedTest]) -> str:
        """Export as Markdown"""
        output = "# Generated Test Cases\n\n"

        for test in tests:
            output += f"## {test.name}\n"
            output += f"- **Type**: {test.test_type}\n"
            output += f"- **Framework**: {test.framework.value}\n"
            output += f"- **Priority**: {test.priority}\n"
            output += f"- **Coverage Improvement**: {test.estimated_coverage_improvement:.1%}\n"
            output += f"\n```\n{test.code}\n```\n\n"

        return output

    def _export_json(self, tests: List[GeneratedTest]) -> str:
        """Export as JSON"""
        data = [
            {
                "id": t.id,
                "name": t.name,
                "framework": t.framework.value,
                "test_type": t.test_type,
                "priority": t.priority,
                "coverage_improvement": t.estimated_coverage_improvement,
                "code": t.code
            }
            for t in tests
        ]
        return json.dumps(data, indent=2)

    def _group_mutations(self, mutations: List[Dict]) -> Dict[str, List[Dict]]:
        """Group mutations by type"""
        groups = {}

        for mutation in mutations:
            mutation_type = mutation.get('operator', 'Unknown')
            if mutation_type not in groups:
                groups[mutation_type] = []
            groups[mutation_type].append(mutation)

        return groups

    async def calculate_test_impact(
        self,
        generated_tests: List[GeneratedTest],
        all_mutations: List[Dict]
    ) -> Dict[str, float]:
        """Calculate impact of generated tests"""

        total_mutations = len(all_mutations)
        caught_mutations = 0

        for test in generated_tests:
            caught_mutations += len(test.affected_mutations)

        return {
            "mutations_caught": caught_mutations,
            "total_mutations": total_mutations,
            "coverage_improvement": caught_mutations / total_mutations if total_mutations > 0 else 0,
            "estimated_score_improvement": (caught_mutations / total_mutations * 100) if total_mutations > 0 else 0
        }
