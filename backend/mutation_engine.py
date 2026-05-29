"""
mutation_engine.py
AST-based in-house mutation engine — plugin architecture with 17 mutation operators.
Supports Python. JS/Java coming via language adapters.
"""
import ast
import copy
import astor
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Mutant:
    id: str
    file_path: str
    function_name: str
    line_no: int
    operator: str          # e.g. "AOR", "ROR", "LCR", "BCR"
    description: str       # human-readable: "+ -> -"
    original_src: str      # original function source
    mutant_src: str        # mutated function source
    status: str = "pending"  # pending | killed | survived | equivalent | error
    equivalent_reason: Optional[str] = None
    difficulty: Optional[str] = None         # low | medium | high
    difficulty_reason: Optional[str] = None
    suggested_test: Optional[str] = None


# ── Base mutator ABC ────────────────────────────────────────────────────────

class BaseMutator(ABC):
    CODE = ""  # operator code e.g. "AOR"

    @abstractmethod
    def generate(self, fn_node, fn_src: str, file_path: str) -> List[Mutant]:
        pass

    def _make_mutant(self, id_, file_path, fn_name, line_no, operator,
                     description, original_src, mutant_src) -> Mutant:
        return Mutant(
            id=id_ or "",
            file_path=file_path,
            function_name=fn_name,
            line_no=line_no,
            operator=operator,
            description=description,
            original_src=original_src,
            mutant_src=mutant_src,
        )

    @staticmethod
    def _safe_to_source(node) -> str:
        """Convert AST node to source, fixing missing locations."""
        try:
            ast.fix_missing_locations(node)
            return astor.to_source(node)
        except Exception:
            try:
                return ast.unparse(node)
            except Exception:
                return ""


# ── Helper: call name ───────────────────────────────────────────────────────

def _call_name(call_node) -> str:
    if isinstance(call_node.func, ast.Name):
        return call_node.func.id
    if isinstance(call_node.func, ast.Attribute):
        return call_node.func.attr
    return "?"


# ── Helper: replace handler body/type ──────────────────────────────────────

def _replace_handler_body(fn_copy, original_handler, new_body):
    for node in ast.walk(fn_copy):
        if isinstance(node, ast.Try):
            for h in node.handlers:
                if h.lineno == original_handler.lineno:
                    h.body = new_body
                    return


def _replace_handler_type(fn_copy, original_handler, new_type):
    for node in ast.walk(fn_copy):
        if isinstance(node, ast.Try):
            for h in node.handlers:
                if h.lineno == original_handler.lineno:
                    h.type = new_type
                    return


# ── Arithmetic Operator Replacement (AOR) ──────────────────────────────────

class _AORTransformer(ast.NodeTransformer):
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


class AORBaseMutator(BaseMutator):
    CODE = "AOR"
    SWAPS = {
        ast.Add:      [ast.Sub, ast.Mult],
        ast.Sub:      [ast.Add, ast.Mult],
        ast.Mult:     [ast.Add, ast.Sub],
        ast.Div:      [ast.Mult, ast.Sub],
        ast.FloorDiv: [ast.Div, ast.Sub],
        ast.Mod:      [ast.Mult, ast.Sub],
    }

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for target_op, replacements in self.SWAPS.items():
            for replacement_op in replacements:
                t = _AORTransformer(target_op, replacement_op)
                new_fn = t.visit(copy.deepcopy(fn_node))
                if t.mutated:
                    op_desc = f"{MutationEngine._op_symbol(target_op)} -> {MutationEngine._op_symbol(replacement_op)}"
                    src = self._safe_to_source(new_fn)
                    if src:
                        mutants.append(self._make_mutant(
                            id_="", file_path=file_path, fn_name=fn_node.name,
                            line_no=t.line_no or fn_node.lineno,
                            operator="AOR", description=op_desc,
                            original_src=fn_src, mutant_src=src))
        return mutants


# ── Relational Operator Replacement (ROR) ──────────────────────────────────

class _RORTransformer(ast.NodeTransformer):
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


class RORBaseMutator(BaseMutator):
    CODE = "ROR"
    SWAPS = {
        ast.Eq:    [ast.NotEq, ast.Lt, ast.Gt],
        ast.NotEq: [ast.Eq, ast.Lt, ast.Gt],
        ast.Lt:    [ast.LtE, ast.Gt, ast.Eq],
        ast.LtE:   [ast.Lt, ast.GtE, ast.Eq],
        ast.Gt:    [ast.GtE, ast.Lt, ast.Eq],
        ast.GtE:   [ast.Gt, ast.LtE, ast.Eq],
    }

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for target_op, replacements in self.SWAPS.items():
            for replacement_op in replacements:
                t = _RORTransformer(target_op, replacement_op)
                new_fn = t.visit(copy.deepcopy(fn_node))
                if t.mutated:
                    op_desc = f"{MutationEngine._op_symbol(target_op)} -> {MutationEngine._op_symbol(replacement_op)}"
                    src = self._safe_to_source(new_fn)
                    if src:
                        mutants.append(self._make_mutant(
                            id_="", file_path=file_path, fn_name=fn_node.name,
                            line_no=t.line_no or fn_node.lineno,
                            operator="ROR", description=op_desc,
                            original_src=fn_src, mutant_src=src))
        return mutants


