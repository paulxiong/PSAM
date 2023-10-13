import subprocess
import time
import os
def run_app_a():
    app_a = ["python", "monitor_and_execute.py", "/Users/boxiong/Library/Containers/com.example.tiktokClone/Data/Documents/image_database.db", "search.py"]
    return subprocess.Popen(app_a, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# def run_flutter_app_b():
#     # Replace 'flutter run' with the actual command to run your Flutter app 
#     app_b = ["flutter", "run", "-d", "macos"]
#     return subprocess.Popen(app_b, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Check if Docker is running
def is_docker_running():
    try:
        subprocess.check_output(["docker", "info"])
        return True
    except subprocess.CalledProcessError:
        return False

# Check if a specific container is running
def is_container_running(container_name):
    try:
        output = subprocess.check_output(["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"])
        return container_name in output.decode("utf-8")
    except subprocess.CalledProcessError:
        return False

# Start a list of containers
def start_containers(container_names):
    for container_name in container_names:
        subprocess.run(["docker", "start", container_name])

# Wait for a list of containers to start
def wait_for_containers(container_names):
    for container_name in container_names:
        while not is_container_running(container_name):
            time.sleep(2)

# Activate the virtual environment and set environment variables
def setup_environment():
    subprocess.run(["source", "/Volumes/997G/github/ISAT_with_segment_anything/venv/bin/activate"], shell=True)
    subprocess.run(["export", "PATH=$PATH:/Volumes/997G/github/photoGPT/flutter/bin/"], shell=True)

# Run the monitor_and_execute.py script
def run_monitor_and_execute():
    subprocess.run(["python", "monitor_and_execute.py", "/Users/boxiong/Library/Containers/com.example.tiktokClone/Data/Documents/image_database.db", "search.py","&"])

# Run the Flutter app
def run_flutter_app():
    subprocess.run(["flutter", "run", "-d", "macos"])

if __name__ == "__main__":
    # List of existing container names to start
    container_names = ["milvus-standalone", "milvus-etcd", "milvus-minio"]

    # Task 1: Check if Docker is running and start it if not
    if not is_docker_running():
        subprocess.run(["open", "-a", "Docker"])

    while not is_docker_running():
        print(f'wait for docker up...')
        time.sleep(2) 

    # Task 2: Start the existing containers
    start_containers(container_names)
    
    # Task 3: Wait for the containers to start
    wait_for_containers(container_names)

    # Task 4: Setup the running environment
    # setup_environment()

    # Task 5: Run the monitor_and_execute.py script
    # os.chdir("/Volumes/997G/github/Personalize-SAM/boost_code")

    # run_monitor_and_execute()
    # process_a = run_app_a()


    # Task 6: Run the Flutter app
    os.chdir("/Volumes/997G/github/photoGPT/tiktok_clone")
    # run_flutter_app()
    # process_b = run_flutter_app_b()

    # while True:
    #     output_a = process_a.stdout.readline().decode('utf-8')
    #     output_b = process_b.stdout.readline().decode('utf-8')
    #     if output_a:
    #         print(output_a)

    #     # if output_a or output_b:
    #     #     print(output_a.strip() if output_a else "", end="")
    #         # print(output_b.strip() if output_b else "", end="")

    #     if process_a.poll() is not None and process_b.poll() is not None:
    #         break