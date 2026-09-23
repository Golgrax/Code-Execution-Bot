import asyncio
import unittest
from executor.local_runner import run_locally
from executor.models import ExecutionStatus


class TestLocalRunner(unittest.IsolatedAsyncioTestCase):
    async def test_python_execution(self):
        res = await run_locally("python", "print('Python Execution Test Passed!')")
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertEqual(res.stdout.strip(), "Python Execution Test Passed!")
        self.assertEqual(res.exit_code, 0)
        self.assertGreater(res.execution_time_ms, 0)

    async def test_javascript_execution(self):
        res = await run_locally("javascript", "console.log('JS Test Passed!')")
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertEqual(res.stdout.strip(), "JS Test Passed!")
        self.assertEqual(res.exit_code, 0)

    async def test_bash_execution(self):
        res = await run_locally("bash", "echo 'Bash Test Passed!'")
        self.assertEqual(res.status, ExecutionStatus.SUCCESS)
        self.assertEqual(res.stdout.strip(), "Bash Test Passed!")

    async def test_python_timeout(self):
        # Test 1.5 second timeout on an infinite loop
        res = await run_locally("python", "import time\nwhile True:\n    time.sleep(0.1)", timeout=1.5)
        self.assertEqual(res.status, ExecutionStatus.TIMEOUT)
        self.assertTrue(res.timed_out)

    async def test_python_syntax_error(self):
        res = await run_locally("python", "print('unclosed")
        self.assertEqual(res.status, ExecutionStatus.ERROR)
        self.assertIn("SyntaxError", res.stderr)

    async def test_environment_isolation(self):
        # Ensure sensitive variables are not present in executed script environment
        res = await run_locally("python", "import os; print(os.environ.get('DISCORD_TOKEN', 'SAFE'))")
        self.assertEqual(res.stdout.strip(), "SAFE")


if __name__ == "__main__":
    unittest.main()