# ── Logical Connector Replacement (LCR) ────────────────────────────────────

class _LCRTransformer(ast.NodeTransformer):
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


class LCRBaseMutator(BaseMutator):
    CODE = "LCR"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for target_op, replacement_op in [(ast.And, ast.Or), (ast.Or, ast.And)]:
            t = _LCRTransformer(target_op, replacement_op)
            new_fn = t.visit(copy.deepcopy(fn_node))
            if t.mutated:
                sym = "and -> or" if target_op == ast.And else "or -> and"
                src = self._safe_to_source(new_fn)
                if src:
                    mutants.append(self._make_mutant(
                        id_="", file_path=file_path, fn_name=fn_node.name,
                        line_no=t.line_no or fn_node.lineno,
                        operator="LCR", description=sym,
                        original_src=fn_src, mutant_src=src))
        return mutants


# ── Boolean Constant Replacement (BCR) ─────────────────────────────────────

class _BCRTransformer(ast.NodeTransformer):
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


class BCRBaseMutator(BaseMutator):
    CODE = "BCR"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        t = _BCRTransformer()
        new_fn = t.visit(copy.deepcopy(fn_node))
        if t.mutated:
            src = self._safe_to_source(new_fn)
            if src:
                mutants.append(self._make_mutant(
                    id_="", file_path=file_path, fn_name=fn_node.name,
                    line_no=t.line_no or fn_node.lineno,
                    operator="BCR", description="True <-> False",
                    original_src=fn_src, mutant_src=src))
        return mutants


# ── Return Value Replacement (RVR) ─────────────────────────────────────────

class _RVRTransformer(ast.NodeTransformer):
    def __init__(self):
        self.mutated = False
        self.line_no = None

    def visit_Return(self, node):
        if node.value is not None and not self.mutated:
            self.mutated = True
            self.line_no = node.lineno
            return ast.Return(value=ast.Constant(value=None))
        return node


class RVRBaseMutator(BaseMutator):
    CODE = "RVR"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        t = _RVRTransformer()
        new_fn = t.visit(copy.deepcopy(fn_node))
        if t.mutated:
            src = self._safe_to_source(new_fn)
            if src:
                mutants.append(self._make_mutant(
                    id_="", file_path=file_path, fn_name=fn_node.name,
                    line_no=t.line_no or fn_node.lineno,
                    operator="RVR", description="return value -> None",
                    original_src=fn_src, mutant_src=src))
        return mutants


# ── Statement Deletion (SDL) ────────────────────────────────────────────────

class SDLMutator(BaseMutator):
    CODE = "SDL"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        stmts = fn_node.body
        for i, stmt in enumerate(stmts):
            if i == 0 or i == len(stmts) - 1:
                continue
            if isinstance(stmt, (ast.Return, ast.Import, ast.ImportFrom, ast.Pass)):
                continue
            if isinstance(stmt, (ast.Expr, ast.Assign, ast.Raise, ast.Assert)):
                new_fn = copy.deepcopy(fn_node)
                new_fn.body = [s for j, s in enumerate(fn_node.body) if j != i]
                try:
                    stmt_src = ast.unparse(stmt)
                except Exception:
                    stmt_src = "stmt"
                desc = f"deleted: {stmt_src[:60]}"
                src = self._safe_to_source(new_fn)
                if src:
                    mutants.append(self._make_mutant(
                        id_="", file_path=file_path, fn_name=fn_node.name,
                        line_no=stmt.lineno, operator="SDL", description=desc,
                        original_src=fn_src, mutant_src=src))
        return mutants


# ── Null / None Injection (NIM) ─────────────────────────────────────────────

class _NIMArgTransformer(ast.NodeTransformer):
    def __init__(self, target_lineno, target_col_offset, arg_index):
        self.target_lineno = target_lineno
        self.target_col_offset = target_col_offset
        self.arg_index = arg_index
        self.mutated = False

    def visit_Call(self, node):
        self.generic_visit(node)
        if (not self.mutated
                and getattr(node, 'lineno', None) == self.target_lineno
                and getattr(node, 'col_offset', None) == self.target_col_offset
                and len(node.args) > self.arg_index):
            new_node = copy.deepcopy(node)
            new_node.args[self.arg_index] = ast.Constant(value=None)
            self.mutated = True
            return new_node
        return node


