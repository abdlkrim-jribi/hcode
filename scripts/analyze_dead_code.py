#!/usr/bin/env python3
"""
Enhanced dead code analyzer that accounts for:
- CLI decorators (@click.command, @click.group)
- Dynamic calls (getattr, __init__, protocols)
- Configuration files
- Entry points
"""
import ast
import pathlib
import json
from typing import Dict, Set, List, Tuple
from collections import defaultdict


ENTRY_POINTS = [
    'hcode.main_cli',
    'hcode.__main__',
    'hcode.core.agent',
]

# Patterns that indicate code is NOT dead even if not directly called
KEEP_PATTERNS = [
    '__init__',
    '__main__',
    '__str__',
    '__repr__',
    'execute',  # Protocol methods
    'to_dict',
    'from_dict',
    'validate',
]

# Decorators that make functions entry points
ENTRY_DECORATORS = [
    'click.command',
    'click.group',
    'property',
    'classmethod',
    'staticmethod',
]


def is_likely_public_api(name: str) -> bool:
    """Check if a name looks like public API."""
    parts = name.split('.')
    last = parts[-1]
    
    # Check keep patterns
    for pattern in KEEP_PATTERNS:
        if pattern in last:
            return True
    
    # Not private (doesn't start with _)
    if not last.startswith('_'):
        # Check if it's a class (capitalized)
        if last[0].isupper():
            return True
    
    return False


