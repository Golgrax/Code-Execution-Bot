import asyncio
import os
import re
import shutil
import signal
import sys
import tempfile
import time
from typing import Dict, Optional, Tuple

from executor.models import ExecutionResult, ExecutionStatus

# Resource limits (POSIX)
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

DEFAULT_TIMEOUT = 6.0  # seconds
MAX_OUTPUT_BYTES = 32 * 1024  # 32 KB

# Pre-resolve interpreter paths
def _find_bin(name: str) -> Optional[str]:
    node_nvm = os.path.expanduser("~/.config/nvm/versions/node")
    extra_paths = []
    if os.path.isdir(node_nvm):
        for ver in os.listdir(node_nvm):
            bin_path = os.path.join(node_nvm, ver, "bin")
            if os.path.isdir(bin_path):
                extra_paths.append(bin_path)

    full_path = os.pathsep.join(extra_paths + [os.environ.get("PATH", "")])
    return shutil.which(name, path=full_path)

BINARIES: Dict[str, Optional[str]] = {
    "python": sys.executable or _find_bin("python3"),
    "javascript": _find_bin("node"),
    "bash": _find_bin("bash"),
    "c": _find_bin("gcc"),
    "cpp": _find_bin("g++"),
    "go": _find_bin("go"),
    "php": _find_bin("php"),
    "java": _find_bin("java"),
}


def is_language_supported_locally(language: str) -> bool:
    lang = language.lower()
    if lang in ("python", "py"):
        return bool(BINARIES["python"])
    if lang in ("javascript", "js", "node"):
        return bool(BINARIES["javascript"])
    if lang in ("bash", "sh", "shell"):
        return bool(BINARIES["bash"])
    if lang in ("c",):
        return bool(BINARIES["c"])
    if lang in ("cpp", "c++"):
        return bool(BINARIES["cpp"])
    if lang in ("go", "golang"):
        return bool(BINARIES["go"])
    if lang in ("php",):
        return bool(BINARIES["php"])
    if lang in ("java",):
        # OpenJDK 11+ supports executing .java files directly without javac
        return bool(BINARIES["java"])
    return False


def get_clean_env(temp_dir: str) -> Dict[str, str]:
    """Provide a sanitized environment with persistent compiler caches."""
    paths = [
        "/usr/local/sbin",
        "/usr/local/bin",
        "/usr/sbin",
        "/usr/bin",
        "/sbin",
        "/bin",
    ]
    if BINARIES["javascript"]:
        node_dir = os.path.dirname(BINARIES["javascript"])
        if node_dir not in paths:
            paths.insert(0, node_dir)

    go_cache = "/tmp/code_bot_cache/go_build"
    go_path = "/tmp/code_bot_cache/go_path"
    os.makedirs(go_cache, exist_ok=True)
    os.makedirs(go_path, exist_ok=True)

    return {
        "PATH": os.pathsep.join(paths),
        "HOME": temp_dir,
        "TMPDIR": temp_dir,
        "TEMP": temp_dir,
        "TMP": temp_dir,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "GOCACHE": go_cache,
        "GOPATH": go_path,
    }


def _set_resource_limits():
    """Limit open files while relying on asyncio.wait_for and process-group kills for wall-clock timeouts."""
    if not HAS_RESOURCE:
        return
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    except Exception:
        pass


async def _run_command(
    cmd: list,
    cwd: str,
    env: dict,
    stdin_data: str = "",
    timeout: float = DEFAULT_TIMEOUT,
) -> Tuple[int, str, str, bool]:
    """Run command with timeout and process group kill on expiration."""
    timed_out = False
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
        preexec_fn=_set_resource_limits if os.name == "posix" else None,
        start_new_session=True if os.name == "posix" else False,
    )

    try:
        input_bytes = stdin_data.encode("utf-8") if stdin_data else None
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(input=input_bytes),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        timed_out = True
        if os.name == "posix":
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
        try:
            stdout_bytes, stderr_bytes = await proc.communicate()
        except Exception:
            stdout_bytes, stderr_bytes = b"", b"Execution timed out."

    stdout = stdout_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
    stderr = stderr_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")

    if len(stdout_bytes) > MAX_OUTPUT_BYTES:
        stdout += "\n... (Output truncated: exceeded 32KB)"
    if len(stderr_bytes) > MAX_OUTPUT_BYTES:
        stderr += "\n... (Error output truncated: exceeded 32KB)"

    exit_code = proc.returncode if not timed_out else -1
    return exit_code, stdout, stderr, timed_out


