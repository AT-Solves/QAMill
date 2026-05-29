"""
mutation_engine.py
AST-based in-house mutation engine — no LLM required.
Supports Python. JS/Java coming via language adapters.
"""
import ast
import copy
import astor
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Mutant:
    id: str
    file_path: str
    function_name: str
    line_no: int
    operator: str          # e.g. "AOR", "ROR", "LCR", "BCR"
    description: str       # human-readable: "+ → -"
    original_src: str      # original function source
    mutant_src: str        # mutated function source
    status: str = "pending"  # pending | killed | survived | equivalent | error
    equivalent_reason: Optional[str] = None
    difficulty: Optional[str] = None         # low | medium | high
    difficulty_reason: Optional[str] = None
    suggested_test: Optional[str] = None


# ── Arithmetic Operator Replacement (AOR) ──────────────────────────────────

class AORMutator(ast.NodeTransformer):
    """Swaps arithmetic operators: + - * / // % **"""
    SWAPS = {
        ast.Add:  [ast.Sub, ast.Mult],
        ast.Sub:  [ast.Add, ast.Mult],
        ast.Mult: [ast.Add, ast.Sub],
        ast.Div:  [ast.Mult, ast.Sub],
        ast.FloorDiv: [ast.Div, ast.Sub],
        ast.Mod:  [ast.Mult, ast.Sub],
    }

    def __init__(self, target_op, replacement_op):
        self.target_op = target_op
        self.replacement_op = replacement_op
        self.mutated = False
        self.line_no = None

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, self.target_op) and not self.mutated:
            self.mutated = True
            self.line_no = node.lineno
            new_node = copy.deepcopy(node)
            new_node.op = self.replacement_op()
            return new_node
        return node


# ── Relational Operator Replacement (ROR) ──────────────────────────────────

class RORMutator(ast.NodeTransformer):
    """Swaps comparison operators: == != > >= < <="""
    SWAPS = {
        ast.Eq:    [ast.NotEq, ast.Lt, ast.Gt],
        ast.NotEq: [ast.Eq, ast.Lt, ast.Gt],
        ast.Lt:    [ast.LtE, ast.Gt, ast.Eq],
        ast.LtE:   [ast.Lt, ast.GtE, ast.Eq],
        ast.Gt:    [ast.GtE, ast.Lt, ast.Eq],
        ast.GtE:   [ast.Gt, ast.LtE, ast.Eq],
    }

    def __init__(self, target_op, replacement_op):
        self.target_op = target_op
        self.replacement_op = replacement_op
        self.mutated = False
        self.line_no = None

    def visit_Compare(self, node):
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            if isinstance(op, self.target_op) and not self.mutated:
                self.mutated = True
                self.line_no = node.lineno
                new_node = copy.deepcopy(node)
                new_node.ops[i] = self.replacement_op()
                return new_node
        return node


# ── Logical Connector Replacement (LCR) ────────────────────────────────────

class LCRMutator(ast.NodeTransformer):
    """Swaps logical operators: and ↔ or"""
    def __init__(self, target_op, replacement_op):
        self.target_op = target_op
        self.replacement_op = replacement_op
        self.mutated = False
        self.line_no = None

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, self.target_op) and not self.mutated:
            self.mutated = True
            self.line_no = node.lineno
            new_node = copy.deepcopy(node)
            new_node.op = self.replacement_op()
            return new_node
        return node


# ── Boolean Constant Replacement (BCR) ─────────────────────────────────────

class BCRMutator(ast.NodeTransformer):
    """Flips True ↔ False constants"""
    def __init__(self):
        self.mutated = False
        self.line_no = None

    def visit_Constant(self, node):
        if node.value is True and not self.mutated:
            self.mutated = True
            self.line_no = node.lineno
            return ast.Constant(value=False)
        if node.value is False and not self.mutated:
            self.mutated = True
            self.line_no = node.lineno
            return ast.Constant(value=True)
        return node


# ── Return Value Replacement (RVR) ─────────────────────────────────────────

class RVRMutator(ast.NodeTransformer):
    """Replaces return value with None"""
    def __init__(self):
        self.mutated = False
        self.line_no = None

    def visit_Return(self, node):
        if node.value is not None and not self.mutated:
            self.mutated = True
            self.line_no = node.lineno
            return ast.Return(value=ast.Constant(value=None))
        return node