def has_entry_decorator(node: ast.FunctionDef) -> bool:
    """Check if function has an entry point decorator."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            if decorator.id in ['command', 'group', 'property', 'classmethod', 'staticmethod']:
                return True
        elif isinstance(decorator, ast.Attribute):
            attr_name = f"{decorator.value.id if isinstance(decorator.value, ast.Name) else ''}.{decorator.attr}"
            if any(pattern in attr_name for pattern in ENTRY_DECORATORS):
                return True
    return False


def collect_definitions_enhanced(tree: ast.AST, module: str) -> Dict[str, Dict]:
    """Collect definitions with metadata."""
    defs: Dict[str, Dict] = {}
    
    class DefVisitor(ast.NodeVisitor):
        def __init__(self):
            self.class_stack: List[str] = []
        
        def _qualname(self, name: str) -> str:
            parts = [module]
            if self.class_stack:
                parts.extend(self.class_stack)
            parts.append(name)
            return '.'.join(parts)
        
        def visit_FunctionDef(self, node: ast.FunctionDef):
            qname = self._qualname(node.name)
            defs[qname] = {
                'type': 'function',
                'is_entry': has_entry_decorator(node),
                'is_public_api': is_likely_public_api(qname),
                'line': node.lineno,
            }
            self.generic_visit(node)
        
        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self.visit_FunctionDef(node)
        
        def visit_ClassDef(self, node: ast.ClassDef):
            qname = self._qualname(node.name)
            defs[qname] = {
                'type': 'class',
                'is_entry': False,
                'is_public_api': is_likely_public_api(qname),
                'line': node.lineno,
            }
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()
    
    DefVisitor().visit(tree)
    return defs


def build_enhanced_call_graph() -> Tuple[Dict[str, Set[str]], Dict[str, Dict]]:
    """Build call graph with metadata."""
    root = pathlib.Path('src/hcode')
    py_files = [p for p in root.rglob('*.py') 
                if 'tests' not in p.parts and '__pycache__' not in p.parts]
    
    # Collect all definitions with metadata
    all_defs: Dict[str, Dict] = {}
    graph: Dict[str, Set[str]] = defaultdict(set)
    
    for file_path in py_files:
        try:
            source = file_path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(file_path))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            continue
        
        # Build module name
        rel_parts = file_path.relative_to(pathlib.Path('src')).with_suffix('').parts
        module_name = '.'.join(rel_parts)
        
        defs = collect_definitions_enhanced(tree, module_name)
        all_defs.update(defs)
    
    # Second pass: collect calls
    for file_path in py_files:
        try:
            source = file_path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(file_path))
        except Exception:
            continue
        
        rel_parts = file_path.relative_to(pathlib.Path('src')).with_suffix('').parts
        module_name = '.'.join(rel_parts)
        
        class CallVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_context = []
            
            def visit_FunctionDef(self, node):
                self.current_context.append(node.name)
                self.generic_visit(node)
                self.current_context.pop()
            
            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)
            
            def visit_ClassDef(self, node):
                self.current_context.append(node.name)
                self.generic_visit(node)
                self.current_context.pop()
            
            def visit_Call(self, node):
                # Extract called name
                called = None
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
                
                if called:
                    caller = '.'.join([module_name] + self.current_context) if self.current_context else module_name
                    # Try to match to known definitions
                    for def_name in all_defs.keys():
                        if def_name.endswith('.' + called) or def_name == called:
                            graph[def_name].add(caller)
                
                self.generic_visit(node)
        
        CallVisitor().visit(tree)
    
    return dict(graph), all_defs


def analyze_dead_code():
    """Analyze and categorize potentially dead code."""
    print("Building call graph...")
    graph, all_defs = build_enhanced_call_graph()
    
    # Categorize unreferenced symbols
    categories = {
        'entry_points': [],
        'public_api': [],
        'likely_dead': [],
        'protocol_methods': [],
    }
    
    for name, metadata in all_defs.items():
        callers = graph.get(name, set())
        
        if callers:
            continue  # Has callers, not dead
        
        # Categorize unreferenced
        if metadata['is_entry']:
            categories['entry_points'].append((name, metadata))
        elif metadata['is_public_api']:
            categories['public_api'].append((name, metadata))
        elif any(pattern in name for pattern in KEEP_PATTERNS):
            categories['protocol_methods'].append((name, metadata))
        else:
            categories['likely_dead'].append((name, metadata))
    
    # Print results
    print(f"\n{'='*80}")
    print(f"DEAD CODE ANALYSIS RESULTS")
    print(f"{'='*80}\n")
    
    print(f"Total symbols analyzed: {len(all_defs)}")
    print(f"Symbols with callers: {len([d for d in all_defs if graph.get(d)])}")
    print(f"Unreferenced symbols: {len(all_defs) - len([d for d in all_defs if graph.get(d)])}\n")
    
    print(f"Entry Points (CLI commands, decorators): {len(categories['entry_points'])}")
    print(f"Public API (likely used externally): {len(categories['public_api'])}")
    print(f"Protocol Methods (special methods): {len(categories['protocol_methods'])}")
    print(f"LIKELY DEAD CODE: {len(categories['likely_dead'])}\n")
    
    if categories['likely_dead']:
        print(f"\n{'='*80}")
        print("LIKELY DEAD CODE (candidates for removal):")
        print(f"{'='*80}\n")
        
        # Group by module
        by_module = defaultdict(list)
        for name, metadata in categories['likely_dead']:
            module = '.'.join(name.split('.')[:-1])
            by_module[module].append((name, metadata))
        
        for module in sorted(by_module.keys()):
            print(f"\n{module}:")
            for name, metadata in sorted(by_module[module], key=lambda x: x[1]['line']):
                short_name = name.split('.')[-1]
                print(f"  Line {metadata['line']:4d}: {short_name} ({metadata['type']})")
    
    # Save detailed report
    report = {
        'summary': {
            'total_symbols': len(all_defs),
            'referenced': len([d for d in all_defs if graph.get(d)]),
            'unreferenced': len(all_defs) - len([d for d in all_defs if graph.get(d)]),
        },
        'categories': {
            k: [(name, meta) for name, meta in v]
            for k, v in categories.items()
        }
    }
    
    with open('dead_code_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n\nDetailed report saved to: dead_code_report.json")


if __name__ == '__main__':
    analyze_dead_code()
