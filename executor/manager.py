import os
from typing import Dict, List, Optional
from executor.models import ExecutionResult, ExecutionStatus
from executor.local_runner import run_locally, is_language_supported_locally, BINARIES
from executor.judge0_runner import run_judge0, LANGUAGE_IDS

DEFAULT_ENGINE = os.getenv("EXECUTION_ENGINE", "local").lower()

SUPPORTED_LOCAL_LANGS = sorted([
    lang for lang, path in BINARIES.items() if path is not None
])


async def execute_code(
    language: str,
    code: str,
    stdin: str = "",
    preferred_engine: Optional[str] = None,
    timeout: float = 6.0,
) -> ExecutionResult:
    """
    Execute code using local sandboxed execution (zero external APIs needed).
    Falls back to Judge0 only if explicitly configured with an API key.
    """
    engine = (preferred_engine or DEFAULT_ENGINE).lower()
    lang = language.lower()

    # 1. Judge0 if explicitly requested and key exists
    if engine == "judge0" and os.getenv("JUDGE0_API_KEY"):
        return await run_judge0(lang, code, stdin, timeout=timeout)

    # 2. Local sandbox execution (Zero API, Offline)
    if is_language_supported_locally(lang):
        local_timeout = 15.0 if lang in ("cpp", "c++", "go") else timeout
        return await run_locally(lang, code, stdin, timeout=local_timeout)

    # 3. Fallback to Judge0 if key is present
    if os.getenv("JUDGE0_API_KEY") and lang in LANGUAGE_IDS:
        return await run_judge0(lang, code, stdin, timeout=timeout)

    # 4. Informative unsupported response
    return ExecutionResult(
        language=lang,
        status=ExecutionStatus.UNSUPPORTED,
        stderr=(
            f"Language '{language}' is not installed locally on this server.\n"
            f"Installed local runtimes: {', '.join(SUPPORTED_LOCAL_LANGS)}"
        ),
        engine="Local Sandbox",
    )


def get_available_languages() -> Dict[str, List[str]]:
    """Return catalog of locally installed languages."""
    return {
        "local": SUPPORTED_LOCAL_LANGS,
        "formatters": ["html", "json", "css", "xml", "python"],
    }