# ── Engine ──────────────────────────────────────────────────────────────────

class MutationEngine:
    def __init__(self):
        self._mutant_counter = 0

    def _next_id(self):
        self._mutant_counter += 1
        return f"M{self._mutant_counter:04d}"

    def generate_mutants(self, file_path: str) -> List[Mutant]:
        with open(file_path) as f:
            source = f.read()

        tree = ast.parse(source)
        mutants = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                fn_src = astor.to_source(node)
                fn_mutants = self._mutate_function(node, fn_src, file_path)
                mutants.extend(fn_mutants)

        return mutants

    def _mutate_function(self, fn_node: ast.FunctionDef,
                         fn_src: str, file_path: str) -> List[Mutant]:
        mutants = []
        fn_name = fn_node.name
        fn_tree = copy.deepcopy(fn_node)

        # ── AOR mutations ──
        for target_op, replacements in AORMutator.SWAPS.items():
            for replacement_op in replacements:
                m = AORMutator(target_op, replacement_op)
                new_tree = m.visit(copy.deepcopy(fn_tree))
                if m.mutated:
                    op_desc = f"{self._op_symbol(target_op)} → {self._op_symbol(replacement_op)}"
                    mutants.append(Mutant(
                        id=self._next_id(),
                        file_path=file_path,
                        function_name=fn_name,
                        line_no=m.line_no or fn_node.lineno,
                        operator="AOR",
                        description=op_desc,
                        original_src=fn_src,
                        mutant_src=astor.to_source(new_tree),
                    ))

        # ── ROR mutations ──
        for target_op, replacements in RORMutator.SWAPS.items():
            for replacement_op in replacements:
                m = RORMutator(target_op, replacement_op)
                new_tree = m.visit(copy.deepcopy(fn_tree))
                if m.mutated:
                    op_desc = f"{self._op_symbol(target_op)} → {self._op_symbol(replacement_op)}"
                    mutants.append(Mutant(
                        id=self._next_id(),
                        file_path=file_path,
                        function_name=fn_name,
                        line_no=m.line_no or fn_node.lineno,
                        operator="ROR",
                        description=op_desc,
                        original_src=fn_src,
                        mutant_src=astor.to_source(new_tree),
                    ))

        # ── LCR mutations ──
        for target_op, replacement_op in [(ast.And, ast.Or), (ast.Or, ast.And)]:
            m = LCRMutator(target_op, replacement_op)
            new_tree = m.visit(copy.deepcopy(fn_tree))
            if m.mutated:
                sym = "and → or" if target_op == ast.And else "or → and"
                mutants.append(Mutant(
                    id=self._next_id(),
                    file_path=file_path,
                    function_name=fn_name,
                    line_no=m.line_no or fn_node.lineno,
                    operator="LCR",
                    description=sym,
                    original_src=fn_src,
                    mutant_src=astor.to_source(new_tree),
                ))

        # ── BCR mutations ──
        m = BCRMutator()
        new_tree = m.visit(copy.deepcopy(fn_tree))
        if m.mutated:
            mutants.append(Mutant(
                id=self._next_id(),
                file_path=file_path,
                function_name=fn_name,
                line_no=m.line_no or fn_node.lineno,
                operator="BCR",
                description="True ↔ False",
                original_src=fn_src,
                mutant_src=astor.to_source(new_tree),
            ))

        # ── RVR mutations ──
        m = RVRMutator()
        new_tree = m.visit(copy.deepcopy(fn_tree))
        if m.mutated:
            mutants.append(Mutant(
                id=self._next_id(),
                file_path=file_path,
                function_name=fn_name,
                line_no=m.line_no or fn_node.lineno,
                operator="RVR",
                description="return value → None",
                original_src=fn_src,
                mutant_src=astor.to_source(new_tree),
            ))

        return mutants

    @staticmethod
    def _op_symbol(op_class) -> str:
        return {
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
            ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%",
            ast.Eq: "==", ast.NotEq: "!=",
            ast.Lt: "<",  ast.LtE: "<=",
            ast.Gt: ">",  ast.GtE: ">=",
            ast.And: "and", ast.Or: "or",
        }.get(op_class, str(op_class))
