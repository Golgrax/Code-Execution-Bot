import ast
import json
import re
from typing import Tuple
from bs4 import BeautifulSoup


def format_code(language: str, code: str) -> Tuple[bool, str]:
    """Format and beautify code based on language."""
    lang = language.lower()

    if lang in ("html", "xml", "svg"):
        try:
            soup = BeautifulSoup(code, "html.parser")
            formatted = soup.prettify()
            return True, formatted
        except Exception as e:
            return False, f"HTML Beautifier error: {str(e)}"

    elif lang in ("json",):
        try:
            obj = json.loads(code)
            formatted = json.dumps(obj, indent=2, ensure_ascii=False)
            return True, formatted
        except Exception as e:
            return False, f"JSON parse error: {str(e)}"

    elif lang in ("python", "py"):
        try:
            # AST parse and unparse (Python 3.9+)
            tree = ast.parse(code)
            formatted = ast.unparse(tree)
            return True, formatted
        except Exception as e:
            return False, f"Python formatting error: {str(e)}"

    elif lang in ("css",):
        try:
            # Clean up spacing around braces and semicolons
            clean = re.sub(r"\s+", " ", code.strip())
            clean = re.sub(r"\s*\{\s*", " {\n    ", clean)
            clean = re.sub(r";\s*", ";\n    ", clean)
            clean = re.sub(r"\s*\}\s*", "\n}\n\n", clean)
            clean = re.sub(r"    \n", "", clean)
            return True, clean.strip()
        except Exception as e:
            return False, f"CSS formatting error: {str(e)}"

    return False, f"No formatter available for language: {language}"
