# PyTestRunner: Isolated Python Script Runner

PyTestRunner is a command-line tool designed to execute Python scripts in a completely isolated, clean, and repeatable environment. It leverages Docker to ensure that a script and its dependencies are run in a pristine container every time, eliminating the "it works on my machine" problem.

This tool is ideal for automated testing, data processing pipelines, and any scenario where consistent, verifiable script execution is critical.

## Features

-   **Total Isolation:** Each script run occurs in a fresh Docker container based on `python:3.10-slim`.
-   **Dependency Management:** Automatically creates a virtual environment and installs dependencies from a `requirements.txt` file.
-   **File I/O:** Supports passing in arbitrary input files and automatically captures all files created during execution.
-   **Argument Passing:** Allows for passing command-line arguments directly to the script being evaluated.
-   **Robust Error Reporting:** Provides detailed, machine-readable JSON output for easy integration into automated workflows.

## Setup

1.  **Prerequisites:**
    *   Python 3.8+ installed on your host machine.
    *   Docker Desktop installed and the Docker daemon running.

2.  **Create a Virtual Environment:** It is highly recommended to run this tool within its own Python virtual environment to avoid conflicts with system-wide packages.
    ```powershell
    # Create the environment
    python -m venv .venv

    # Activate it (on Windows PowerShell)
    .venv\Scripts\Activate.ps1
    ```

3.  **Install Dependencies:** The runner itself has one dependency, the `docker` library for Python.
    ```powershell
    pip install -r requirements.txt
    ```

## Usage

The script is invoked via `python py_test_runner.py` with the following arguments:


Usage: 
```
py_test_runner.py [-h] --script SCRIPT --reqs REQS [--inputs INPUTS [INPUTS ...]] [--script-args SCRIPT_ARGS] [--json-output]


A simple Python script runner using Docker.

options:
  -h, --help            show this help message and exit
  --script SCRIPT       Path to the Python script to execute. (Required)
  --reqs REQS           Path to the requirements.txt file. (Required)
  --inputs INPUTS [INPUTS ...]
                        Optional list of input files to be copied into the context.
  --script-args SCRIPT_ARGS
                        A string of arguments to pass to the script being executed.
  --json-output         Enable JSON output for machine readability.
```

### Arguments Explained

*   `--script`: **(Required)** The path to the Python script you want to run.
*   `--reqs`: **(Required)** The path to the `requirements.txt` file for the script. This can be an empty file if there are no dependencies. **Do not pass data files to this argument.**
*   `--inputs`: **(Optional)** A space-separated list of paths to any data files, configuration files, or other assets that the script needs to access.
*   `--script-args`: **(Optional)** A single string containing all the command-line arguments you want to pass to your script. Enclose the entire string in quotes.
*   `--json-output`: **(Optional)** Switches the output mode from human-readable logs to a single, machine-readable JSON object printed to standard output.

### Examples

**1. Basic Run (Human-Readable Output)**

This command runs a simple script with a data file and passes it an argument.

```powershell
python py_test_runner.py `
    --script my_script.py `
    --reqs requirements.txt `
    --inputs data.csv `
    --script-args "--input-file data.csv --mode fast"
```
*Output will be progress logs on `stderr` and the script's own output (from `print` statements) on `stdout`.*

**2. Automated Run (JSON Output)**

This is the same command, but optimized for automation. The script runs silently and prints a single JSON object at the end.

```powershell
python py_test_runner.py `
    --script my_script.py `
    --reqs requirements.txt `
    --inputs data.csv `
    --script-args "--input-file data.csv --mode fast" `
    --json-output
```

## Outputs

### Standard Output

*   **Human-Readable Mode:** In the default mode, the raw output (`stdout`) of the script being executed inside the container is piped to the runner's `stdout`.
*   **JSON Mode:** In this mode, `stdout` is reserved for a single JSON object describing the final result of the run.

### Filesystem Output

*   The runner will automatically create a `./results` directory in your current working directory.
*   Any new files created by your script during its execution will be automatically copied from the container into this `./results` directory.
*   **Important:** The `./results` directory is **deleted and recreated** on every run to ensure a clean output environment.

### JSON Output Schema

When using the `--json-output` flag, the script will produce one of the following JSON structures.

#### On Success:
```json
{
  "status": "success",
  "message": "Script executed successfully. Captured 2 output file(s).",
  "captured_files": [
    "output.csv",
    "plot.png"
  ],
  "details": {
    "raw_logs": "Container's raw stdout and stderr logs go here..."
  }
}
```

#### On Failure:
The `status` will be `"error"` and an `error_type` field will specify the nature of the failure.

*   `file_not_found`: A required input file (script, reqs, or inputs) was not found.
*   `environment_setup_failed`: The `pip install` command failed inside the container. Check the `raw_logs` for the `pip` error message.
*   `script_execution_failed`: The user's script started but exited with a non-zero status code. Check `raw_logs` for the script's traceback.
*   `docker_daemon_error`: The runner could not communicate with the Docker daemon.
*   `runner_internal_error`: An unexpected error occurred within the `py_test_runner.py` script itself.

**Example Script Failure JSON:**
```json
{
  "status": "error",
  "error_type": "script_execution_failed",
  "message": "The user script failed with a non-zero exit code.",
  "details": {
    "exit_code": 1,
    "raw_logs": "Traceback (most recent call last):\n  File \"/app/my_buggy_script.py\", line 5, in <module>\n    x = 1 / 0\nZeroDivisionError: division by zero"
  }
}
```
