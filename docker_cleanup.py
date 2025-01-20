import sys
import argparse
from datetime import datetime
import docker

def clean_docker(simulator=True, validator=True):
    """
    Clean Docker resources based on specified parameters.
    
    Args:
        simulator (bool): Clean simulator-related resources if True
        validator (bool): Clean validator-related resources if True
    """
    try:
        client = docker.from_env()

        # Get initial disk usage
        initial_space = client.df()

        print("Starting Docker cleanup...")

        # Helper function to check if resource is related to simulator/validator
        def is_target_resource(name):
            if simulator and 'simulator' in name.lower():
                return True
            if validator and 'validator' in name.lower():
                return True
            return False

        print("\n1. Stopping and removing containers...")
        containers = client.containers.list(all=True)
        for container in containers:
            if is_target_resource(container.name):
                try:
                    print(f"   Stopping container: {container.name}")
                    container.stop()
                    print(f"   Removing container: {container.name}")
                    container.remove()
                except Exception as e:
                    print(f"   Error with container {container.name}: {str(e)}")

        print("\n2. Removing images...")
        images = client.images.list(all=True)
        for image in images:
            tags = image.tags
            image_id = image.id
            # Check if any tag contains simulator/validator
            if any(is_target_resource(tag) for tag in tags):
                try:
                    if tags:
                        print(f"   Removing image: {tags[0]}")
                    else:
                        print(f"   Removing untagged image: {image_id[:12]}")
                    client.images.remove(image.id, force=True)
                except Exception as e:
                    print(f"   Error removing image {image_id[:12]}: {str(e)}")

        print("\n3. Removing build cache...")
        try:
            client.api.prune_builds()
            print("   Build cache removed successfully")
        except Exception as e:
            print(f"   Error removing build cache: {str(e)}")

        print("\n4. Removing volumes...")
        volumes = client.volumes.list()
        for volume in volumes:
            if is_target_resource(volume.name):
                try:
                    volume.remove(force=True)
                    print(f"   Removed volume: {volume.name}")
                except Exception as e:
                    print(f"   Error removing volume {volume.name}: {str(e)}")

        print("\n5. Removing networks...")
        networks = client.networks.list()
        for network in networks:
            if is_target_resource(network.name):
                try:
                    network.remove()
                    print(f"   Removed network: {network.name}")
                except Exception as e:
                    print(f"   Error removing network {network.name}: {str(e)}")

        # Get final disk usage
        final_space = client.df()

        # Calculate space saved
        initial_total = (
            sum(space["Size"] for space in initial_space["Images"])
            + sum(space["Size"] for space in initial_space["Containers"])
            + sum(space["Size"] for space in initial_space["Volumes"])
        )

        final_total = (
            sum(space["Size"] for space in final_space["Images"])
            + sum(space["Size"] for space in final_space["Containers"])
            + sum(space["Size"] for space in final_space["Volumes"])
        )

        space_saved = (initial_total - final_total) / (1024 * 1024 * 1024)  # Convert to GB

        print(f"\nCleanup completed successfully!")
        print(f"Approximately {space_saved:.2f} GB of space freed")

    except docker.errors.DockerException as e:
        print(f"Error connecting to Docker daemon: {str(e)}")
        print("Please ensure Docker is running and you have the necessary permissions.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Clean Docker resources for simulator and/or validator')
    parser.add_argument('-s', '--simulator', action='store_true', 
                        help='Clean only simulator-related resources')
    parser.add_argument('-v', '--validator', action='store_true',
                        help='Clean only validator-related resources')
    return parser.parse_args()

if __name__ == "__main__":
    print(f"Docker cleanup started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    args = parse_arguments()
    
    # If no specific flags are provided, clean both
    if not args.simulator and not args.validator:
        clean_docker(simulator=True, validator=True)
    else:
        clean_docker(simulator=args.simulator, validator=args.validator)