# Running the Test Suite

This repository uses **pytest** together with the **pytest‑cov** plugin to run the unit tests and generate a coverage report.

---

## Prerequisites

1. **Python 3.8+** must be installed and available on your `PATH`.
2. It is recommended to work inside a virtual environment to keep dependencies isolated:
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On Unix/macOS
   source .venv/bin/activate
   ```
3. Install the required packages (including the test dependencies):
   ```bash
   pip install -r requirements.txt
   pip install -e .   # install the package in editable mode
   pip install pytest pytest-cov
   ```

---

## Basic test run

Run all tests with the default configuration:
```bash
pytest
```
This will discover all files matching `test_*.py` inside the `tests/` directory and execute them.

---

## Running with coverage

To see how much of the source code is exercised, use the coverage flags that are already defined in `pyproject.toml`:
```bash
pytest --cov=src/hcode --cov-report=term-missing
```
The output will show a table with the percentage of statements, branches and functions covered, and a list of uncovered lines.

---

## Common options

| Option | Description |
|--------|-------------|
| `-q`   | Quiet mode – only show failures and the final summary. |
| `-v`   | Verbose – show each test name as it runs. |
| `--maxfail=N` | Stop after the first *N* failures. |
| `-k "expr"` | Run only tests whose name matches the given expression. |
| `--tb=short` | Shorter traceback output for failures. |
| `--capture=no` | Show `print` statements immediately (useful for debugging). |

You can combine them, e.g.:
```bash
pytest -q -k "ContextManager" --maxfail=1
```

---

## Environment variables used by the tests

| Variable | Purpose |
|----------|---------|
| `HCODE_PROVIDER` | Selects which LLM provider the library should use (e.g., `openai`, `anthropic`). The tests mock the provider, but the variable must be set for the code to initialise correctly. |
| `HCODE_LOG_LEVEL` | Controls logging verbosity; the test suite forces it to `ERROR` to keep output clean. |
| `HCODE_CONTEXT_PATH` | Path to the JSON file used by `ContextManager`. The tests override this with a temporary file via a fixture. |

---

## Cleaning up

All temporary files created by the tests are placed in the `tmp_path` fixture provided by pytest, which automatically removes them after each test. No manual cleanup is required.

---

## Running the full CI‑style command

If you want to emulate the CI pipeline (run tests and enforce 100 % coverage), execute:
```bash
pytest --cov=src/hcode --cov-report=term-missing
```
The CI configuration fails the build if any coverage metric falls below 100 %.

---

## Troubleshooting

* **ImportError: No module named 'hcode'** – Ensure you have installed the package in editable mode (`pip install -e .`).
* **Missing `pytest` or `pytest‑cov`** – Install them with `pip install pytest pytest-cov`.
* **Permission errors on Windows** – Run the command prompt or PowerShell as Administrator, or ensure the virtual environment directory is writable.

---

Happy testing! 🚀
