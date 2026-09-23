from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class ExecutionResult:
    language: str
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    execution_time_ms: float = 0.0
    engine: str = "Local Sandbox"
    timed_out: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS

    @property
    def combined_output(self) -> str:
        out = []
        if self.stdout:
            out.append(self.stdout)
        if self.stderr:
            out.append(f"[stderr]\n{self.stderr}")
        return "\n".join(out).strip() or "(No output)"
