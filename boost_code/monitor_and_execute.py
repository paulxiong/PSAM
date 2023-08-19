import sys
import time
import subprocess
import os

def main(file_to_monitor, python_script, *python_args):
    print("Monitoring started...")
    last_modified = os.path.getmtime(file_to_monitor)

    try:
        while True:
            time.sleep(1)
            current_modified = os.path.getmtime(file_to_monitor)
            if current_modified != last_modified:
                last_modified = current_modified
                print("File modified. Executing Python script...")
                subprocess.run(["python3", python_script] + list(python_args))
    except KeyboardInterrupt:
        print("Monitoring stopped.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 monitor_and_execute.py <file_to_monitor> <python_script> [python_args ...]")
    else:
        file_to_monitor = sys.argv[1]
        python_script = sys.argv[2]
        python_args = sys.argv[3:]
        main(file_to_monitor, python_script, *python_args)
