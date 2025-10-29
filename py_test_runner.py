import argparse
import sys
from pathlib import Path
import tempfile
import shutil
import docker

def main():
    """
    Initializes Docker client and runs a simple test container.
    """
    parser = argparse.ArgumentParser(description="A simple Python script runner using Docker.")
    parser.add_argument("--script", required=True, help="Path to the Python script to execute.")
    parser.add_argument("--reqs", required=True, help="Path to the requirements.txt file.")

    args = parser.parse_args()

    script_path = Path(args.script)
    reqs_path = Path(args.reqs)

    if not script_path.is_file():
        raise FileNotFoundError(f"File not found: {args.script}")
    if not reqs_path.is_file():
        raise FileNotFoundError(f"File not found: {args.reqs}")

    client = docker.from_env()
    print("Docker client initialized.")

    image = "python:3.10-slim"
    command = "echo 'Hello from Docker'"
    
    print(f"Pulling image: {image}...")
    client.images.pull(image)
    print("Image pulled.")

    print(f"Running command in container: {command}")
    container_logs = client.containers.run(
        image,
        command,
        auto_remove=True
    )

    print("Container executed successfully. Logs:")
    print(container_logs.decode('utf-8').strip())

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except docker.errors.DockerException as e:
        print(f"ERROR: Docker operation failed. Is the Docker daemon running?", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
