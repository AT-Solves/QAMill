"""
JavaScript Equivalence Detector - Phase 2
Detects equivalent mutants that don't change program behavior
"""
import re
from typing import Optional, Tuple
from language_adapters.base_adapter import Mutant


class JavaScriptEquivalenceDetector:
    """Detect equivalent mutants for JavaScript"""

    def __init__(self):
        self.equivalence_patterns = {
            # Same mathematical operations (order matters for + and *)
            ("AOR", "+ -> -"): "Changing + to - always changes result",
            ("AOR", "- -> +"): "Changing - to + always changes result",

            # Relational operators (comparing values)
            ("ROR", "=== -> !=="): "Flipping === always changes result",

            # Logical operators
            ("LCR", "&& -> ||"): "May be equivalent if operands are same",

            # Boolean flip
            ("BCR", "true -> false"): "Flipping boolean always changes control flow",

            # String changes
            ("STR", '"" change'): "String changes always affect behavior",
        }

    def is_equivalent(self, mutant: Mutant) -> Tuple[bool, Optional[str]]:
        """
        Detect if a mutant is equivalent.
        Returns: (is_equivalent, reason)
        """

        # Pattern 1: Operators that don't change behavior in special cases
        if mutant.operator == "ROR":
            if self._check_relational_equivalence(mutant):
                return True, "Relational mutation may not change behavior for specific inputs"

        # Pattern 2: Empty string operations
        if mutant.operator == "STR":
            if mutant.original_src == '""' or mutant.mutant_src == '""':
                return False, "String mutations always affect behavior"

        # Pattern 3: Boolean constants in always-true/false paths
        if mutant.operator == "BCR":
            if self._check_boolean_equivalence(mutant):
                return True, "Boolean in unreachable code path"

        # Pattern 4: Arithmetic operators
        if mutant.operator == "AOR":
            if self._check_arithmetic_equivalence(mutant):
                return False, "Arithmetic mutation always changes result"

        # Default: not equivalent
        return False, None

    def _check_relational_equivalence(self, mutant: Mutant) -> bool:
        """Check if relational operator mutation could be equivalent"""

        # === and !== are not equivalent when dealing with type coercion
        if mutant.description in ["=== to !==", "!== to ==="]:
            # In strict JavaScript, these are almost never equivalent
            return False

        # >= and > might be equivalent in edge cases
        if mutant.description in [">= to <=", "<= to >="]:
            # Only equivalent if compared values are same
            return False

        return False

    def _check_boolean_equivalence(self, mutant: Mutant) -> bool:
        """Check if boolean constant is in unreachable code"""
        # This would require control flow analysis
        # For now, assume all boolean mutations are significant
        return False

    def _check_arithmetic_equivalence(self, mutant: Mutant) -> bool:
        """Check if arithmetic mutation could be equivalent"""
        # Arithmetic mutations almost always change result
        return False

    def get_equivalence_confidence(self, mutant: Mutant) -> float:
        """
        Get confidence score for equivalence (0.0 to 1.0).
        0.0 = definitely not equivalent
        1.0 = definitely equivalent
        """
        is_equiv, reason = self.is_equivalent(mutant)

        if is_equiv:
            return 0.85  # High confidence
        else:
            return 0.05  # Low confidence (likely not equivalent)


class JavaScriptDynamicEquivalenceDetector:
    """
    Dynamic equivalence detection through test execution.
    If a mutant survives ALL tests, it might be equivalent.
    """

    def __init__(self, threshold: float = 0.95):
        self.survival_threshold = threshold  # % of tests that must pass

    def analyze_for_equivalence(
        self,
        mutant: Mutant,
        killed_count: int,
        total_tests: int
    ) -> Tuple[bool, str]:
        """
        Analyze if a survived mutant is likely equivalent.

        Returns: (likely_equivalent, reason)
        """

        # If mutant killed ANY test, it's not equivalent
        if killed_count > 0:
            return False, f"Mutant killed {killed_count} test(s)"

        # If mutant survived ALL tests, it MIGHT be equivalent
        # Mark for manual review
        return True, "Survived all tests - likely equivalent mutant"