class NIMMutator(BaseMutator):
    CODE = "NIM"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for node in ast.walk(fn_node):
            if isinstance(node, ast.Call):
                for i, arg in enumerate(node.args):
                    if isinstance(arg, ast.Name):
                        transformer = _NIMArgTransformer(
                            getattr(node, 'lineno', None),
                            getattr(node, 'col_offset', None),
                            i)
                        new_fn = transformer.visit(copy.deepcopy(fn_node))
                        if transformer.mutated:
                            arg_name = arg.id
                            desc = f"{arg_name} -> None in {_call_name(node)}()"
                            src = self._safe_to_source(new_fn)
                            if src:
                                mutants.append(self._make_mutant(
                                    id_="", file_path=file_path, fn_name=fn_node.name,
                                    line_no=getattr(node, 'lineno', fn_node.lineno),
                                    operator="NIM", description=desc,
                                    original_src=fn_src, mutant_src=src))
        return mutants


# ── Boundary Value Mutation (BVM) ───────────────────────────────────────────

class _NumericLiteralTransformer(ast.NodeTransformer):
    def __init__(self, target_lineno, target_col_offset, target_value, new_value):
        self.target_lineno = target_lineno
        self.target_col_offset = target_col_offset
        self.target_value = target_value
        self.new_value = new_value
        self.mutated = False

    def visit_Constant(self, node):
        if (not self.mutated
                and isinstance(node.value, (int, float))
                and not isinstance(node.value, bool)
                and node.value == self.target_value
                and getattr(node, 'lineno', None) == self.target_lineno
                and getattr(node, 'col_offset', None) == self.target_col_offset):
            self.mutated = True
            return ast.Constant(value=self.new_value)
        return node


class BVMMutator(BaseMutator):
    CODE = "BVM"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for node in ast.walk(fn_node):
            if (isinstance(node, ast.Constant)
                    and isinstance(node.value, (int, float))
                    and not isinstance(node.value, bool)):
                val = node.value
                lineno = getattr(node, 'lineno', None)
                col = getattr(node, 'col_offset', None)
                candidates = [
                    (val - 1, f"{val} -> {val - 1}"),
                    (val + 1, f"{val} -> {val + 1}"),
                ]
                if val != 0:
                    candidates.append((0, f"{val} -> 0"))
                for new_val, desc in candidates:
                    transformer = _NumericLiteralTransformer(lineno, col, val, new_val)
                    new_fn = transformer.visit(copy.deepcopy(fn_node))
                    if transformer.mutated:
                        src = self._safe_to_source(new_fn)
                        if src:
                            mutants.append(self._make_mutant(
                                id_="", file_path=file_path, fn_name=fn_node.name,
                                line_no=lineno or fn_node.lineno,
                                operator="BVM", description=desc,
                                original_src=fn_src, mutant_src=src))
        return mutants


# ── Exception Handling Mutation (EHM) ──────────────────────────────────────

class _RaiseRemover(ast.NodeTransformer):
    def __init__(self, target_lineno):
        self.target_lineno = target_lineno
        self.mutated = False

    def visit_Raise(self, node):
        if (not self.mutated
                and node.exc is not None
                and getattr(node, 'lineno', None) == self.target_lineno):
            self.mutated = True
            return ast.Pass()
        return node


class EHMMutator(BaseMutator):
    CODE = "EHM"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for node in ast.walk(fn_node):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    # 1. Replace except body with pass
                    new_fn = copy.deepcopy(fn_node)
                    _replace_handler_body(new_fn, handler, [ast.Pass()])
                    src = self._safe_to_source(new_fn)
                    if src:
                        mutants.append(self._make_mutant(
                            id_="", file_path=file_path, fn_name=fn_node.name,
                            line_no=handler.lineno, operator="EHM",
                            description="except body -> pass (swallowed exception)",
                            original_src=fn_src, mutant_src=src))

                    # 2. Swap exception type to Exception (catch-all)
                    if handler.type and not (
                            isinstance(handler.type, ast.Name)
                            and handler.type.id == "Exception"):
                        try:
                            exc_name = ast.unparse(handler.type)
                        except Exception:
                            exc_name = "exc"
                        new_fn2 = copy.deepcopy(fn_node)
                        _replace_handler_type(new_fn2, handler, ast.Name(id="Exception", ctx=ast.Load()))
                        src2 = self._safe_to_source(new_fn2)
                        if src2:
                            mutants.append(self._make_mutant(
                                id_="", file_path=file_path, fn_name=fn_node.name,
                                line_no=handler.lineno, operator="EHM",
                                description=f"except {exc_name} -> except Exception",
                                original_src=fn_src, mutant_src=src2))

            # 3. Remove raise statements
            if isinstance(node, ast.Raise) and node.exc is not None:
                raise_lineno = getattr(node, 'lineno', None)
                transformer = _RaiseRemover(raise_lineno)
                new_fn3 = transformer.visit(copy.deepcopy(fn_node))
                if transformer.mutated:
                    try:
                        exc_src = ast.unparse(node.exc)[:40]
                    except Exception:
                        exc_src = "exc"
                    src3 = self._safe_to_source(new_fn3)
                    if src3:
                        mutants.append(self._make_mutant(
                            id_="", file_path=file_path, fn_name=fn_node.name,
                            line_no=raise_lineno or fn_node.lineno,
                            operator="EHM", description=f"raise {exc_src} deleted",
                            original_src=fn_src, mutant_src=src3))
        return mutants


