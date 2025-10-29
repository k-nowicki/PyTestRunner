import argparse

# A simple script to parse and print command-line arguments.
# This is used to test the --script-args functionality of the runner.

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", required=True, help="Path to an input file.")
    parser.add_argument("--message", required=True, help="A message to print.")
    parser.add_argument("--number", type=int, help="A number.")
    
    args = parser.parse_args()
    
    with open("output.txt", "w") as f:
        f.write(f"Script received the following arguments:\n")
        f.write(f"Input File: {args.input_file}\n")
        f.write(f"Message: {args.message}\n")
        f.write(f"Number: {args.number}\n")

    print("Arguments successfully parsed and written to output.txt.")
