import ast
import pathlib
from typing import Dict, Set, List


def _collect_definitions(tree: ast.AST, module: str) -> Dict[str, Set[str]]:
    """Collect function and class definitions with fully‑qualified names.
    Returns a dict mapping definition name -> empty set (callers will be filled later)."""
    defs: Dict[str, Set[str]] = {}

    class DefVisitor(ast.NodeVisitor):
        def __init__(self):
            self.class_stack: List[str] = []

        def _qualname(self, name: str) -> str:
            parts = [module]
            if self.class_stack:
                parts.extend(self.class_stack)
            parts.append(name)
            return ".".join(parts)

        def visit_FunctionDef(self, node: ast.FunctionDef):
            qname = self._qualname(node.name)
            defs[qname] = set()
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self.visit_FunctionDef(node)

        def visit_ClassDef(self, node: ast.ClassDef):
            qname = self._qualname(node.name)
            defs[qname] = set()
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

    DefVisitor().visit(tree)
    return defs


def _collect_calls(tree: ast.AST) -> List[str]:
    """Collect simple call names (e.g., func(), obj.method())."""
    calls: List[str] = []

    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            # Handle Name and Attribute call forms
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                # Build dotted name (obj.attr1.attr2...)
                parts = []
                cur = node.func
                while isinstance(cur, ast.Attribute):
                    parts.append(cur.attr)
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    parts.append(cur.id)
                calls.append(".".join(reversed(parts)))
            self.generic_visit(node)

    CallVisitor().visit(tree)
    return calls


def build_call_graph() -> Dict[str, Set[str]]:
    """Return a mapping of symbol -> set of callers.
    The analysis walks all ``.py`` files under ``src/hcode`` (excluding tests).
    Only intra‑package symbols are tracked – external library calls are ignored.
    """
    root = pathlib.Path('src/hcode')
    # Gather all python files (skip tests & __pycache__)
    py_files = [p for p in root.rglob('*.py') if 'tests' not in p.parts and '__pycache__' not in p.parts]

    # First pass: collect definitions
    graph: Dict[str, Set[str]] = {}
    for file_path in py_files:
        try:
            source = file_path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(file_path))
        except Exception:
            continue  # Skip files that cannot be parsed
        module_name = '.'.join(file_path.with_suffix('').parts[-(len(file_path.parts)-1):])  # e.g., src.hcode.utils.config -> hcode.utils.config
        defs = _collect_definitions(tree, module_name)
        graph.update(defs)

    # Second pass: collect calls and link callers to definitions
    for file_path in py_files:
        try:
            source = file_path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(file_path))
        except Exception:
            continue
        module_name = '.'.join(file_path.with_suffix('').parts[-(len(file_path.parts)-1):])
        # Determine the current function/class context while walking
        class ContextVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current: List[str] = []  # stack of qualified names

            def _push(self, name: str):
                self.current.append(name)

            def _pop(self):
                self.current.pop()

            def _qualname(self, name: str) -> str:
                parts = [module_name]
                parts.extend(self.current)
                parts.append(name)
                return '.'.join(parts)

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._push(node.name)
                self.generic_visit(node)
                self._pop()

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self.visit_FunctionDef(node)

            def visit_ClassDef(self, node: ast.ClassDef):
                self._push(node.name)
                self.generic_visit(node)
                self._pop()

            def visit_Call(self, node: ast.Call):
                # Resolve called name (simple heuristic)
                if isinstance(node.func, ast.Name):
                    called = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    parts = []
                    cur = node.func
                    while isinstance(cur, ast.Attribute):
                        parts.append(cur.attr)
                        cur = cur.value
                    if isinstance(cur, ast.Name):
                        parts.append(cur.id)
                    called = '.'.join(reversed(parts))
                else:
                    called = None

                if called:
                    # Build caller name (module + stack)
                    caller = '.'.join([module_name] + self.current) if self.current else module_name
                    # Record edge if the callee is a known definition
                    for def_name in graph.keys():
                        if def_name.endswith('.' + called) or def_name == called:
                            graph.setdefault(def_name, set()).add(caller)
                self.generic_visit(node)

        ContextVisitor().visit(tree)

    return graph
