import ast
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set


@dataclass
class FunctionInfo:
    name: str
    args: List[str]
    has_docstring: bool
    is_async: bool
    is_recursive: bool
    line_number: int


@dataclass
class ClassInfo:
    name: str
    bases: List[str]
    methods: List[str]
    line_number: int


@dataclass
class CodeAnalysisReport:
    language: str
    is_valid_syntax: bool
    syntax_error: Optional[str] = None
    loc_total: int = 0
    loc_code: int = 0
    loc_comments: int = 0
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    cyclomatic_complexity: int = 1
    max_loop_depth: int = 0
    estimated_complexity: str = "O(1)"
    warnings: List[str] = field(default_factory=list)
    summary_text: str = ""


class ASTComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 1
        self.current_loop_depth = 0
        self.max_loop_depth = 0
        self.current_function: Optional[str] = None
        self.recursive_functions: Set[str] = set()

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.current_loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_AsyncFor(self, node):
        self.complexity += 1
        self.current_loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_While(self, node):
        self.complexity += 1
        self.current_loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        prev = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev

    def visit_AsyncFunctionDef(self, node):
        prev = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev

    def visit_Call(self, node):
        if self.current_function and isinstance(node.func, ast.Name):
            if node.func.id == self.current_function:
                self.recursive_functions.add(self.current_function)
        self.generic_visit(node)


def analyze_python_code(code: str) -> CodeAnalysisReport:
    """Analyze Python code using AST without requiring any external LLM or API."""
    lines = code.splitlines()
    loc_total = len(lines)
    loc_comments = sum(1 for line in lines if line.strip().startswith("#"))
    loc_blank = sum(1 for line in lines if not line.strip())
    loc_code = max(0, loc_total - loc_comments - loc_blank)

    # 1. Syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        caret = " " * (e.offset - 1) + "^" if e.offset else ""
        error_msg = f"Line {e.lineno}, Col {e.offset}: {e.msg}\n  {e.text.rstrip() if e.text else ''}\n  {caret}"
        return CodeAnalysisReport(
            language="python",
            is_valid_syntax=False,
            syntax_error=error_msg.strip(),
            loc_total=loc_total,
            loc_code=loc_code,
            loc_comments=loc_comments,
            summary_text=f"Python Syntax Error at line {e.lineno}: {e.msg}",
        )

    # 2. Complexity & recursion
    visitor = ASTComplexityVisitor()
    visitor.visit(tree)

    # Big-O estimation heuristic
    if visitor.recursive_functions:
        if visitor.max_loop_depth >= 1:
            est_complexity = "O(N * 2^N) or higher (Recursive with loops)"
        else:
            est_complexity = "O(2^N) or O(N) (Recursive)"
    elif visitor.max_loop_depth == 0:
        est_complexity = "O(1) (Constant / Sequential)"
    elif visitor.max_loop_depth == 1:
        est_complexity = "O(N) (Linear)"
    elif visitor.max_loop_depth == 2:
        est_complexity = "O(N²) (Quadratic)"
    elif visitor.max_loop_depth == 3:
        est_complexity = "O(N³) (Cubic)"
    else:
        est_complexity = f"O(N^{visitor.max_loop_depth}) (Polynomial)"

    # 3. Extract functions, classes, imports, and detect warnings
    functions: List[FunctionInfo] = []
    classes: List[ClassInfo] = []
    imports: List[str] = []
    warnings: List[str] = []

    BUILTIN_SHADOWS = {"list", "dict", "str", "int", "set", "tuple", "id", "type", "open", "file", "print"}

    for node in ast.walk(tree):
        # Imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = [alias.name for alias in node.names]
            imports.append(f"{mod}: {', '.join(names)}")

        # Functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_async = isinstance(node, ast.AsyncFunctionDef)
            args = [arg.arg for arg in node.args.args]
            has_doc = ast.get_docstring(node) is not None
            is_rec = node.name in visitor.recursive_functions
            functions.append(FunctionInfo(
                name=node.name,
                args=args,
                has_docstring=has_doc,
                is_async=is_async,
                is_recursive=is_rec,
                line_number=node.lineno,
            ))

            # Check mutable default argument anti-pattern: def f(x=[])
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    warnings.append(f"Function `{node.name}` (line {node.lineno}) uses mutable default argument.")

        # Classes
        elif isinstance(node, ast.ClassDef):
            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
            methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append(ClassInfo(
                name=node.name,
                bases=bases,
                methods=methods,
                line_number=node.lineno,
            ))

        # Bare except warning: except:
        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                warnings.append(f"Line {node.lineno}: Bare `except:` caught (catch specific exceptions like `Exception`).")

        # Dangerous calls
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec"):
                warnings.append(f"Line {node.lineno}: Dynamic code evaluation `{node.func.id}()` detected.")

        # Shadowing builtins in assignment
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in BUILTIN_SHADOWS:
                    warnings.append(f"Line {node.lineno}: Variable `{target.id}` shadows Python built-in.")

    # 4. Generate deterministic summary explanation ("Understanding Code without LLMs")
    parts = []
    if classes:
        cls_desc = [f"`{c.name}` ({len(c.methods)} methods)" for c in classes]
        parts.append(f"Defines {len(classes)} class(es): {', '.join(cls_desc)}.")
    if functions:
        fn_desc = [f"`{f.name}({', '.join(f.args)})`" + (" [recursive]" if f.is_recursive else "") for f in functions]
        parts.append(f"Declares {len(functions)} function(s): {', '.join(fn_desc)}.")
    if imports:
        parts.append(f"Imports dependencies: {', '.join(imports)}.")

    if not classes and not functions:
        parts.append("Script consists of top-level procedural statements.")

    parts.append(f"Flow complexity is {visitor.complexity} with max loop nesting level {visitor.max_loop_depth} ({est_complexity}).")

    if not warnings:
        parts.append("Clean code: No static anti-patterns detected.")
    else:
        parts.append(f"Identified {len(warnings)} potential issue(s).")

    summary_text = " ".join(parts)

    return CodeAnalysisReport(
        language="python",
        is_valid_syntax=True,
        loc_total=loc_total,
        loc_code=loc_code,
        loc_comments=loc_comments,
        functions=functions,
        classes=classes,
        imports=imports,
        cyclomatic_complexity=visitor.complexity,
        max_loop_depth=visitor.max_loop_depth,
        estimated_complexity=est_complexity,
        warnings=warnings,
        summary_text=summary_text,
    )
