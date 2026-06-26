"""
JavaScript Mutation Engine - AST-based mutations for JS/TS

5 Critical Operators:
1. AOR - Arithmetic Operator Replacement
2. ROR - Relational Operator Replacement
3. LCR - Logical Connector Replacement
4. BCR - Boolean Constant Replacement
5. STR - String Replacement
"""
import subprocess
import json
import re
from typing import List, Optional, Dict
from pathlib import Path
from language_adapters.base_adapter import Mutant


class JavaScriptMutationEngine:
    """Generate mutations for JavaScript/TypeScript files"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.mutant_id_counter = 0

    def generate_mutants(self, file_path: str) -> List[Mutant]:
        """
        Generate all mutants for a JavaScript file.
        Uses regex-based approach (simpler than AST for MVP).
        """
        source = Path(file_path).read_text()
        mutants = []

        # Apply each operator
        mutants.extend(self._apply_aor(file_path, source))  # Arithmetic
        mutants.extend(self._apply_ror(file_path, source))  # Relational
        mutants.extend(self._apply_lcr(file_path, source))  # Logical
        mutants.extend(self._apply_bcr(file_path, source))  # Boolean
        mutants.extend(self._apply_str(file_path, source))  # String

        return mutants

    def _apply_aor(self, file_path: str, source: str) -> List[Mutant]:
        """AOR - Arithmetic Operator Replacement: + → -, * → /, etc."""
        mutants = []
        operators = {
            "+": "-",
            "-": "+",
            "*": "/",
            "/": "*",
            "%": "*",
        }

        for old_op, new_op in operators.items():
            # Find all arithmetic operations (simple regex, not perfect)
            pattern = rf"(\w|\))\s*\{re.escape(old_op)}\s*(\w|\()"
            for match in re.finditer(pattern, source):
                start, end = match.span()
                mutant_src = (
                    source[:start]
                    + match.group(0).replace(old_op, new_op)
                    + source[end:]
                )

                line_no = source[: match.start()].count("\n") + 1

                mutant = Mutant(
                    id=f"AOR_{self.mutant_id_counter}",
                    file_path=file_path,
                    function_name="unknown",
                    line_no=line_no,
                    operator="AOR",
                    description=f"{old_op} → {new_op}",
                    original_src=match.group(0),
                    mutant_src=match.group(0).replace(old_op, new_op),
                )
                mutants.append(mutant)
                self.mutant_id_counter += 1

        return mutants

    def _apply_ror(self, file_path: str, source: str) -> List[Mutant]:
        """ROR - Relational Operator Replacement: === → !==, > → <, etc."""
        mutants = []
        operators = {
            "===": "!==",
            "!==": "===",
            "==": "!=",
            "!=": "==",
            ">": "<",
            "<": ">",
            ">=": "<=",
            "<=": ">=",
        }

        for old_op, new_op in operators.items():
            pattern = re.escape(old_op)
            for match in re.finditer(pattern, source):
                start, end = match.span()
                mutant_src = source[:start] + new_op + source[end:]
                line_no = source[:start].count("\n") + 1

                mutant = Mutant(
                    id=f"ROR_{self.mutant_id_counter}",
                    file_path=file_path,
                    function_name="unknown",
                    line_no=line_no,
                    operator="ROR",
                    description=f"{old_op} → {new_op}",
                    original_src=old_op,
                    mutant_src=new_op,
                )
                mutants.append(mutant)
                self.mutant_id_counter += 1

        return mutants

    def _apply_lcr(self, file_path: str, source: str) -> List[Mutant]:
        """LCR - Logical Connector Replacement: && → ||, ! removal, etc."""
        mutants = []

        # && → ||
        for match in re.finditer(r"&&", source):
            start, end = match.span()
            mutant_src = source[:start] + "||" + source[end:]
            line_no = source[:start].count("\n") + 1

            mutant = Mutant(
                id=f"LCR_{self.mutant_id_counter}",
                file_path=file_path,
                function_name="unknown",
                line_no=line_no,
                operator="LCR",
                description="&& → ||",
                original_src="&&",
                mutant_src="||",
            )
            mutants.append(mutant)
            self.mutant_id_counter += 1

        # || → &&
        for match in re.finditer(r"\|\|", source):
            start, end = match.span()
            mutant_src = source[:start] + "&&" + source[end:]
            line_no = source[:start].count("\n") + 1

            mutant = Mutant(
                id=f"LCR_{self.mutant_id_counter}",
                file_path=file_path,
                function_name="unknown",
                line_no=line_no,
                operator="LCR",
                description="|| → &&",
                original_src="||",
                mutant_src="&&",
            )
            mutants.append(mutant)
            self.mutant_id_counter += 1

        return mutants

    def _apply_bcr(self, file_path: str, source: str) -> List[Mutant]:
        """BCR - Boolean Constant Replacement: true → false, false → true"""
        mutants = []

        # true → false
        for match in re.finditer(r"\btrue\b", source):
            start, end = match.span()
            mutant_src = source[:start] + "false" + source[end:]
            line_no = source[:start].count("\n") + 1

            mutant = Mutant(
                id=f"BCR_{self.mutant_id_counter}",
                file_path=file_path,
                function_name="unknown",
                line_no=line_no,
                operator="BCR",
                description="true → false",
                original_src="true",
                mutant_src="false",
            )
            mutants.append(mutant)
            self.mutant_id_counter += 1

        # false → true
        for match in re.finditer(r"\bfalse\b", source):
            start, end = match.span()
            mutant_src = source[:start] + "true" + source[end:]
            line_no = source[:start].count("\n") + 1

            mutant = Mutant(
                id=f"BCR_{self.mutant_id_counter}",
                file_path=file_path,
                function_name="unknown",
                line_no=line_no,
                operator="BCR",
                description="false → true",
                original_src="false",
                mutant_src="true",
            )
            mutants.append(mutant)
            self.mutant_id_counter += 1

        return mutants

    def _apply_str(self, file_path: str, source: str) -> List[Mutant]:
        """STR - String Replacement: "str" → "", 'str' → '', etc."""
        mutants = []

        # Double-quoted strings
        for match in re.finditer(r'"([^"]*)"', source):
            start, end = match.span()
            original = match.group(0)
            mutant_src = source[:start] + '""' + source[end:]
            line_no = source[:start].count("\n") + 1

            if original != '""':  # Don't mutate empty strings
                mutant = Mutant(
                    id=f"STR_{self.mutant_id_counter}",
                    file_path=file_path,
                    function_name="unknown",
                    line_no=line_no,
                    operator="STR",
                    description=f'{original} → ""',
                    original_src=original,
                    mutant_src='""',
                )
                mutants.append(mutant)
                self.mutant_id_counter += 1

        # Single-quoted strings
        for match in re.finditer(r"'([^']*)'", source):
            start, end = match.span()
            original = match.group(0)
            mutant_src = source[:start] + "''" + source[end:]
            line_no = source[:start].count("\n") + 1

            if original != "''":  # Don't mutate empty strings
                mutant = Mutant(
                    id=f"STR_{self.mutant_id_counter}",
                    file_path=file_path,
                    function_name="unknown",
                    line_no=line_no,
                    operator="STR",
                    description=f"{original} → ''",
                    original_src=original,
                    mutant_src="''",
                )
                mutants.append(mutant)
                self.mutant_id_counter += 1

        return mutants

    def validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Validate JavaScript syntax using Node.js.
        Returns: (valid, error_message)
        """
        try:
            # Use Node.js to validate syntax
            result = subprocess.run(
                ["node", "-c"],
                input=code,
                capture_output=True,
                timeout=5,
                text=True,
            )
            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr or "Syntax error"
        except subprocess.TimeoutExpired:
            return False, "Syntax validation timeout"
        except FileNotFoundError:
            return False, "Node.js not found"
        except Exception as e:
            return False, str(e)
