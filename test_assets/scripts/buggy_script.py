# This script is designed to fail
import sys

print("This script will now raise an unhandled exception to generate a traceback.")

def faulty_function():
    # This will raise a ZeroDivisionError
    x = 1 / 0

faulty_function()