# ── Data Flow Mutation (DFM) ────────────────────────────────────────────────

class _NameSwapper(ast.NodeTransformer):
    def __init__(self, name1, name2):
        self.name1 = name1
        self.name2 = name2
        self.swapped = False

    def visit_Name(self, node):
        if node.id == self.name1:
            self.swapped = True
            return ast.Name(id=self.name2, ctx=node.ctx)
        if node.id == self.name2:
            self.swapped = True
            return ast.Name(id=self.name1, ctx=node.ctx)
        return node


class DFMMutator(BaseMutator):
    CODE = "DFM"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        params = [arg.arg for arg in fn_node.args.args if arg.arg != 'self']
        if len(params) < 2:
            return mutants

        pairs = self._find_swappable_pairs(params, fn_node)
        for p1, p2 in pairs:
            new_fn = copy.deepcopy(fn_node)
            transformer = _NameSwapper(p1, p2)
            new_fn = transformer.visit(new_fn)
            if transformer.swapped:
                src = self._safe_to_source(new_fn)
                if src:
                    mutants.append(self._make_mutant(
                        id_="", file_path=file_path, fn_name=fn_node.name,
                        line_no=fn_node.lineno, operator="DFM",
                        description=f"parameters {p1} <-> {p2} swapped",
                        original_src=fn_src, mutant_src=src))
        return mutants

    def _find_swappable_pairs(self, params, fn_node):
        pairs = []
        seen = set()
        for i, p1 in enumerate(params):
            for p2 in params[i + 1:]:
                key = (min(p1, p2), max(p1, p2))
                if key in seen:
                    continue
                seen.add(key)
                if self._is_used(p1, fn_node) and self._is_used(p2, fn_node):
                    pairs.append((p1, p2))
        return pairs[:3]

    def _is_used(self, name, fn_node):
        for node in ast.walk(fn_node):
            if isinstance(node, ast.Name) and node.id == name:
                return True
        return False


# ── String and Constant Mutation (SCM) ─────────────────────────────────────

OPPOSITES = {
    "active": "inactive", "inactive": "active",
    "open": "closed", "closed": "open",
    "enabled": "disabled", "disabled": "enabled",
    "true": "false", "false": "true",
    "success": "failure", "failure": "success",
    "pass": "fail", "fail": "pass",
    "admin": "guest", "guest": "admin",
    "yes": "no", "no": "yes",
}


class _StringLiteralTransformer(ast.NodeTransformer):
    def __init__(self, target_lineno, target_col_offset, target_value, new_value):
        self.target_lineno = target_lineno
        self.target_col_offset = target_col_offset
        self.target_value = target_value
        self.new_value = new_value
        self.mutated = False

    def visit_Constant(self, node):
        if (not self.mutated
                and isinstance(node.value, str)
                and node.value == self.target_value
                and getattr(node, 'lineno', None) == self.target_lineno
                and getattr(node, 'col_offset', None) == self.target_col_offset):
            self.mutated = True
            return ast.Constant(value=self.new_value)
        return node


class SCMMutator(BaseMutator):
    CODE = "SCM"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for node in ast.walk(fn_node):
            if (isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and node.value):
                val = node.value
                lineno = getattr(node, 'lineno', None)
                col = getattr(node, 'col_offset', None)
                candidates = [("", f'"{val}" -> ""')]
                if val != val.upper():
                    candidates.append((val.upper(), f'"{val}" -> "{val.upper()}"'))
                lower = val.lower()
                if lower in OPPOSITES:
                    opp = OPPOSITES[lower]
                    candidates.append((opp, f'"{val}" -> "{opp}"'))
                for new_val, desc in candidates:
                    transformer = _StringLiteralTransformer(lineno, col, val, new_val)
                    new_fn = transformer.visit(copy.deepcopy(fn_node))
                    if transformer.mutated:
                        src = self._safe_to_source(new_fn)
                        if src:
                            mutants.append(self._make_mutant(
                                id_="", file_path=file_path, fn_name=fn_node.name,
                                line_no=lineno or fn_node.lineno,
                                operator="SCM", description=desc,
                                original_src=fn_src, mutant_src=src))
        return mutants


# ── Loop Mutation (LMO) ─────────────────────────────────────────────────────

class _ForIterTransformer(ast.NodeTransformer):
    def __init__(self, target_lineno, lower=None, upper=None):
        self.target_lineno = target_lineno
        self.lower = lower
        self.upper = upper
        self.mutated = False

    def visit_For(self, node):
        self.generic_visit(node)
        if not self.mutated and getattr(node, 'lineno', None) == self.target_lineno:
            new_node = copy.deepcopy(node)
            lower_node = ast.Constant(value=self.lower) if self.lower is not None else None
            if self.upper is not None and self.upper < 0:
                upper_node = ast.UnaryOp(
                    op=ast.USub(),
                    operand=ast.Constant(value=abs(self.upper)))
            elif self.upper is not None:
                upper_node = ast.Constant(value=self.upper)
            else:
                upper_node = None
            slice_node = ast.Slice(lower=lower_node, upper=upper_node)
            new_node.iter = ast.Subscript(
                value=copy.deepcopy(node.iter),
                slice=slice_node,
                ctx=ast.Load())
            self.mutated = True
            return new_node
        return node


