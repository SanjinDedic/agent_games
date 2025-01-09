import sys
from datetime import datetime

import docker


def clean_docker():
    """Clean all unused Docker resources including images, containers, and build cache."""
    try:
        client = docker.from_env()

        # Get initial disk usage
        initial_space = client.df()

        print("Starting Docker cleanup...")
        print("\n1. Stopping and removing all containers...")
        containers = client.containers.list(all=True)
        for container in containers:
            try:
                print(f"   Stopping container: {container.name}")
                container.stop()
                print(f"   Removing container: {container.name}")
                container.remove()
            except Exception as e:
                print(f"   Error with container {container.name}: {str(e)}")

        print("\n2. Removing all images...")
        images = client.images.list(all=True)
        for image in images:
            try:
                tags = image.tags
                image_id = image.id
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

        print("\n4. Removing all volumes...")
        try:
            client.volumes.prune()
            print("   Unused volumes removed successfully")
        except Exception as e:
            print(f"   Error removing volumes: {str(e)}")

        print("\n5. Removing all networks...")
        try:
            client.networks.prune()
            print("   Unused networks removed successfully")
        except Exception as e:
            print(f"   Error removing networks: {str(e)}")

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

        space_saved = (initial_total - final_total) / (
            1024 * 1024 * 1024
        )  # Convert to GB

        print(f"\nCleanup completed successfully!")
        print(f"Approximately {space_saved:.2f} GB of space freed")

    except docker.errors.DockerException as e:
        print(f"Error connecting to Docker daemon: {str(e)}")
        print("Please ensure Docker is running and you have the necessary permissions.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    print(f"Docker cleanup started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    clean_docker()