async def run_locally(
    language: str,
    code: str,
    stdin: str = "",
    timeout: float = DEFAULT_TIMEOUT,
) -> ExecutionResult:
    """Execute code in an isolated local sandbox directory with safety restrictions."""
    lang = language.lower()

    alias_map = {
        "py": "python",
        "python3": "python",
        "js": "javascript",
        "node": "javascript",
        "sh": "bash",
        "shell": "bash",
        "c++": "cpp",
        "golang": "go",
    }
    canonical_lang = alias_map.get(lang, lang)

    if not is_language_supported_locally(canonical_lang):
        return ExecutionResult(
            language=canonical_lang,
            status=ExecutionStatus.UNSUPPORTED,
            stderr=f"Language '{language}' is not installed locally on this server.",
            engine="Local Sandbox",
        )

    start_time = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="sandbox_") as temp_dir:
        env = get_clean_env(temp_dir)

        try:
            if canonical_lang == "python":
                source_path = os.path.join(temp_dir, "script.py")
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(code)
                cmd = [BINARIES["python"], "-u", "script.py"]
                exit_code, stdout, stderr, timed_out = await _run_command(cmd, temp_dir, env, stdin, timeout)

            elif canonical_lang == "javascript":
                source_path = os.path.join(temp_dir, "script.js")
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(code)
                cmd = [BINARIES["javascript"], "--max-old-space-size=256", "script.js"]
                exit_code, stdout, stderr, timed_out = await _run_command(cmd, temp_dir, env, stdin, timeout)

            elif canonical_lang == "bash":
                source_path = os.path.join(temp_dir, "script.sh")
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(code)
                cmd = [BINARIES["bash"], "script.sh"]
                exit_code, stdout, stderr, timed_out = await _run_command(cmd, temp_dir, env, stdin, timeout)

            elif canonical_lang == "c":
                source_path = os.path.join(temp_dir, "main.c")
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(code)
                compile_cmd = [BINARIES["c"], "-O2", "main.c", "-o", "prog", "-lm"]
                c_exit, c_out, c_err, c_timed_out = await _run_command(compile_cmd, temp_dir, env, "", timeout=8.0)
                if c_exit != 0:
                    duration = (time.monotonic() - start_time) * 1000
                    return ExecutionResult(
                        language="c",
                        status=ExecutionStatus.COMPILATION_ERROR,
                        stdout=c_out,
                        stderr=c_err or "Compilation failed.",
                        exit_code=c_exit,
                        execution_time_ms=round(duration, 2),
                        engine="GCC",
                    )
                cmd = ["./prog"]
                exit_code, stdout, stderr, timed_out = await _run_command(cmd, temp_dir, env, stdin, timeout)

            elif canonical_lang == "cpp":
                source_path = os.path.join(temp_dir, "main.cpp")
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(code)
                compile_cmd = [BINARIES["cpp"], "-O0", "main.cpp", "-o", "prog", "-lm"]
                c_exit, c_out, c_err, c_timed_out = await _run_command(compile_cmd, temp_dir, env, "", timeout=15.0)
                if c_exit != 0:
                    duration = (time.monotonic() - start_time) * 1000
                    return ExecutionResult(
                        language="cpp",
                        status=ExecutionStatus.COMPILATION_ERROR,
                        stdout=c_out,
                        stderr=c_err or "Compilation failed.",
                        exit_code=c_exit,
                        execution_time_ms=round(duration, 2),
                        engine="G++",
                    )
                cmd = ["./prog"]
                exit_code, stdout, stderr, timed_out = await _run_command(cmd, temp_dir, env, stdin, timeout)

            elif canonical_lang == "go":
                source_path = os.path.join(temp_dir, "main.go")
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(code)
                cmd = [BINARIES["go"], "run", "main.go"]
                # Go compilation with cache
                exit_code, stdout, stderr, timed_out = await _run_command(cmd, temp_dir, env, stdin, timeout=15.0)

            elif canonical_lang == "php":
                source_path = os.path.join(temp_dir, "script.php")
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(code)
                cmd = [BINARIES["php"], "script.php"]
                exit_code, stdout, stderr, timed_out = await _run_command(cmd, temp_dir, env, stdin, timeout)

            elif canonical_lang == "java":
                match = re.search(r"public\s+class\s+(\w+)", code)
                class_name = match.group(1) if match else "Main"
                source_path = os.path.join(temp_dir, f"{class_name}.java")
                with open(source_path, "w", encoding="utf-8") as f:
                    f.write(code)
                # OpenJDK 11+ single-source direct launch
                cmd = [BINARIES["java"], f"{class_name}.java"]
                exit_code, stdout, stderr, timed_out = await _run_command(cmd, temp_dir, env, stdin, timeout=12.0)

            else:
                return ExecutionResult(
                    language=canonical_lang,
                    status=ExecutionStatus.UNSUPPORTED,
                    stderr=f"No local runner handler for '{canonical_lang}'.",
                )

        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            return ExecutionResult(
                language=canonical_lang,
                status=ExecutionStatus.ERROR,
                stderr=f"Sandbox execution error: {str(e)}",
                execution_time_ms=round(duration, 2),
                engine="Local Sandbox",
            )

    duration = (time.monotonic() - start_time) * 1000

    if timed_out:
        status = ExecutionStatus.TIMEOUT
    elif exit_code == 0:
        status = ExecutionStatus.SUCCESS
    else:
        status = ExecutionStatus.ERROR

    return ExecutionResult(
        language=canonical_lang,
        status=status,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        execution_time_ms=round(duration, 2),
        engine=f"Local ({canonical_lang.capitalize()})",
        timed_out=timed_out,
    )
