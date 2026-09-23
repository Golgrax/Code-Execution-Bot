import re
import textwrap
from typing import Optional, Tuple

LANG_ALIASES = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    "ts": "typescript",
    "c++": "cpp",
    "sh": "bash",
    "shell": "bash",
    "rb": "ruby",
    "rs": "rust",
    "golang": "go",
}

KNOWN_LANGUAGES = {
    "python", "javascript", "bash", "c", "cpp", "java", "ruby", "rust",
    "go", "php", "html", "css", "json", "swift", "kotlin", "lua"
}


def normalize_language(lang: Optional[str]) -> str:
    """Normalize language name or alias to canonical form."""
    if not lang:
        return "python"
    clean = lang.strip().lower()
    return LANG_ALIASES.get(clean, clean)


def clean_and_dedent(code: str) -> str:
    """Dedent code while preserving uniform indentation on multi-line blocks."""
    if not code:
        return ""
    # Strip leading/trailing blank lines only, preserving column indentation of code lines
    code_lines = code.splitlines()
    while code_lines and not code_lines[0].strip():
        code_lines.pop(0)
    while code_lines and not code_lines[-1].strip():
        code_lines.pop()

    preserved = "\n".join(code_lines)
    return textwrap.dedent(preserved.expandtabs(4)).strip()


def detect_language_from_code(code: str, fallback: str = "python") -> str:
    """Heuristically infer programming language if user did not specify one."""
    code_stripped = code.strip()

    # PHP
    if code_stripped.startswith("<?php") or "<?php" in code:
        return "php"

    # Go
    if re.search(r"\bpackage\s+main\b", code_stripped) or re.search(r"\bfunc\s+main\s*\(", code_stripped):
        return "go"

    # C / C++
    if "#include <iostream>" in code or "std::cout" in code or "std::vector" in code:
        return "cpp"
    if "#include <stdio.h>" in code or "#include <stdlib.h>" in code or re.search(r"\bint\s+main\s*\(\s*(void)?\s*\)", code):
        return "c"

    # Java
    if re.search(r"\bpublic\s+class\s+\w+", code_stripped) or "System.out.print" in code:
        return "java"

    # Python patterns (functions with colons, imports, decorators)
    if re.search(r"\bdef\s+\w+\s*\(.*?\)\s*:", code) or re.search(r"\bclass\s+\w+.*?:", code) or re.search(r"^\s*(from|import)\s+\w+", code, re.M):
        return "python"

    # Rust
    if re.search(r"\bfn\s+main\s*\(", code_stripped) or re.search(r"\blet\s+(mut\s+)?\w+\s*:\s*\w+", code_stripped):
        return "rust"

    # Ruby (def ... end without colon)
    if re.search(r"\bputs\s+['\"]", code_stripped) or (re.search(r"\bdef\s+\w+\b", code_stripped) and re.search(r"\bend\b", code_stripped) and ":" not in code):
        return "ruby"

    # JavaScript / Node
    if "console.log" in code or "document." in code or "window." in code or re.search(r"\bconst\s+\w+\s*=", code):
        return "javascript"

    # HTML
    if code_stripped.startswith("<!DOCTYPE") or code_stripped.startswith("<html") or (code_stripped.startswith("<") and code_stripped.endswith(">") and "</" in code):
        return "html"

    # JSON
    if (code_stripped.startswith("{") and code_stripped.endswith("}")) or (code_stripped.startswith("[") and code_stripped.endswith("]")):
        if ":" in code_stripped and '"' in code_stripped:
            return "json"

    # Bash / Shell
    if code_stripped.startswith("#!") or code_stripped.startswith("echo ") or "uname " in code:
        return "bash"

    return fallback


def extract_code_and_language(text: str, default_lang: str = "python") -> Tuple[str, str]:
    """
    Extract language and code from raw message content.
    Automatically handles indentation and infers language if omitted.
    """
    # 1. Check for markdown code blocks: ```lang\ncode``` or ```code```
    code_block_match = re.search(r"```([a-zA-Z0-9_+#.-]*)\s*\n([\s\S]+?)```", text)
    if code_block_match:
        lang_spec = code_block_match.group(1).strip()
        code_content = code_block_match.group(2)
        dedented = clean_and_dedent(code_content)
        if lang_spec:
            lang = normalize_language(lang_spec)
        else:
            lang = detect_language_from_code(dedented, default_lang)
        return lang, dedented

    # Single-line code block: ```code```
    inline_block_match = re.search(r"```([\s\S]+?)```", text)
    if inline_block_match:
        code_content = inline_block_match.group(1)
        dedented = clean_and_dedent(code_content)
        lang = detect_language_from_code(dedented, default_lang)
        return lang, dedented

    # Inline code with single backticks: `code`
    tick_match = re.search(r"`([^`]+)`", text)
    if tick_match:
        code_content = tick_match.group(1)
        dedented = clean_and_dedent(code_content)
        lang = detect_language_from_code(dedented, default_lang)
        return lang, dedented

    # Format: <language> <code> (e.g. !code python print(1) or !code js console.log(1))
    cleaned_start = text.lstrip()
    tokens = cleaned_start.split(None, 1)
    if len(tokens) == 2:
        candidate_lang = tokens[0].lower()
        if candidate_lang in LANG_ALIASES or candidate_lang in KNOWN_LANGUAGES:
            code_content = tokens[1]
            dedented = clean_and_dedent(code_content)
            return normalize_language(candidate_lang), dedented

    # Default: infer language from content and dedent
    dedented = clean_and_dedent(text)
    detected_lang = detect_language_from_code(dedented, default_lang)
    return detected_lang, dedented
