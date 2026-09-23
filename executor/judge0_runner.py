import asyncio
import os
from typing import Optional
import aiohttp
from executor.models import ExecutionResult, ExecutionStatus

JUDGE0_BASE_URL = os.getenv("JUDGE0_BASE_URL", "https://judge0-ce.p.rapidapi.com")

LANGUAGE_IDS = {
    "python": 71,      # Python 3
    "py": 71,
    "javascript": 63,  # Node.js
    "js": 63,
    "java": 62,        # Java 11
    "c": 50,           # C (GCC 9.2.0)
    "cpp": 54,         # C++ (GCC 9.2.0)
    "c++": 54,
    "csharp": 51,      # C# (.NET Core 3.1.0)
    "c#": 51,
    "php": 68,         # PHP 7.4.1
    "ruby": 72,        # Ruby 2.7.0
    "rb": 72,
    "rust": 73,        # Rust 1.40.0
    "rs": 73,
    "go": 60,          # Go 1.13.5
    "kotlin": 78,      # Kotlin 1.3.70
    "swift": 83,       # Swift 5.2.3
    "bash": 46,        # Bash 5.0.0
    "sh": 46,
}


async def run_judge0(
    language: str,
    code: str,
    stdin: str = "",
    api_key: Optional[str] = None,
    timeout: float = 10.0,
) -> ExecutionResult:
    """Execute code using Judge0 API asynchronously via aiohttp."""
    api_key = api_key or os.getenv("JUDGE0_API_KEY")
    if not api_key:
        return ExecutionResult(
            language=language,
            status=ExecutionStatus.ERROR,
            stderr="Judge0 API key is not configured.",
            engine="Judge0",
        )

    lang_id = LANGUAGE_IDS.get(language.lower())
    if not lang_id:
        return ExecutionResult(
            language=language,
            status=ExecutionStatus.UNSUPPORTED,
            stderr=f"Language '{language}' not supported by Judge0.",
            engine="Judge0",
        )

    headers = {
        "Content-Type": "application/json",
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
    }

    data = {
        "source_code": code,
        "language_id": lang_id,
        "stdin": stdin,
        "cpu_time_limit": 5,
        "memory_limit": 128000,
    }

    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        try:
            async with session.post(f"{JUDGE0_BASE_URL}/submissions", headers=headers, json=data) as resp:
                if resp.status != 201:
                    text = await resp.text()
                    return ExecutionResult(
                        language=language,
                        status=ExecutionStatus.ERROR,
                        stderr=f"Judge0 submission error ({resp.status}): {text[:200]}",
                        engine="Judge0",
                    )
                sub_res = await resp.json()

            token = sub_res.get("token")
            if not token:
                return ExecutionResult(
                    language=language,
                    status=ExecutionStatus.ERROR,
                    stderr="Failed to get submission token from Judge0",
                    engine="Judge0",
                )

            # Poll for results (non-blocking)
            for _ in range(10):
                await asyncio.sleep(1)
                async with session.get(f"{JUDGE0_BASE_URL}/submissions/{token}", headers=headers) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        return ExecutionResult(
                            language=language,
                            status=ExecutionStatus.ERROR,
                            stderr=f"Judge0 polling error ({resp.status}): {text[:200]}",
                            engine="Judge0",
                        )
                    result = await resp.json()

                status_id = result.get("status", {}).get("id", 1)
                if status_id not in (1, 2):  # Finished processing
                    break

            status_id = result.get("status", {}).get("id", 0)
            stdout = result.get("stdout") or ""
            stderr = result.get("stderr") or ""
            compile_output = result.get("compile_output") or ""
            exec_time = float(result.get("time") or 0.0) * 1000

            if status_id == 3:  # Accepted
                status = ExecutionStatus.SUCCESS
            elif status_id == 5:  # Time Limit Exceeded
                status = ExecutionStatus.TIMEOUT
            elif status_id == 6:  # Compilation Error
                status = ExecutionStatus.COMPILATION_ERROR
                stderr = compile_output
            else:
                status = ExecutionStatus.ERROR

            return ExecutionResult(
                language=language,
                status=status,
                stdout=stdout,
                stderr=stderr,
                execution_time_ms=round(exec_time, 2),
                engine="Judge0 (Cloud)",
            )

        except asyncio.TimeoutError:
            return ExecutionResult(
                language=language,
                status=ExecutionStatus.TIMEOUT,
                stderr="Judge0 API execution timed out.",
                engine="Judge0",
                timed_out=True,
            )
        except Exception as e:
            return ExecutionResult(
                language=language,
                status=ExecutionStatus.ERROR,
                stderr=f"Judge0 request failed: {str(e)}",
                engine="Judge0",
            )
