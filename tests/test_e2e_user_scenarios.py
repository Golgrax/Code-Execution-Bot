import unittest
from unittest.mock import MagicMock
from main import resolve_message_content
from bot.parser import extract_code_and_language
from executor.manager import execute_code
from executor.models import ExecutionStatus
from analyzer.ast_analyzer import analyze_python_code
from analyzer.formatter import format_code


def simulate_message(content: str):
    """Simulate a Discord ctx message for resolve_message_content."""
    ctx = MagicMock()
    ctx.message.content = content
    ctx.message.reference = None
    extracted_raw = resolve_message_content(ctx, content)
    return extract_code_and_language(extracted_raw)


class TestE2EUserScenarios(unittest.IsolatedAsyncioTestCase):
    async def test_01_python_inline(self):
        msg = '!code python print(f"Python version test. Calculation: {sum(x**2 for x in range(10))}")'
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "python")
        res = await execute_code(lang, code)
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertIn("Python version test. Calculation: 285", res.stdout)

    async def test_02_python_indented_multiline(self):
        msg = """!code 
        def primes(n):
            return [x for x in range(2, n) if all(x % d != 0 for d in range(2, int(x**0.5) + 1))]

        print("Primes under 30:", primes(30))"""
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "python")
        res = await execute_code(lang, code)
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertIn("Primes under 30: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]", res.stdout)

    async def test_03_javascript_inline(self):
        msg = '!code js console.log("System time: 2026", "Mapping:", [10, 20, 30].map(x => x / 10));'
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "javascript")
        res = await execute_code(lang, code)
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertIn("Mapping: [ 1, 2, 3 ]", res.stdout)

    async def test_04_javascript_indented_multiline(self):
        msg = """!code 
        const data = { alpha: 1, beta: 2, gamma: 3 };
        const inverted = Object.fromEntries(Object.entries(data).map(([k, v]) => [v, k]));
        console.log(JSON.stringify(inverted));"""
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "javascript")
        res = await execute_code(lang, code)
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertIn('{"1":"alpha","2":"beta","3":"gamma"}', res.stdout)

    async def test_05_bash(self):
        msg = '!code bash echo "Kernel: $(uname -s)"; echo "Arithmetic: $(( 1024 * 8 )) bytes"'
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "bash")
        res = await execute_code(lang, code)
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertIn("Arithmetic: 8192 bytes", res.stdout)

    async def test_06_c(self):
        msg = """!code 
        #include <stdio.h>

        int main(void) {
            long long total = 0;
            for (int i = 1; i <= 100; i++) {
                total += i;
            }
            printf("Sum 1..100 = %lld\\n", total);
            return 0;
        }"""
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "c")
        res = await execute_code(lang, code)
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertIn("Sum 1..100 = 5050", res.stdout)

    async def test_07_cpp(self):
        msg = """!code 
        #include <iostream>
        #include <vector>
        #include <numeric>

        int main() {
            std::vector<int> nums = {1, 2, 3, 4, 5};
            int product = std::accumulate(nums.begin(), nums.end(), 1, std::multiplies<int>());
            std::cout << "Product: " << product << std::endl;
            return 0;
        }"""
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "cpp")
        res = await execute_code(lang, code)
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertIn("Product: 120", res.stdout)

    async def test_08_go(self):
        msg = """!code 
        package main

        import "fmt"

        func main() {
            languages := []string{"Go", "Python", "C", "JavaScript"}
            for idx, lang := range languages {
                fmt.Printf("[%d] %s\\n", idx+1, lang)
            }
        }"""
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "go")
        res = await execute_code(lang, code)
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertIn("[1] Go", res.stdout)
        self.assertIn("[4] JavaScript", res.stdout)

    async def test_09_php(self):
        msg = '!code php <?php echo "PHP runtime operational: " . (100 * 25) . "\\n";'
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "php")
        res = await execute_code(lang, code)
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertIn("PHP runtime operational: 2500", res.stdout)

    async def test_10_java(self):
        msg = """!code 
        public class Main {
            public static void main(String[] args) {
                int[] values = {5, 10, 15, 20};
                int sum = 0;
                for (int v : values) sum += v;
                System.out.println("Java execution verified. Total: " + sum);
            }
        }"""
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "java")
        res = await execute_code(lang, code)
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertIn("Java execution verified. Total: 50", res.stdout)

    def test_11_analyze_indented_multiline(self):
        msg = """!analyze 
        import math

        class DataProcessor:
            def init(self, data):
                self.data = data

            def process(self):
                for i in range(len(self.data)):
                    for j in range(len(self.data)):
                        if self.data[i] == self.data[j]:
                            pass

        def compute(x=[]):
            try:
                eval("1 + 1")
            except:
                pass"""
        lang, code = simulate_message(msg)
        self.assertEqual(lang, "python")
        rep = analyze_python_code(code)
        self.assertTrue(rep.is_valid_syntax)
        self.assertIn("O(N²)", rep.estimated_complexity)
        self.assertTrue(any("mutable default" in w for w in rep.warnings))
        self.assertTrue(any("Bare `except:`" in w for w in rep.warnings))
        self.assertTrue(any("eval()" in w for w in rep.warnings))

    def test_12_format_html(self):
        raw = "<section><header><h1>Document Title</h1></header><article><p>Paragraph 1</p></article></section>"
        ok, res = format_code("html", raw)
        self.assertTrue(ok)
        self.assertIn("<section>\n", res)
        self.assertIn("Document Title", res)

    def test_13_format_json(self):
        raw = '{"status":"success","exit_code":0,"metrics":{"execution_time_ms":24.5}}'
        ok, res = format_code("json", raw)
        self.assertTrue(ok)
        self.assertIn('  "status": "success"', res)


if __name__ == "__main__":
    unittest.main()
