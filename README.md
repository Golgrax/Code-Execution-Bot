# Code Execution & Analysis Bot

A sandboxed Discord bot designed to execute source code, perform static analysis and linting without external language models, and format source code and markup. Operates fully offline with zero external API requirements.

Supports Discord Slash Commands (`/code`, `/analyze`, `/format`, `/langs`, `/help`) and Message Prefix Commands (`!code`, `!analyze`, `!format`, `!langs`, `!help`).

---

## Features

- **Local Sandbox Execution (Zero External APIs)**:
  - Operates directly on the host using native compilers and interpreters.
  - Process isolation: Execution runs inside temporary sandbox directories with enforced execution timeouts and automated process-group cleanup (`SIGKILL`).
  - Environment sanitization: Strips environment variables to ensure secrets, system tokens, and user credentials cannot be accessed by executed code.
  - Supported local runtimes:
    - Python 3 (`python3`)
    - JavaScript (`node`)
    - Bash (`bash`)
    - C (`gcc`)
    - C++ (`g++`)
    - Go (`go` with persistent build cache)
    - PHP (`php`)
    - Java (OpenJDK 11+ single-source direct launch)
- **Static Code Analysis & Understanding (No LLMs Required)**:
  - Abstract Syntax Tree (AST) inspection extracting defined classes, methods, functions, and imported dependencies.
  - Algorithmic time complexity estimation based on loop nesting levels and recursion detection ($O(1)$, $O(N)$, $O(N^2)$, $O(2^N)$).
  - Offline static bug and anti-pattern warnings: detects bare `except:` clauses, mutable default function arguments, dynamic `eval()` execution, and shadowed built-in identifiers.
  - Syntax error diagnostics with exact line, column, and caret indicators.
  - Bracket and brace balance validation (`()`, `{}`, `[]`) across multi-line source files.
- **Code Formatting & Beautification**:
  - Structured formatting for HTML, CSS, JSON, and Python.
- **User Interface**:
  - Embed-based reporting with execution duration (ms), exit codes, and runtime engine metadata.
  - Automatic `.txt` file attachment when standard output or standard error exceeds Discord message constraints.
  - Interactive UI buttons (`Analyze Code`, `Dismiss`).

---

## Quick Start

### 1. Prerequisites and Installation

Clone the repository and set up a Python virtual environment:

```bash
git clone https://github.com/Golgrax/Code-Execution-Bot.git
cd Code-Execution-Bot

python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```env
DISCORD_TOKEN=your_discord_bot_token_here

# Execution mode: "local" (default) or "judge0"
EXECUTION_ENGINE=local

# Optional: Judge0 RapidAPI key (only required if using cloud Judge0)
JUDGE0_API_KEY=
```

> [!WARNING]
> Do not commit `.env` or Discord tokens to version control. The repository includes `.gitignore` to prevent secret exposure.

### 3. Running the Service

Start the bot using the virtual environment interpreter:

```bash
./venv/bin/python3 main.py
```

---

## Commands Reference

### Code Execution (`!code` or `/code`)

Executes source code in an isolated local sandbox.

- Inline syntax:
  ```text
  !code python print(sum(x**2 for x in range(10)))
  ```
- Multi-line code block syntax:
  ````markdown
  !code ```javascript
  const values = [10, 20, 30];
  console.log(values.map(v => v * 2));
  ```
  ````
- Raw multi-line snippet:
  ```text
  !code
  def primes(n):
      return [x for x in range(2, n) if all(x % d != 0 for d in range(2, int(x**0.5) + 1))]

  print("Primes:", primes(30))
  ```

### Static Code Analysis (`!analyze` or `/analyze`)

Performs offline structural inspection, complexity estimation, and lint analysis.

```text
!analyze
import math

class DataProcessor:
    def __init__(self, data):
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
        pass
```

### Code Formatting (`!format` or `/format`)

Formats and indents supported markup and code:

```text
!format html <section><header><h1>Title</h1></header><article><p>Content</p></article></section>
```

```text
!format json {"status":"success","exit_code":0,"metrics":{"execution_time_ms":24.5}}
```

### General Utilities

- `!langs` / `/langs` — Catalog of installed runtimes and available formatters.
- `!ping` / `/ping` — Reports Discord gateway latency.
- `!help` / `/help` — Command usage manual.

---

## Automated Testing

The project includes unit and end-to-end regression tests verifying parser robustness, sandbox execution, AST analysis, and formatting.

Run the test suite:

```bash
./venv/bin/python3 -m unittest discover tests
```

---

## Architecture

```
Code-Execution-Bot/
├── analyzer/              # Static code analysis and formatters (no LLMs)
│   ├── ast_analyzer.py    # Python AST parsing, complexity heuristics, linting
│   ├── multi_analyzer.py  # Generic language analysis & bracket balancing
│   └── formatter.py       # HTML, JSON, CSS, Python formatters
├── bot/                   # Discord interface and command parsing
│   ├── parser.py          # Multi-line indentation preservation & detection
│   └── ui.py              # Embed formatters and interactive buttons
├── executor/              # Sandboxed multi-runtime executor
│   ├── local_runner.py    # Zero-API local sandbox with timeout & env isolation
│   ├── judge0_runner.py   # Asynchronous Judge0 runner (optional)
│   ├── manager.py         # Execution engine coordinator
│   └── models.py          # Data models and status enumerations
├── tests/                 # Unit and end-to-end integration tests
│   ├── test_parser.py
│   ├── test_analyzer.py
│   ├── test_local_runner.py
│   └── test_e2e_user_scenarios.py
├── keep_alive.py          # Daemon health-check HTTP server
├── main.py                # Service entrypoint and slash command tree sync
└── requirements.txt       # Dependencies
```

---

## License

MIT License
