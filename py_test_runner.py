import argparse
import sys
from pathlib import Path
import tempfile
import shutil
import docker
import time
import json
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ScriptResult:
    """Holds the results of a script execution."""
    status: str
    message: str
    captured_files: Optional[List[str]] = None
    details: Optional[dict] = None

@dataclass
class ScriptConfig:
    """Holds all script configuration."""
    script_path: Path
    reqs_path: Path
    input_paths: List[Path]
    script_args: str
    json_output: bool
    python_version: str

# --- Custom Exceptions ---
class RunnerError(Exception):
    """Base exception for the runner."""
    error_type = "runner_internal_error"
    def __init__(self, message, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details if details is not None else {}

class EnvironmentSetupError(RunnerError):
    """Raised when dependency installation fails."""
    error_type = "environment_setup_failed"

class ScriptExecutionError(RunnerError):
    """Raised when the user script fails."""
    error_type = "script_execution_failed"

class DockerDaemonError(RunnerError):
    """Raised for issues with the Docker daemon connection."""
    error_type = "docker_daemon_error"

class WorkspaceManager:
    """Manages the temporary workspace and results directory."""
    def __init__(self, config: ScriptConfig):
        self.config = config
        self.results_dir = Path.cwd() / "results"
        self.temp_dir = None
        self.temp_path = None
        self.initial_files = set()

    def __enter__(self):
        """Sets up the workspace."""
        # Prepare and clean the output directory
        if self.results_dir.exists():
            shutil.rmtree(self.results_dir)
        self.results_dir.mkdir()

        # Create a temporary directory and copy all necessary files
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        shutil.copy(self.config.script_path, self.temp_path)
        shutil.copy(self.config.reqs_path, self.temp_path)
        for input_file in self.config.input_paths:
            shutil.copy(input_file, self.temp_path)

        # Take a snapshot of the context before execution
        self.initial_files = set(p.name for p in self.temp_path.iterdir())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleans up the temporary directory."""
        if not self.temp_dir:
            return

        timeout = 15
        interval = 0.5
        start_time = time.time()
        while True:
            try:
                shutil.rmtree(self.temp_dir)
                break
            except OSError as e:
                if time.time() - start_time > timeout:
                    print(f"FATAL: Failed to clean up temp dir {self.temp_dir}. Error: {e}", file=sys.stderr)
                    break
                time.sleep(interval)
    
    def capture_outputs(self) -> List[str]:
        """Compares snapshots to find new files and copies them to results_dir."""
        final_files = set(p.name for p in self.temp_path.iterdir())
        new_files = final_files - self.initial_files
        captured_files = sorted(list(new_files))

        for file_name in captured_files:
            shutil.copy(self.temp_path / file_name, self.results_dir)
        
        return captured_files


class DockerRunner:
    """Manages the Docker container lifecycle."""
    def __init__(self, config: ScriptConfig, workspace_path: Path, log_func):
        self.config = config
        self.workspace_path = workspace_path
        self.log = log_func
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            raise DockerDaemonError(f"Failed to connect to Docker daemon: {e}") from e
        self.image = f"python:{self.config.python_version}-slim"

    def run(self) -> ScriptResult:
        """
        Runs the full container sequence: pull, create, start, wait, logs, remove.
        Returns the container logs on success.
        Raises a specific RunnerError on failure.
        """
        script_name = self.config.script_path.name
        reqs_name = self.config.reqs_path.name
        command_str = (
            f"python -m venv /opt/venv && "
            f"/opt/venv/bin/pip install -r /app/{reqs_name} && "
            f"/opt/venv/bin/python /app/{script_name} {self.config.script_args}"
        )
        command = ["sh", "-c", command_str]

        container = None
        try:
            self.log(f"Pulling image: {self.image}...")
            self.client.images.pull(self.image)
            
            self.log(f"Creating container...")
            container = self.client.containers.create(
                self.image,
                command,
                volumes={str(self.workspace_path.resolve()): {'bind': '/app', 'mode': 'rw'}},
                working_dir='/app'
            )
            
            self.log(f"Starting container: {container.short_id}...")
            container.start()
            
            result = container.wait()
            exit_code = result['StatusCode']
            self.log(f"Container finished with exit code: {exit_code}")

            logs_bytes = container.logs(stdout=True, stderr=True)
            container_logs = logs_bytes.decode('utf-8').strip()
            self.log("Container logs captured.")

            if exit_code != 0:
                pip_error_signatures = [
                    "Could not find a version that satisfies",
                    "No matching distribution found",
                    "Invalid requirement:",
                    "is not a valid requirement."
                ]
                is_pip_error = any(sig in container_logs for sig in pip_error_signatures)
                details = {"exit_code": exit_code, "raw_logs": container_logs}
                
                if is_pip_error:
                    return ScriptResult(
                        status="environment_setup_failed",
                        message="Failed to install dependencies from requirements.txt.",
                        details=details
                    )
                else:
                    return ScriptResult(
                        status="script_failed",
                        message="The user script failed with a non-zero exit code.",
                        details=details
                    )
            
            return ScriptResult(status="success", message="Script executed successfully.", details={"raw_logs": container_logs})
        except docker.errors.DockerException as e:
            # Broadly catch other Docker errors (e.g., image not found if pull fails)
            raise DockerDaemonError(f"A Docker error occurred: {e}") from e
        finally:
            if container:
                self.log(f"Removing container: {container.short_id}")
                container.remove()


def handle_exit(is_json_output, status, data):
    """
    Prints the final result as either a JSON object or human-readable logs
    and exits the script.
    """
    if is_json_output:
        # For JSON output, print the structured data to stdout and nothing else.
        print(json.dumps(data, indent=2))
    else:
        # For human-readable output, print messages to the appropriate streams.
        is_failure_report = data.get("status") in ["script_failed", "environment_setup_failed"]
        log_stream = sys.stderr if status == 'error' or is_failure_report else sys.stdout
        print(data.get("message", ""), file=log_stream)
        if "details" in data and "raw_logs" in data["details"]:
             # In case of container errors, show the raw logs for context.
            print("\n--- Container Logs ---", file=sys.stderr)
            print(data["details"]["raw_logs"], file=sys.stderr)
            print("----------------------", file=sys.stderr)

    exit_code = 0 if status == 'success' else 1
    sys.exit(exit_code)


def parse_and_validate_args() -> ScriptConfig:
    """Parses CLI arguments and performs initial validation."""
    parser = argparse.ArgumentParser(description="A simple Python script runner using Docker.")
    parser.add_argument("--script", required=True, help="Path to the Python script to execute.")
    parser.add_argument("--reqs", required=True, help="Path to the requirements.txt file.")
    parser.add_argument("--inputs", nargs='+', help="Optional list of input files to be copied into the context.")
    parser.add_argument("--script-args", type=str, default="", help="A string of arguments to pass to the script being executed.")
    parser.add_argument("--python-version", type=str, default="3.10", help="Specify the Python version for the Docker image (e.g., '3.9', '3.11'). Defaults to '3.10'.")
    parser.add_argument("--json-output", action='store_true', help="Enable JSON output for machine readability.")

    args = parser.parse_args()

    script_path = Path(args.script)
    if not script_path.is_file():
        handle_exit(args.json_output, 'error', {
            "status": "error",
            "error_type": "file_not_found",
            "message": f"Input script not found: {args.script}"
        })

    reqs_path = Path(args.reqs)
    if not reqs_path.is_file():
        handle_exit(args.json_output, 'error', {
            "status": "error",
            "error_type": "file_not_found",
            "message": f"Requirements file not found: {args.reqs}"
        })

    input_paths = []
    if args.inputs:
        for input_file in args.inputs:
            input_path = Path(input_file)
            if not input_path.is_file():
                handle_exit(args.json_output, 'error', {
                    "status": "error",
                    "error_type": "file_not_found",
                    "message": f"Input file not found: {input_file}"
                })
            input_paths.append(input_path)

    return ScriptConfig(
        script_path=script_path,
        reqs_path=reqs_path,
        input_paths=input_paths,
        script_args=args.script_args,
        json_output=args.json_output,
        python_version=args.python_version
    )


def main():
    """
    Creates a temporary context, mounts it as a volume in a Docker container,
    and lists its contents.
    """
    config = parse_and_validate_args()

    # Centralized logging function for human-readable mode
    log = lambda msg: print(msg, file=sys.stderr) if not config.json_output else None

    try:
        with WorkspaceManager(config) as workspace:
            log(f"Preparing clean output directory at: {workspace.results_dir}")
            log(f"Temporary context created and files copied to: {workspace.temp_path}")
            log(f"Initial context contains: {', '.join(workspace.initial_files) or 'no files'}")

            runner = DockerRunner(config, workspace.temp_path, log)
            result = runner.run()

            captured_files = workspace.capture_outputs()
            log(f"Found {len(captured_files)} new file(s) to capture: {', '.join(captured_files) or 'none'}")
            log(f"All new files copied to: {workspace.results_dir}")
        
        # runner.run() now returns a result object. We augment it with captured files.
        result.captured_files = captured_files
        
        # The runner itself succeeded, so the exit status is 'success'
        # The JSON payload will describe the script's outcome.
        handle_exit(config.json_output, 'success', {
            "status": result.status,
            "message": result.message,
            "captured_files": result.captured_files,
            "details": result.details
        })

    except RunnerError as e:
        handle_exit(config.json_output, 'error', {
            "status": "error",
            "error_type": e.error_type,
            "message": e.message,
            "details": e.details
        })
    except Exception as e:
        # Fallback for truly unexpected errors
        internal_error = RunnerError(
            f"An unexpected internal error occurred in the runner: {e}"
        )
        handle_exit(config.json_output, 'error', {
            "status": "error",
            "error_type": internal_error.error_type,
            "message": internal_error.message,
            "details": {}
        })


if __name__ == "__main__":
    main()
