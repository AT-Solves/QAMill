"""
JavaScript Adapter - Unified interface for JavaScript mutation testing
"""
from pathlib import Path
from typing import List, Dict, Optional
import asyncio
from language_adapters import detect_test_framework
from language_adapters.base_adapter import LanguageAdapter, Mutant
from javascript_mutation_engine import JavaScriptMutationEngine
from javascript_test_runner import JestTestRunner, VitestTestRunner, MochaTestRunner


class JavaScriptAdapter(LanguageAdapter):
    """
    Complete JavaScript/TypeScript mutation testing adapter.
    Supports: Jest, Vitest, Mocha test frameworks
    Implements: 5 critical mutation operators (AOR, ROR, LCR, BCR, STR)
    """

    def __init__(self, project_path: str, test_framework: str = None):
        self.project_path = Path(project_path)

        # Auto-detect framework if not provided
        if not test_framework:
            test_framework = detect_test_framework(str(project_path), "javascript")
            if not test_framework:
                test_framework = "jest"

        self.test_framework = test_framework
        self.mutation_engine = JavaScriptMutationEngine(str(project_path))

        # Initialize appropriate test runner
        if test_framework == "vitest":
            self.test_runner = VitestTestRunner(str(project_path))
        elif test_framework == "mocha":
            self.test_runner = MochaTestRunner(str(project_path))
        else:  # Default to Jest
            self.test_runner = JestTestRunner(str(project_path))

    def parse_file(self, file_path: str) -> Dict:
        """Parse JavaScript file (returns basic metadata)"""
        source = Path(file_path).read_text()
        return {
            "file_path": file_path,
            "language": "javascript",
            "lines": len(source.split("\n")),
            "chars": len(source),
        }

    def generate_mutants(self, file_path: str) -> List[Mutant]:
        """Generate all mutants for a JavaScript file"""
        return self.mutation_engine.generate_mutants(file_path)

    async def run_test_against_mutant(
        self, mutant: Mutant, test_files: List[str]
    ) -> Dict:
        """Run tests against a mutant and determine if it's killed"""
        result = await self.test_runner.test_mutant(mutant, test_files)
        return result

    def validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """Validate JavaScript syntax"""
        return self.mutation_engine.validate_syntax(code)

    def get_framework_info(self) -> Dict:
        """Get information about the detected test framework"""
        return {
            "framework": self.test_framework,
            "display_name": self._get_framework_name(),
            "icon": self._get_framework_icon(),
        }

    def _get_framework_name(self) -> str:
        """Get human-readable framework name"""
        names = {
            "jest": "Jest",
            "vitest": "Vitest",
            "mocha": "Mocha",
        }
        return names.get(self.test_framework, "Unknown")

    def _get_framework_icon(self) -> str:
        """Get emoji icon for framework"""
        icons = {
            "jest": "🃏",
            "vitest": "⚡",
            "mocha": "☕",
        }
        return icons.get(self.test_framework, "🧪")