class _WhileCondTransformer(ast.NodeTransformer):
    def __init__(self, target_lineno, new_test):
        self.target_lineno = target_lineno
        self.new_test = new_test
        self.mutated = False

    def visit_While(self, node):
        self.generic_visit(node)
        if not self.mutated and getattr(node, 'lineno', None) == self.target_lineno:
            new_node = copy.deepcopy(node)
            new_node.test = self.new_test
            self.mutated = True
            return new_node
        return node


class LMOMutator(BaseMutator):
    CODE = "LMO"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for node in ast.walk(fn_node):
            lineno = getattr(node, 'lineno', None)

            if isinstance(node, ast.For):
                for lower, upper, desc in [
                    (1, None, "for loop: skip first element"),
                    (None, -1, "for loop: skip last element"),
                    (None, 1, "for loop: only first element"),
                ]:
                    t = _ForIterTransformer(lineno, lower=lower, upper=upper)
                    new_fn = t.visit(copy.deepcopy(fn_node))
                    if t.mutated:
                        src = self._safe_to_source(new_fn)
                        if src:
                            mutants.append(self._make_mutant(
                                id_="", file_path=file_path, fn_name=fn_node.name,
                                line_no=lineno or fn_node.lineno, operator="LMO",
                                description=desc,
                                original_src=fn_src, mutant_src=src))

            elif isinstance(node, ast.While):
                for new_test, desc in [
                    (ast.Constant(value=True), "while condition -> True (infinite loop)"),
                    (ast.Constant(value=False), "while condition -> False (never executes)"),
                    (ast.UnaryOp(op=ast.Not(), operand=copy.deepcopy(node.test)),
                     "while condition negated"),
                ]:
                    t = _WhileCondTransformer(lineno, new_test)
                    new_fn = t.visit(copy.deepcopy(fn_node))
                    if t.mutated:
                        src = self._safe_to_source(new_fn)
                        if src:
                            mutants.append(self._make_mutant(
                                id_="", file_path=file_path, fn_name=fn_node.name,
                                line_no=lineno or fn_node.lineno, operator="LMO",
                                description=desc,
                                original_src=fn_src, mutant_src=src))
        return mutants


# ── Async Mutation (AMO) ────────────────────────────────────────────────────

class _AwaitRemover(ast.NodeTransformer):
    def __init__(self, target_lineno):
        self.target_lineno = target_lineno
        self.mutated = False

    def visit_Await(self, node):
        if not self.mutated and getattr(node, 'lineno', None) == self.target_lineno:
            self.mutated = True
            return node.value  # return inner expression without await
        return node


class _AsyncWithToSync(ast.NodeTransformer):
    def __init__(self, target_lineno):
        self.target_lineno = target_lineno
        self.mutated = False

    def visit_AsyncWith(self, node):
        self.generic_visit(node)
        if not self.mutated and getattr(node, 'lineno', None) == self.target_lineno:
            self.mutated = True
            new_node = ast.With(items=node.items, body=node.body)
            ast.copy_location(new_node, node)
            return new_node
        return node


class AMOMutator(BaseMutator):
    CODE = "AMO"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        if not isinstance(fn_node, ast.AsyncFunctionDef):
            return mutants

        for node in ast.walk(fn_node):
            if isinstance(node, ast.Await):
                transformer = _AwaitRemover(getattr(node, 'lineno', None))
                new_fn = transformer.visit(copy.deepcopy(fn_node))
                if transformer.mutated:
                    src = self._safe_to_source(new_fn)
                    if src:
                        mutants.append(self._make_mutant(
                            id_="", file_path=file_path, fn_name=fn_node.name,
                            line_no=getattr(node, 'lineno', fn_node.lineno),
                            operator="AMO",
                            description="await removed — returns coroutine object",
                            original_src=fn_src, mutant_src=src))

        for node in ast.walk(fn_node):
            if isinstance(node, ast.AsyncWith):
                transformer = _AsyncWithToSync(getattr(node, 'lineno', None))
                new_fn = transformer.visit(copy.deepcopy(fn_node))
                if transformer.mutated:
                    src = self._safe_to_source(new_fn)
                    if src:
                        mutants.append(self._make_mutant(
                            id_="", file_path=file_path, fn_name=fn_node.name,
                            line_no=getattr(node, 'lineno', fn_node.lineno),
                            operator="AMO", description="async with -> sync with",
                            original_src=fn_src, mutant_src=src))
        return mutants


