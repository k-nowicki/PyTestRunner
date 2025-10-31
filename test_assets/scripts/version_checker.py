import sys

with open("output.txt", "w") as f:
    f.write(f"This script was executed by Python version: {sys.version}\n")

print("Python version has been written to output.txt.")
