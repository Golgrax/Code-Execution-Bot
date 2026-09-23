import unittest
from bot.parser import extract_code_and_language, normalize_language


class TestParser(unittest.TestCase):
    def test_normalize_language(self):
        self.assertEqual(normalize_language("py"), "python")
        self.assertEqual(normalize_language("js"), "javascript")
        self.assertEqual(normalize_language("c++"), "cpp")
        self.assertEqual(normalize_language("sh"), "bash")
        self.assertEqual(normalize_language("Python"), "python")

    def test_code_block_with_language(self):
        content = "```python\nprint('hello')\n```"
        lang, code = extract_code_and_language(content)
        self.assertEqual(lang, "python")
        self.assertEqual(code, "print('hello')")

    def test_code_block_without_language(self):
        content = "```\nconsole.log(123)\n```"
        lang, code = extract_code_and_language(content, default_lang="javascript")
        self.assertEqual(lang, "javascript")
        self.assertEqual(code, "console.log(123)")

    def test_inline_language_and_code(self):
        content = "python print('hello world')"
        lang, code = extract_code_and_language(content)
        self.assertEqual(lang, "python")
        self.assertEqual(code, "print('hello world')")

    def test_inline_with_backticks(self):
        content = "`print(42)`"
        lang, code = extract_code_and_language(content)
        self.assertEqual(lang, "python")
        self.assertEqual(code, "print(42)")

    def test_plain_code_default_fallback(self):
        content = "x = [1, 2, 3]\nprint(sum(x))"
        lang, code = extract_code_and_language(content)
        self.assertEqual(lang, "python")
        self.assertEqual(code, content)


if __name__ == "__main__":
    unittest.main()
