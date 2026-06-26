"""
Base Adapter - Abstract interface for language-specific implementations
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class Mutant:
    """Unified mutant representation across all languages"""

    id: str
    file_path: str
    function_name: str
    line_no: int
    operator: str  # e.g. "AOR", "ROR", "LCR"
    description: str  # human-readable: "+ -> -"
    original_src: str  # original function/code
    mutant_src: str  # mutated code
    status: str = "pending"  # pending | killed | survived | equivalent | error
    equivalent_reason: Optional[str] = None
    difficulty: Optional[str] = None  # low | medium | high
    difficulty_reason: Optional[str] = None
    suggested_test: Optional[str] = None


class LanguageAdapter(ABC):
    """Base interface for language-specific mutation testing"""

    @abstractmethod
    def __init__(self, project_path: str, test_framework: str):
        """Initialize adapter with project path and test framework"""
        pass

    @abstractmethod
    def parse_file(self, file_path: str) -> any:
        """Parse file into language-specific AST"""
        pass

    @abstractmethod
    def generate_mutants(self, file_path: str) -> List[Mutant]:
        """Generate all possible mutants for a file"""
        pass

    @abstractmethod
    async def run_test_against_mutant(
        self, mutant: Mutant, test_files: List[str]
    ) -> Dict:
        """
        Run tests against a mutant.
        Returns: {
            "status": "killed" | "survived" | "error",
            "killed_count": int,
            "failed_tests": List[str],
            "error": Optional[str]
        }
        """
        pass

    @abstractmethod
    def validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """Validate code syntax. Returns: (valid, error_message)"""
        pass
