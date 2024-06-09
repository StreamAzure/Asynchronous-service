import os
import sys

PREFIX = "microracer" # Image name prefix
VERSION = "base" # Image version

base_path = os.getcwd()
build_paths = []

def mvn_build():
    """
    1. Use Maven to compile and generate jar packages for all modules
    """
    mvn_status = os.system("mvn clean package -DskipTests")
    return mvn_status == 0

def init_docker_build_paths():
    """
    2. Get the absolute paths of each module
    """
    list_paths = os.listdir(os.getcwd())
    for p in list_paths:
        if os.path.isdir(p):
            if p.startswith("ts-"):
                build_path = base_path + "/" + p
                build_paths.append(build_path)

def docker_build():
    """
    3. Build images based on the Dockerfiles in each module directory
    """
    total = len(build_paths)
    failed_images = []
    for build_path in build_paths:
        image_name = build_path.split("/")[-1]
        # The image name is the module directory name, such as ts-station-service

        os.chdir(build_path)
        files = os.listdir(build_path)
        
        # Build images for each module
        if "Dockerfile" in files:
            docker_build_status = os.system(f"docker build . -t {PREFIX}/{image_name}:{VERSION}")
            # e.g. stream/ts-station-service:1.0
            if docker_build_status != 0:
                print(f"[FAIL] {image_name} build failed.")
                failed_images.append(image_name)
            else:
                print(f"[SUCCESS] {image_name} build succeeded.")
            # [FAIL] ts-avatar-service build failed.
    
    print("\nAll building is done.")
    print(f"Total: {total}, Success: {total - len(failed_images)}, Failed: {len(failed_images)}")
    if len(failed_images) > 0:
        print("Building Failed: ", failed_images)

if __name__ == '__main__':
    if not mvn_build():
        print("Maven build failed")
        exit(1)
    init_docker_build_paths()
    docker_build()
