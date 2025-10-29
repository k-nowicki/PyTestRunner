import argparse
import sys
from pathlib import Path
import tempfile
import shutil
import docker
import time
import json

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
        log_stream = sys.stdout if status == 'success' else sys.stderr
        print(data.get("message", ""), file=log_stream)
        if "details" in data and "raw_logs" in data["details"]:
             # In case of container errors, show the raw logs for context.
            print("\n--- Container Logs ---", file=sys.stderr)
            print(data["details"]["raw_logs"], file=sys.stderr)
            print("----------------------", file=sys.stderr)

    exit_code = 0 if status == 'success' else 1
    sys.exit(exit_code)


def main():
    """
    Creates a temporary context, mounts it as a volume in a Docker container,
    and lists its contents.
    """
    parser = argparse.ArgumentParser(description="A simple Python script runner using Docker.")
    parser.add_argument("--script", required=True, help="Path to the Python script to execute.")
    parser.add_argument("--reqs", required=True, help="Path to the requirements.txt file.")
    parser.add_argument("--json-output", action='store_true', help="Enable JSON output for machine readability.")

    args = parser.parse_args()

    # Centralized logging function for human-readable mode
    log = lambda msg: print(msg, file=sys.stderr) if not args.json_output else None

    script_path = Path(args.script)
    reqs_path = Path(args.reqs)

    if not script_path.is_file():
        handle_exit(args.json_output, 'error', {
            "status": "error",
            "error_type": "file_not_found",
            "message": f"Input script not found: {args.script}"
        })
    if not reqs_path.is_file():
        handle_exit(args.json_output, 'error', {
            "status": "error",
            "error_type": "file_not_found",
            "message": f"Requirements file not found: {args.reqs}"
        })
    
    container_logs = ""
    temp_dir = tempfile.mkdtemp()
    try:
        temp_path = Path(temp_dir)
        shutil.copy(script_path, temp_path)
        shutil.copy(reqs_path, temp_path)
        log(f"Temporary context created and files copied to: {temp_path}")

        client = docker.from_env()
        image = "python:3.10-slim"
        
        script_name = script_path.name
        reqs_name = reqs_path.name
        command_str = (
            f"python -m venv /opt/venv && "
            f"/opt/venv/bin/pip install -r /app/{reqs_name} && "
            f"/opt/venv/bin/python /app/{script_name}"
        )
        command = ["sh", "-c", command_str]
        
        container = None
        try:
            log(f"Pulling image: {image}...")
            client.images.pull(image)
            
            log(f"Creating container...")
            container = client.containers.create(
                image,
                command,
                volumes={str(temp_path.resolve()): {'bind': '/app', 'mode': 'rw'}},
                working_dir='/app'
            )
            
            log(f"Starting container: {container.short_id}...")
            container.start()
            
            result = container.wait()
            exit_code = result['StatusCode']
            log(f"Container finished with exit code: {exit_code}")

            logs_bytes = container.logs(stdout=True, stderr=True)
            container_logs = logs_bytes.decode('utf-8').strip()
            log("Container logs captured.")

            if exit_code != 0:
                raise docker.errors.ContainerError(
                    f"Container exited with a non-zero status code: {exit_code}",
                    exit_code, command, image, logs_bytes
                )
        finally:
            if container:
                log(f"Removing container: {container.short_id}")
                container.remove()

        output_file_name = "output.txt"
        output_file_in_temp = temp_path / output_file_name
        if not output_file_in_temp.is_file():
             handle_exit(args.json_output, 'error', {
                "status": "error",
                "error_type": "output_file_missing",
                "message": f"Output file '{output_file_name}' not found after execution.",
                "details": {"raw_logs": container_logs}
            })

        shutil.copy(output_file_in_temp, Path.cwd())
        log(f"Output file '{output_file_name}' captured and copied to current directory.")

    except docker.errors.ContainerError as e:
        # Heuristic to determine failure phase
        is_pip_error = "Could not find a version that satisfies" in container_logs or \
                       "No matching distribution found" in container_logs
        
        if is_pip_error:
            handle_exit(args.json_output, 'error', {
                "status": "error",
                "error_type": "environment_setup_failed",
                "message": "Failed to install dependencies from requirements.txt.",
                "details": {"exit_code": e.exit_status, "raw_logs": container_logs}
            })
        else:
            handle_exit(args.json_output, 'error', {
                "status": "error",
                "error_type": "script_execution_failed",
                "message": "The user script failed with a non-zero exit code.",
                "details": {"exit_code": e.exit_status, "raw_logs": container_logs}
            })

    except docker.errors.DockerException as e:
        handle_exit(args.json_output, 'error', {
            "status": "error",
            "error_type": "docker_daemon_error",
            "message": f"An error occurred with the Docker daemon: {e}",
            "details": {"raw_logs": container_logs}
        })
    except Exception as e:
        handle_exit(args.json_output, 'error', {
            "status": "error",
            "error_type": "runner_internal_error",
            "message": f"An unexpected internal error occurred in the runner: {e}",
            "details": {"raw_logs": container_logs}
        })
    finally:
        log(f"Cleaning up temporary directory: {temp_dir}")
        timeout = 15
        interval = 0.5
        start_time = time.time()
        while True:
            try:
                shutil.rmtree(temp_dir)
                log("Temporary directory cleaned up successfully.")
                break
            except OSError as e:
                if time.time() - start_time > timeout:
                    # This final error cannot use handle_exit as we are already in an exit path
                    print(f"FATAL: Failed to clean up temp dir {temp_dir}. Error: {e}", file=sys.stderr)
                    break
                time.sleep(interval)
    
    handle_exit(args.json_output, 'success', {
        "status": "success",
        "message": "Script executed successfully and output file was captured.",
        "details": {"raw_logs": container_logs}
    })


if __name__ == "__main__":
    main()