# ── API/Integration Mutation (AIM) ─────────────────────────────────────────

HTTP_METHODS = {
    "get":    ["post", "put"],
    "post":   ["get", "put"],
    "put":    ["get", "post"],
    "delete": ["get"],
    "patch":  ["put", "get"],
}
DB_SWAPS = {"save": "delete", "find": "update", "update": "find"}


class _MethodNameSwapper(ast.NodeTransformer):
    def __init__(self, target_lineno, target_col_offset, replacement):
        self.target_lineno = target_lineno
        self.target_col_offset = target_col_offset
        self.replacement = replacement
        self.mutated = False

    def visit_Call(self, node):
        self.generic_visit(node)
        if (not self.mutated
                and isinstance(node.func, ast.Attribute)
                and getattr(node, 'lineno', None) == self.target_lineno
                and getattr(node, 'col_offset', None) == self.target_col_offset):
            new_node = copy.deepcopy(node)
            new_node.func.attr = self.replacement
            self.mutated = True
            return new_node
        return node


class AIMMutator(BaseMutator):
    CODE = "AIM"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for node in ast.walk(fn_node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                method = node.func.attr
                lineno = getattr(node, 'lineno', fn_node.lineno)
                col = getattr(node, 'col_offset', 0)

                if method in HTTP_METHODS:
                    for replacement in HTTP_METHODS[method]:
                        transformer = _MethodNameSwapper(lineno, col, replacement)
                        new_fn = transformer.visit(copy.deepcopy(fn_node))
                        if transformer.mutated:
                            src = self._safe_to_source(new_fn)
                            if src:
                                mutants.append(self._make_mutant(
                                    id_="", file_path=file_path, fn_name=fn_node.name,
                                    line_no=lineno, operator="AIM",
                                    description=f".{method}() -> .{replacement}()",
                                    original_src=fn_src, mutant_src=src))

                if method in DB_SWAPS:
                    replacement = DB_SWAPS[method]
                    transformer = _MethodNameSwapper(lineno, col, replacement)
                    new_fn = transformer.visit(copy.deepcopy(fn_node))
                    if transformer.mutated:
                        src = self._safe_to_source(new_fn)
                        if src:
                            mutants.append(self._make_mutant(
                                id_="", file_path=file_path, fn_name=fn_node.name,
                                line_no=lineno, operator="AIM",
                                description=f".{method}() -> .{replacement}() (destructive swap)",
                                original_src=fn_src, mutant_src=src))
        return mutants


# ── Type Coercion Mutation (TCM) ────────────────────────────────────────────

TYPE_SWAPS = {
    "int":   ["str", "float"],
    "str":   ["int", "repr"],
    "float": ["int", "str"],
    "bool":  ["int"],
}


class _CallReplacer(ast.NodeTransformer):
    def __init__(self, target_lineno, target_col_offset, replacement_node):
        self.target_lineno = target_lineno
        self.target_col_offset = target_col_offset
        self.replacement_node = replacement_node
        self.mutated = False

    def visit_Call(self, node):
        self.generic_visit(node)
        if (not self.mutated
                and getattr(node, 'lineno', None) == self.target_lineno
                and getattr(node, 'col_offset', None) == self.target_col_offset):
            self.mutated = True
            return copy.deepcopy(self.replacement_node)
        return node


class TCMMutator(BaseMutator):
    CODE = "TCM"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for node in ast.walk(fn_node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                fn_name_called = node.func.id
                lineno = getattr(node, 'lineno', fn_node.lineno)
                col = getattr(node, 'col_offset', 0)

                if fn_name_called in TYPE_SWAPS and len(node.args) == 1:
                    arg = node.args[0]
                    # 1. Remove cast: int(x) -> x
                    transformer = _CallReplacer(lineno, col, copy.deepcopy(arg))
                    new_fn = transformer.visit(copy.deepcopy(fn_node))
                    if transformer.mutated:
                        src = self._safe_to_source(new_fn)
                        if src:
                            mutants.append(self._make_mutant(
                                id_="", file_path=file_path, fn_name=fn_node.name,
                                line_no=lineno, operator="TCM",
                                description=f"{fn_name_called}() cast removed",
                                original_src=fn_src, mutant_src=src))
                    # 2. Swap cast type
                    for alt_type in TYPE_SWAPS[fn_name_called]:
                        new_call = ast.Call(
                            func=ast.Name(id=alt_type, ctx=ast.Load()),
                            args=[copy.deepcopy(arg)],
                            keywords=[])
                        ast.fix_missing_locations(new_call)
                        transformer2 = _CallReplacer(lineno, col, new_call)
                        new_fn2 = transformer2.visit(copy.deepcopy(fn_node))
                        if transformer2.mutated:
                            src2 = self._safe_to_source(new_fn2)
                            if src2:
                                mutants.append(self._make_mutant(
                                    id_="", file_path=file_path, fn_name=fn_node.name,
                                    line_no=lineno, operator="TCM",
                                    description=f"{fn_name_called}() -> {alt_type}()",
                                    original_src=fn_src, mutant_src=src2))

                if fn_name_called == "len" and len(node.args) == 1:
                    arg = node.args[0]
                    transformer = _CallReplacer(lineno, col, copy.deepcopy(arg))
                    new_fn = transformer.visit(copy.deepcopy(fn_node))
                    if transformer.mutated:
                        src = self._safe_to_source(new_fn)
                        if src:
                            mutants.append(self._make_mutant(
                                id_="", file_path=file_path, fn_name=fn_node.name,
                                line_no=lineno, operator="TCM",
                                description="len() removed",
                                original_src=fn_src, mutant_src=src))
        return mutants


# ── Decorator/Visibility Mutation (DVM) ────────────────────────────────────

class DVMMutator(BaseMutator):
    CODE = "DVM"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        if not fn_node.decorator_list:
            return mutants

        for i, dec in enumerate(fn_node.decorator_list):
            dec_name = self._dec_name(dec)
            # 1. Remove decorator
            new_fn = copy.deepcopy(fn_node)
            new_fn.decorator_list = [d for j, d in enumerate(fn_node.decorator_list) if j != i]
            src = self._safe_to_source(new_fn)
            if src:
                mutants.append(self._make_mutant(
                    id_="", file_path=file_path, fn_name=fn_node.name,
                    line_no=fn_node.lineno, operator="DVM",
                    description=f"@{dec_name} decorator removed",
                    original_src=fn_src, mutant_src=src))

            # 2. Swap @staticmethod <-> @classmethod
            if dec_name == "staticmethod":
                new_fn2 = copy.deepcopy(fn_node)
                new_fn2.decorator_list[i] = ast.Name(id="classmethod", ctx=ast.Load())
                src2 = self._safe_to_source(new_fn2)
                if src2:
                    mutants.append(self._make_mutant(
                        id_="", file_path=file_path, fn_name=fn_node.name,
                        line_no=fn_node.lineno, operator="DVM",
                        description="@staticmethod -> @classmethod",
                        original_src=fn_src, mutant_src=src2))
            elif dec_name == "classmethod":
                new_fn2 = copy.deepcopy(fn_node)
                new_fn2.decorator_list[i] = ast.Name(id="staticmethod", ctx=ast.Load())
                src2 = self._safe_to_source(new_fn2)
                if src2:
                    mutants.append(self._make_mutant(
                        id_="", file_path=file_path, fn_name=fn_node.name,
                        line_no=fn_node.lineno, operator="DVM",
                        description="@classmethod -> @staticmethod",
                        original_src=fn_src, mutant_src=src2))
        return mutants

    def _dec_name(self, dec):
        if isinstance(dec, ast.Name):
            return dec.id
        if isinstance(dec, ast.Attribute):
            return dec.attr
        if isinstance(dec, ast.Call):
            return self._dec_name(dec.func)
        return "?"


# ── Configuration/Environment Mutation (CEM) ───────────────────────────────

class _NodeReplacer(ast.NodeTransformer):
    """Replace a Call node at a specific location with a replacement node."""
    def __init__(self, target_lineno, target_col_offset, replacement_node):
        self.target_lineno = target_lineno
        self.target_col_offset = target_col_offset
        self.replacement_node = replacement_node
        self.mutated = False

    def visit_Call(self, node):
        self.generic_visit(node)
        if (not self.mutated
                and getattr(node, 'lineno', None) == self.target_lineno
                and getattr(node, 'col_offset', None) == self.target_col_offset):
            self.mutated = True
            return copy.deepcopy(self.replacement_node)
        return node


class CEMMutator(BaseMutator):
    CODE = "CEM"

    def generate(self, fn_node, fn_src, file_path):
        mutants = []
        for node in ast.walk(fn_node):
            if isinstance(node, ast.Call):
                lineno = getattr(node, 'lineno', fn_node.lineno)
                col = getattr(node, 'col_offset', 0)

                if self._is_environ_get(node):
                    # Replace with default value if present
                    if len(node.args) >= 2:
                        default_val = node.args[1]
                        transformer = _NodeReplacer(lineno, col, copy.deepcopy(default_val))
                        new_fn = transformer.visit(copy.deepcopy(fn_node))
                        if transformer.mutated:
                            try:
                                key = ast.unparse(node.args[0])
                            except Exception:
                                key = "key"
                            src = self._safe_to_source(new_fn)
                            if src:
                                mutants.append(self._make_mutant(
                                    id_="", file_path=file_path, fn_name=fn_node.name,
                                    line_no=lineno, operator="CEM",
                                    description=f"env var {key} removed — always uses default",
                                    original_src=fn_src, mutant_src=src))

                    # Replace with empty string
                    transformer2 = _NodeReplacer(lineno, col, ast.Constant(value=""))
                    new_fn2 = transformer2.visit(copy.deepcopy(fn_node))
                    if transformer2.mutated:
                        try:
                            key = ast.unparse(node.args[0]) if node.args else "key"
                        except Exception:
                            key = "key"
                        src2 = self._safe_to_source(new_fn2)
                        if src2:
                            mutants.append(self._make_mutant(
                                id_="", file_path=file_path, fn_name=fn_node.name,
                                line_no=lineno, operator="CEM",
                                description=f"env var {key} always returns empty string",
                                original_src=fn_src, mutant_src=src2))
        return mutants

    def _is_environ_get(self, node):
        if not isinstance(node.func, ast.Attribute):
            return False
        attr = node.func
        if attr.attr not in ("get", "getenv"):
            return False
        if isinstance(attr.value, ast.Attribute) and attr.value.attr == "environ":
            return True
        if isinstance(attr.value, ast.Name) and attr.value.id in ("environ", "config", "settings", "os"):
            return True
        return False


# ── All registered mutators ─────────────────────────────────────────────────

_ALL_MUTATOR_CLASSES = [
    AORBaseMutator,
    RORBaseMutator,
    LCRBaseMutator,
    BCRBaseMutator,
    RVRBaseMutator,
    SDLMutator,
    NIMMutator,
    BVMMutator,
    EHMMutator,
    DFMMutator,
    SCMMutator,
    LMOMutator,
    AMOMutator,
    AIMMutator,
    TCMMutator,
    DVMMutator,
    CEMMutator,
]

OPERATOR_METADATA = {
    "AOR": {"name": "Arithmetic Operator Replacement", "description": "Swaps arithmetic operators: + - * / // %"},
    "ROR": {"name": "Relational Operator Replacement", "description": "Swaps comparison operators: == != > >= < <="},
    "LCR": {"name": "Logical Connector Replacement", "description": "Swaps logical operators: and <-> or"},
    "BCR": {"name": "Boolean Constant Replacement", "description": "Flips True <-> False"},
    "RVR": {"name": "Return Value Replacement", "description": "Replaces return value with None"},
    "SDL": {"name": "Statement Deletion", "description": "Deletes statements from function body"},
    "NIM": {"name": "Null/None Injection", "description": "Replaces variable arguments with None"},
    "BVM": {"name": "Boundary Value Mutation", "description": "Shifts numeric literals by +1/-1 or to 0"},
    "EHM": {"name": "Exception Handling Mutation", "description": "Swallows exceptions, removes raises, widens except clauses"},
    "DFM": {"name": "Data Flow Mutation", "description": "Swaps function parameter names in body"},
    "SCM": {"name": "String and Constant Mutation", "description": "Mutates string literals: empty, uppercase, opposites"},
    "LMO": {"name": "Loop Mutation", "description": "Skips first/last element, negates while conditions"},
    "AMO": {"name": "Async Mutation", "description": "Removes await, converts async with to sync with"},
    "AIM": {"name": "API/Integration Mutation", "description": "Swaps HTTP verbs, DB method names"},
    "TCM": {"name": "Type Coercion Mutation", "description": "Removes type casts, swaps int/str/float"},
    "DVM": {"name": "Decorator/Visibility Mutation", "description": "Removes decorators, swaps @staticmethod/@classmethod"},
    "CEM": {"name": "Configuration/Environment Mutation", "description": "Bypasses env var lookups with defaults or empty string"},
}


# ── Engine ──────────────────────────────────────────────────────────────────

class MutationEngine:
    def __init__(self, enable="all"):
        self._mutant_counter = 0
        if enable == "all":
            self.mutators = [cls() for cls in _ALL_MUTATOR_CLASSES]
        else:
            enabled_set = set(enable) if not isinstance(enable, str) else {enable}
            self.mutators = [cls() for cls in _ALL_MUTATOR_CLASSES if cls.CODE in enabled_set]

    def _next_id(self) -> str:
        self._mutant_counter += 1
        return f"M{self._mutant_counter:04d}"

    def generate_mutants(self, file_path: str) -> List[Mutant]:
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        except Exception:
            return []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        mutants = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                try:
                    fn_src = astor.to_source(node)
                except Exception:
                    try:
                        fn_src = ast.unparse(node)
                    except Exception:
                        fn_src = ""

                for mutator in self.mutators:
                    try:
                        raw = mutator.generate(node, fn_src, file_path)
                        for m in raw:
                            m.id = self._next_id()
                            mutants.append(m)
                    except Exception:
                        continue  # skip this mutator for this function on error

        return mutants

    @staticmethod
    def _op_symbol(op_class) -> str:
        return {
            ast.Add:      "+",
            ast.Sub:      "-",
            ast.Mult:     "*",
            ast.Div:      "/",
            ast.FloorDiv: "//",
            ast.Mod:      "%",
            ast.Eq:       "==",
            ast.NotEq:    "!=",
            ast.Lt:       "<",
            ast.LtE:      "<=",
            ast.Gt:       ">",
            ast.GtE:      ">=",
            ast.And:      "and",
            ast.Or:       "or",
        }.get(op_class, str(op_class))
