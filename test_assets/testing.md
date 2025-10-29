# PyTestRunner Test Battery

This document outlines a series of commands to test the core functionality and error handling of the `py_test_runner.py` script using the assets in the `test_assets/` directory.

**Prerequisite:** Before running these tests, ensure you have an active virtual environment with the `docker` library installed. (`.venv\Scripts\Activate.ps1` and `pip install -r requirements.txt`)

---

## 1. Core Functionality Tests

### Test 1.1: Successful Execution and Output Capture

This is the primary "happy path" test. It verifies that a simple script can run, create an output file, and that the runner correctly captures it.

**Command:**
```powershell
python py_test_runner.py --script test_assets/scripts/create_output.py --reqs test_assets/reqs/empty_reqs.txt
```

**Expected Outcome:**
*   The script exits with code `0`.
*   A `./results` directory is created.
*   The `./results` directory contains a file named `output.txt` with the content "This is the output file.".
*   The human-readable output confirms that 1 file was captured.

### Test 1.2: Passing Command-Line Arguments to Script

This test verifies that the `--script-args` feature correctly passes arguments to the target script.

**Command:**
```powershell
python py_test_runner.py --script test_assets/scripts/arg_printer.py --reqs test_assets/reqs/empty_reqs.txt --inputs test_assets/inputs/data.csv --script-args '--input-file data.csv --message "Testing 123" --number 42'
```

**Expected Outcome:**
*   The script exits with code `0`.
*   The `./results/output.txt` file is created and contains the parsed arguments, confirming they were received correctly by `arg_printer.py`.

### Test 1.3: Handling Additional Input Files

This test verifies that files passed via `--inputs` are available to the script. The `read_input.py` script copies the input `data.csv` to `output.txt`.

**Command:**
```powershell
python py_test_runner.py --script test_assets/scripts/read_input.py --reqs test_assets/reqs/empty_reqs.txt --inputs test_assets/inputs/data.csv
```

**Expected Outcome:**
*   The script exits with code `0`.
*   The `./results/output.txt` file is created and its content is identical to `test_assets/inputs/data.csv`.

---

## 2. Error Handling Tests (JSON Output)

These tests are best run with the `--json-output` flag to verify the structured error reporting.

### Test 2.1: Failure - Environment Setup (`pip` install)

This test ensures that a failure during the `pip install` phase is correctly identified.

**Command:**
```powershell
python py_test_runner.py --script test_assets/scripts/simple_print.py --reqs test_assets/reqs/faulty_reqs.txt --json-output
```

**Expected Outcome:**
*   The script exits with code `1`.
*   A single JSON object is printed to `stdout`.
*   The JSON contains `"status": "error"` and `"error_type": "environment_setup_failed"`.
*   The `details.raw_logs` field contains the error message from `pip`.

### Test 2.2: Failure - Script Execution (Unhandled Exception)

This test ensures that an error within the user's script is correctly identified and that the traceback is captured.

**Command:**
```powershell
python py_test_runner.py --script test_assets/scripts/buggy_script.py --reqs test_assets/reqs/empty_reqs.txt --json-output
```

**Expected Outcome:**
*   The script exits with code `1`.
*   A single JSON object is printed to `stdout`.
*   The JSON contains `"status": "error"` and `"error_type": "script_execution_failed"`.
*   The `details.raw_logs` field contains the full Python traceback for the `ZeroDivisionError`.

### Test 2.3: Failure - Input File Not Found

This test verifies the runner's built-in file validation.

**Command:**
```powershell
python py_test_runner.py --script test_assets/scripts/simple_print.py --reqs non_existent_file.txt --json-output
```

**Expected Outcome:**
*   The script exits with code `1`.
*   The JSON output contains `"status": "error"` and `"error_type": "file_not_found"`.
*   The `message` field indicates which file was missing.

### Test 2.4: Success - No Output Files Created

This test ensures the runner behaves correctly when the script runs successfully but does not create any new files.

**Command:**
```powershell
python py_test_runner.py --script test_assets/scripts/simple_print.py --reqs test_assets/reqs/empty_reqs.txt --json-output
```

**Expected Outcome:**
*   The script exits with code `0`.
*   The JSON output contains `"status": "success"`.
*   The `captured_files` field is an empty list `[]`.
*   The `./results` directory is created and is empty.
