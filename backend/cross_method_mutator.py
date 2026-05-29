"""
cross_method_mutator.py
Game Changer 3: finds caller→callee relationships in Python AST and
generates interaction-level mutants at function call boundaries.
Operator prefix: CMR (Cross-Method Replacement)
"""
import ast
import copy
import astor
from typing import Dict, List, Optional, Set

from mutation_engine import Mutant


# ── Call-graph builder ─────────────────────────────────────────────────────

class _CallGraphBuilder(ast.NodeVisitor):
    """Walks the AST and maps each function to the set of internal functions it calls."""

    def __init__(self, internal_names: Set[str]):
        self.internal = internal_names
        self.current: Optional[str] = None
        self.graph: Dict[str, Set[str]] = {}         # caller → {callee, ...}
        self.call_sites: Dict[str, List[ast.Call]] = {}  # caller → [Call nodes]

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev = self.current
        self.current = node.name
        self.graph.setdefault(node.name, set())
        self.call_sites.setdefault(node.name, [])
        self.generic_visit(node)
        self.current = prev

    def visit_Call(self, node: ast.Call):
        if self.current and isinstance(node.func, ast.Name):
            callee = node.func.id
            if callee in self.internal and callee != self.current:
                self.graph[self.current].add(callee)
                self.call_sites[self.current].append(node)
        self.generic_visit(node)


# ── Interaction mutators ───────────────────────────────────────────────────

class _ArgSwapper(ast.NodeTransformer):
    """Reverse the argument list on the first matching call."""
    def __init__(self, callee: str):
        self.callee = callee
        self.mutated = False

    def visit_Call(self, node: ast.Call):
        self.generic_visit(node)
        if (not self.mutated and
                isinstance(node.func, ast.Name) and
                node.func.id == self.callee and
                len(node.args) >= 2):
            self.mutated = True
            new = copy.deepcopy(node)
            new.args = list(reversed(new.args))
            return new
        return node


class _FirstArgNone(ast.NodeTransformer):
    """Replace the first positional argument with None on the first matching call."""
    def __init__(self, callee: str):
        self.callee = callee
        self.mutated = False

    def visit_Call(self, node: ast.Call):
        self.generic_visit(node)
        if (not self.mutated and
                isinstance(node.func, ast.Name) and
                node.func.id == self.callee and
                len(node.args) >= 1):
            self.mutated = True
            new = copy.deepcopy(node)
            new.args[0] = ast.Constant(value=None)
            return new
        return node


class _ReturnValueDiscarder(ast.NodeTransformer):
    """Replace `return callee(...)` with `return None`, discarding the result."""
    def __init__(self, callee: str):
        self.callee = callee
        self.mutated = False

    def visit_Return(self, node: ast.Return):
        if (not self.mutated and
                node.value is not None and
                isinstance(node.value, ast.Call) and
                isinstance(node.value.func, ast.Name) and
                node.value.func.id == self.callee):
            self.mutated = True
            return ast.Return(value=ast.Constant(value=None))
        return node


# ── Main class ─────────────────────────────────────────────────────────────

class CrossMethodMutator:
    def __init__(self):
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"CMR{self._counter:04d}"

    def generate_mutants(self, file_path: str) -> List[Mutant]:
        with open(file_path) as f:
            source = f.read()

        tree = ast.parse(source)

        # Collect all function names defined in this file
        internal = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }

        builder = _CallGraphBuilder(internal)
        builder.visit(tree)

        fn_nodes: Dict[str, ast.FunctionDef] = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }

        mutants: List[Mutant] = []
        for caller_name, callees in builder.graph.items():
            if caller_name not in fn_nodes:
                continue
            caller_node = fn_nodes[caller_name]
            caller_src = astor.to_source(caller_node)

            for callee_name in sorted(callees):
                mutants.extend(
                    self._make_mutants(
                        caller_node, caller_src, callee_name, file_path
                    )
                )
        return mutants

    def _make_mutants(
        self,
        caller: ast.FunctionDef,
        caller_src: str,
        callee: str,
        file_path: str,
    ) -> List[Mutant]:
        results: List[Mutant] = []

        # ── CMR-1: swap argument order ──────────────────────────────────────
        swapper = _ArgSwapper(callee)
        new_tree = swapper.visit(copy.deepcopy(caller))
        if swapper.mutated:
            results.append(Mutant(
                id=self._next_id(),
                file_path=file_path,
                function_name=caller.name,
                line_no=caller.lineno,
                operator="CMR",
                description=f"swap args in call to {callee}()",
                original_src=caller_src,
                mutant_src=astor.to_source(new_tree),
            ))

        # ── CMR-2: replace first arg with None ──────────────────────────────
        nullifier = _FirstArgNone(callee)
        new_tree = nullifier.visit(copy.deepcopy(caller))
        if nullifier.mutated:
            results.append(Mutant(
                id=self._next_id(),
                file_path=file_path,
                function_name=caller.name,
                line_no=caller.lineno,
                operator="CMR",
                description=f"pass None as first arg to {callee}()",
                original_src=caller_src,
                mutant_src=astor.to_source(new_tree),
            ))

        # ── CMR-3: discard return value ─────────────────────────────────────
        discarder = _ReturnValueDiscarder(callee)
        new_tree = discarder.visit(copy.deepcopy(caller))
        if discarder.mutated:
            results.append(Mutant(
                id=self._next_id(),
                file_path=file_path,
                function_name=caller.name,
                line_no=caller.lineno,
                operator="CMR",
                description=f"discard return value of {callee}()",
                original_src=caller_src,
                mutant_src=astor.to_source(new_tree),
            ))

        return results


# ── Debug helper ───────────────────────────────────────────────────────────

def list_interactions(file_path: str):
    """Print all internal caller → callee relationships found in a file."""
    with open(file_path) as f:
        source = f.read()
    tree = ast.parse(source)
    internal = {
        n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
    }
    builder = _CallGraphBuilder(internal)
    builder.visit(tree)

    print(f"\nCall graph for: {file_path}")
    print("-" * 50)
    found = False
    for caller, callees in sorted(builder.graph.items()):
        for callee in sorted(callees):
            print(f"  {caller}() -> {callee}()")
            found = True
    if not found:
        print("  (no internal call relationships found)")
    print("-" * 50)


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "../sample_project/math_utils.py"
    list_interactions(target)
    mutator = CrossMethodMutator()
    mutants = mutator.generate_mutants(target)
    print(f"\nGenerated {len(mutants)} cross-method mutants")
    for m in mutants:
        print(f"  {m.id}  {m.function_name}()  [{m.description}]")
