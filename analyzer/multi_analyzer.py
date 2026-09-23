import re
from typing import List, Dict, Tuple, Optional
from analyzer.ast_analyzer import CodeAnalysisReport, analyze_python_code


def check_bracket_balance(code: str) -> Tuple[bool, Optional[str]]:
    """Check if brackets (), {}, [] in code are balanced, returning line & col of error if not."""
    stack = []
    pairs = {")": "(", "}": "{", "]": "["}
    openers = set(pairs.values())

    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False

    lines = code.split("\n")
    for row_idx, line in enumerate(lines, start=1):
        in_line_comment = False
        col_idx = 0
        while col_idx < len(line):
            ch = line[col_idx]
            nxt = line[col_idx + 1] if col_idx + 1 < len(line) else ""

            # Comments
            if not in_single_quote and not in_double_quote:
                if not in_block_comment and ch == "/" and nxt == "/":
                    in_line_comment = True
                    break
                elif not in_block_comment and ch == "#":
                    in_line_comment = True
                    break
                elif not in_block_comment and ch == "/" and nxt == "*":
                    in_block_comment = True
                    col_idx += 2
                    continue
                elif in_block_comment and ch == "*" and nxt == "/":
                    in_block_comment = False
                    col_idx += 2
                    continue

            if in_line_comment or in_block_comment:
                col_idx += 1
                continue

            # Quotes
            if ch == "'" and not in_double_quote and (col_idx == 0 or line[col_idx - 1] != "\\"):
                in_single_quote = not in_single_quote
            elif ch == '"' and not in_single_quote and (col_idx == 0 or line[col_idx - 1] != "\\"):
                in_double_quote = not in_double_quote

            if not in_single_quote and not in_double_quote:
                if ch in openers:
                    stack.append((ch, row_idx, col_idx + 1))
                elif ch in pairs:
                    expected = pairs[ch]
                    if not stack:
                        return False, f"Unmatched closing '{ch}' at Line {row_idx}, Col {col_idx + 1}"
                    top_char, top_row, top_col = stack.pop()
                    if top_char != expected:
                        return False, f"Mismatched bracket: opened '{top_char}' at Line {top_row}, Col {top_col} but found '{ch}' at Line {row_idx}, Col {col_idx + 1}"

            col_idx += 1

    if stack:
        unclosed, u_row, u_col = stack.pop()
        return False, f"Unclosed bracket '{unclosed}' opened at Line {u_row}, Col {u_col}"

    return True, None


def analyze_code_generic(language: str, code: str) -> CodeAnalysisReport:
    """Analyze code for multiple languages (JS, C, C++, Java, Go, etc.) without LLMs."""
    lang = language.lower()
    if lang in ("python", "py"):
        return analyze_python_code(code)

    lines = code.splitlines()
    loc_total = len(lines)
    loc_blank = sum(1 for l in lines if not l.strip())
    loc_comments = sum(1 for l in lines if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"))
    loc_code = max(0, loc_total - loc_blank - loc_comments)

    # Bracket check
    balanced, bracket_err = check_bracket_balance(code)
    warnings = []
    if not balanced and bracket_err:
        warnings.append(bracket_err)

    # Heuristic pattern matching
    functions_found = []
    classes_found = []
    imports_found = []

    # Detect functions in JS, C/C++, Java, Go
    fn_patterns = [
        r"(?:function\s+([a-zA-Z0-9_$]+)|(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)",  # JS
        r"(?:(?:public|private|protected|static|async)\s+)+[\w<>\[\]]+\s+([a-zA-Z0-9_$]+)\s*\(",  # Java/C#
        r"(?:void|int|char|float|double|bool|auto)\s+([a-zA-Z0-9_$]+)\s*\(",  # C/C++
        r"func\s+(?:\([^)]*\)\s*)?([a-zA-Z0-9_]+)\s*\(",  # Go
    ]
    for pat in fn_patterns:
        matches = re.findall(pat, code)
        for m in matches:
            name = m if isinstance(m, str) else (m[0] or m[1])
            if name and name not in ("if", "for", "while", "switch", "catch"):
                functions_found.append(name)

    # Detect classes
    cls_matches = re.findall(r"(?:class|struct|interface)\s+([a-zA-Z0-9_$]+)", code)
    classes_found.extend(cls_matches)

    # Detect imports / includes
    import_matches = re.findall(r"(?:#include\s*[<\"].*?[>\"]|import\s+.*?from\s+['\"].*?['\"]|require\(['\"].*?['\"]\)|import\s+['\"].*?['\"])", code)
    imports_found.extend([i.strip() for i in import_matches[:5]])

    # Loops & Branches
    loop_count = len(re.findall(r"\b(for|while|foreach)\b", code))
    if_count = len(re.findall(r"\b(if|else if|switch|case)\b", code))
    complexity = 1 + loop_count + if_count

    if loop_count == 0:
        est_complexity = "O(1) (Sequential)"
    elif loop_count == 1:
        est_complexity = "O(N) (Linear)"
    elif loop_count >= 2:
        est_complexity = "O(N²) or higher (Nested/Multiple loops)"
    else:
        est_complexity = "O(1)"

    parts = [f"Language: `{language.capitalize()}` ({loc_code} code lines)."]
    if classes_found:
        parts.append(f"Identified structures/classes: {', '.join(set(classes_found[:4]))}.")
    if functions_found:
        parts.append(f"Detected {len(functions_found)} function(s): {', '.join(set(functions_found[:5]))}.")
    if imports_found:
        parts.append(f"Dependencies: {len(imports_found)} included.")
    parts.append(f"Branch/Loop count: {complexity - 1} (Est. complexity: {est_complexity}).")
    if balanced:
        parts.append("Syntax brackets balanced.")
    else:
        parts.append("Bracket imbalance detected.")

    summary = " ".join(parts)

    return CodeAnalysisReport(
        language=language,
        is_valid_syntax=balanced,
        syntax_error=bracket_err,
        loc_total=loc_total,
        loc_code=loc_code,
        loc_comments=loc_comments,
        cyclomatic_complexity=complexity,
        max_loop_depth=min(loop_count, 3),
        estimated_complexity=est_complexity,
        warnings=warnings,
        summary_text=summary,
    )
