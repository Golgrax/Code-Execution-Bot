import asyncio
import aiohttp
from typing import Optional
from executor.models import ExecutionResult, ExecutionStatus

PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"

# Language alias mapping for Piston
PISTON_LANG_MAP = {
    "python": "python",
    "py": "python",
    "javascript": "javascript",
    "js": "javascript",
    "node": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "c": "c",
    "cpp": "c++",
    "c++": "c++",
    "csharp": "csharp",
    "c#": "csharp",
    "java": "java",
    "ruby": "ruby",
    "rb": "ruby",
    "rust": "rust",
    "rs": "rust",
    "go": "go",
    "golang": "go",
    "php": "php",
    "bash": "bash",
    "sh": "bash",
    "swift": "swift",
    "kotlin": "kotlin",
    "lua": "lua",
}


async def run_piston(
    language: str,
    code: str,
    stdin: str = "",
    timeout: float = 10.0,
) -> ExecutionResult:
    """Execute code via public Piston API (requires no API key)."""
    lang = language.lower()
    piston_lang = PISTON_LANG_MAP.get(lang, lang)

    payload = {
        "language": piston_lang,
        "version": "*",
        "files": [{"content": code}],
        "stdin": stdin,
    }

    try:
        timeout_client = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_client) as session:
            async with session.post(PISTON_API_URL, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    return ExecutionResult(
                        language=lang,
                        status=ExecutionStatus.ERROR,
                        stderr=f"Piston API returned HTTP {resp.status}: {text[:200]}",
                        engine="Piston (Cloud)",
                    )
                data = await resp.json()

        run_info = data.get("run", {})
        compile_info = data.get("compile", {})

        # If compilation error
        if compile_info and compile_info.get("code", 0) != 0:
            return ExecutionResult(
                language=lang,
                status=ExecutionStatus.COMPILATION_ERROR,
                stdout=compile_info.get("stdout", ""),
                stderr=compile_info.get("stderr", "") or "Compilation failed",
                exit_code=compile_info.get("code"),
                engine=f"Piston ({data.get('language', lang)} {data.get('version', '')})",
            )

        exit_code = run_info.get("code", 0)
        stdout = run_info.get("stdout", "")
        stderr = run_info.get("stderr", "")
        status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.ERROR

        return ExecutionResult(
            language=lang,
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            engine=f"Piston ({data.get('language', lang)} {data.get('version', '')})",
        )

    except asyncio.TimeoutError:
        return ExecutionResult(
            language=lang,
            status=ExecutionStatus.TIMEOUT,
            stderr="Piston execution timed out.",
            engine="Piston (Cloud)",
            timed_out=True,
        )
    except Exception as e:
        return ExecutionResult(
            language=lang,
            status=ExecutionStatus.ERROR,
            stderr=f"Piston connection error: {str(e)}",
            engine="Piston (Cloud)",
        )
