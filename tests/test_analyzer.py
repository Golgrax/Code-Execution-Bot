import unittest
from analyzer.ast_analyzer import analyze_python_code
from analyzer.multi_analyzer import analyze_code_generic, check_bracket_balance
from analyzer.formatter import format_code


class TestAnalyzer(unittest.TestCase):
    def test_python_syntax_error(self):
        bad_code = "def foo(\n    print('missing paren'"
        report = analyze_python_code(bad_code)
        self.assertFalse(report.is_valid_syntax)
        self.assertIsNotNone(report.syntax_error)

    def test_python_valid_analysis(self):
        code = """
import math

class Calculator:
    def add(self, a, b):
        return a + b

def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
"""
        report = analyze_python_code(code)
        self.assertTrue(report.is_valid_syntax)
        self.assertEqual(len(report.classes), 1)
        self.assertEqual(report.classes[0].name, "Calculator")
        self.assertEqual(len(report.functions), 2)
        # Check recursive detection
        fib_fn = next(f for f in report.functions if f.name == "fib")
        self.assertTrue(fib_fn.is_recursive)
        self.assertIn("math", report.imports)

    def test_python_anti_patterns(self):
        code = """
def bad(items=[]):
    try:
        eval("2 + 2")
    except:
        pass
"""
        report = analyze_python_code(code)
        self.assertTrue(any("mutable default" in w for w in report.warnings))
        self.assertTrue(any("Bare `except:`" in w for w in report.warnings))
        self.assertTrue(any("eval()" in w for w in report.warnings))

    def test_bracket_balance(self):
        balanced_code = "function f() { if (true) { return [1, 2]; } }"
        valid, err = check_bracket_balance(balanced_code)
        self.assertTrue(valid)
        self.assertIsNone(err)

        unbalanced_code = "function f() { if (true) { return [1, 2; } }"
        valid, err = check_bracket_balance(unbalanced_code)
        self.assertFalse(valid)
        self.assertIsNotNone(err)

    def test_formatter(self):
        html_code = "<div><p>Hello</p></div>"
        ok, res = format_code("html", html_code)
        self.assertTrue(ok)
        self.assertIn("<p>\n", res)

        json_code = '{"a":1,"b":2}'
        ok, res = format_code("json", json_code)
        self.assertTrue(ok)
        self.assertIn('  "a": 1', res)


if __name__ == "__main__":
    unittest.main()
