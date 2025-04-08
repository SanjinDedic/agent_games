import argparse
import sys
from datetime import datetime

import docker


def clean_docker(
    api=False,
    simulator=False,
    validator=False,
    postgres=False,
    test_db=False,
    all_services=False,
):
    """
    Clean Docker resources based on specified parameters.

    Args:
        api (bool): Clean API-related resources if True
        simulator (bool): Clean simulator-related resources if True
        validator (bool): Clean validator-related resources if True
        postgres (bool): Clean PostgreSQL-related resources if True
        test_db (bool): Clean test database-related resources if True
        all_services (bool): Clean all resources if True
    """
    try:
        client = docker.from_env()

        # If all_services is True, set all options to True
        if all_services:
            api = True
            simulator = True
            validator = True
            postgres = True
            test_db = True

        # If no service is specified, inform the user and exit
        if not any([api, simulator, validator, postgres, test_db]):
            print(
                "No services specified for cleanup. Use options to select services to clean."
            )
            print("Use --all to clean all services.")
            return

        # Try to get initial disk usage, but handle missing keys
        try:
            initial_space = client.df()
        except Exception as e:
            print(f"Note: Couldn't get initial disk usage stats: {str(e)}")
            initial_space = None

        print("Starting Docker cleanup...")
        print(
            f"Selected services: {' '.join(s for s, enabled in zip(['api', 'simulator', 'validator', 'postgres', 'test_db'], [api, simulator, validator, postgres, test_db]) if enabled)}"
        )

        # Helper function to check if resource is related to selected services
        def is_target_resource(name):
            if api and ("api" in name.lower() or "agent_games-api" in name.lower()):
                return True
            if simulator and (
                "simulator" in name.lower() or "agent_games-simulator" in name.lower()
            ):
                return True
            if validator and (
                "validator" in name.lower() or "agent_games-validator" in name.lower()
            ):
                return True
            if postgres and (
                "postgres" in name.lower() or "agent_games-postgres" in name.lower()
            ):
                return True
            if test_db and (
                "test_db" in name.lower()
                or "test-db" in name.lower()
                or "testdb" in name.lower()
            ):
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
            # Check if any tag contains target service names
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
            if is_target_resource(volume.name) or (
                postgres and volume.name == "postgres_data"
            ):
                try:
                    volume.remove(force=True)
                    print(f"   Removed volume: {volume.name}")
                except Exception as e:
                    print(f"   Error removing volume {volume.name}: {str(e)}")

        print("\n5. Removing networks...")
        networks = client.networks.list()
        for network in networks:
            if (
                is_target_resource(network.name)
                or network.name == "agent_games_default"
            ):
                try:
                    network.remove()
                    print(f"   Removed network: {network.name}")
                except Exception as e:
                    print(f"   Error removing network {network.name}: {str(e)}")

        # Try to calculate space saved, but handle missing keys
        if initial_space is not None:
            try:
                final_space = client.df()

                # Safely calculate space using get() with default values
                initial_images = sum(
                    space.get("Size", 0) for space in initial_space.get("Images", [])
                )
                initial_containers = sum(
                    space.get("Size", 0)
                    for space in initial_space.get("Containers", [])
                )
                initial_volumes = sum(
                    space.get("Size", 0) for space in initial_space.get("Volumes", [])
                )

                final_images = sum(
                    space.get("Size", 0) for space in final_space.get("Images", [])
                )
                final_containers = sum(
                    space.get("Size", 0) for space in final_space.get("Containers", [])
                )
                final_volumes = sum(
                    space.get("Size", 0) for space in final_space.get("Volumes", [])
                )

                initial_total = initial_images + initial_containers + initial_volumes
                final_total = final_images + final_containers + final_volumes

                space_saved = (initial_total - final_total) / (
                    1024 * 1024 * 1024
                )  # Convert to GB
                print(f"\nApproximately {space_saved:.2f} GB of space freed")
            except Exception as e:
                print(f"\nCouldn't calculate space saved: {str(e)}")

        print("\nCleanup completed successfully!")

    except docker.errors.DockerException as e:
        print(f"Error connecting to Docker daemon: {str(e)}")
        print("Please ensure Docker is running and you have the necessary permissions.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Clean Docker resources for agent_games services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Docker Cleanup Utility for Agent Games
--------------------------------------
This script helps you clean up Docker resources related to the Agent Games platform.
It can remove containers, images, volumes, networks and build cache for specified services.

The cleanup process includes:
1. Stopping and removing containers
2. Removing Docker images
3. Cleaning Docker build cache
4. Removing Docker volumes
5. Removing Docker networks

You can specify which services to clean up using the options below.
If no options are provided, the script will display this help message.

Examples:
  python docker_cleanup.py --all                 # Clean up all resources
  python docker_cleanup.py -a -p                # Clean up API and PostgreSQL resources
  python docker_cleanup.py -s -v -t             # Clean up simulator, validator, and test database resources

The script will show detailed progress and calculate disk space saved after completion.
""",
    )
    parser.add_argument(
        "-a", "--api", action="store_true", help="Clean API-related resources"
    )
    parser.add_argument(
        "-s",
        "--simulator",
        action="store_true",
        help="Clean simulator-related resources",
    )
    parser.add_argument(
        "-v",
        "--validator",
        action="store_true",
        help="Clean validator-related resources",
    )
    parser.add_argument(
        "-p",
        "--postgres",
        action="store_true",
        help="Clean PostgreSQL-related resources",
    )
    parser.add_argument(
        "-t",
        "--test_db",
        action="store_true",
        help="Clean test database-related resources",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Clean all resources (API, simulator, validator, PostgreSQL, test database)",
    )
    parser.add_argument(
        "--help-full",
        action="store_true",
        help="Show detailed help about the script functionality",
    )
    return parser.parse_args()

if __name__ == "__main__":
    print(f"Docker cleanup started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    args = parse_arguments()

    # Handle special help-full case
    if args.help_full:
        print(
            """
Docker Cleanup Utility for Agent Games - Detailed Help
------------------------------------------------------
This script provides a comprehensive way to clean up Docker resources 
associated with the Agent Games platform. It can target specific components
or clean everything at once.

Supported services for cleanup:
- API containers and resources (-a, --api)
- Simulator containers and resources (-s, --simulator)
- Validator containers and resources (-v, --validator)
- PostgreSQL database containers and volumes (-p, --postgres)
- Test database containers and volumes (-t, --test_db)
- All of the above (--all)

What gets cleaned up:
1. Containers: Stops and removes all containers matching the selected services
2. Images: Removes all Docker images for the selected services
3. Build cache: Prunes the Docker build cache
4. Volumes: Removes volumes associated with the selected services
5. Networks: Removes networks associated with the selected services

The script attempts to calculate and display the disk space freed after cleanup.

Usage examples:
  # Clean up everything:
  python docker_cleanup.py --all
  
  # Clean up only API and PostgreSQL resources:
  python docker_cleanup.py -a -p
  
  # Clean up test database resources:
  python docker_cleanup.py -t
  
  # Clean up simulator and validator:
  python docker_cleanup.py -s -v
"""
        )
        sys.exit(0)

    clean_docker(
        api=args.api,
        simulator=args.simulator,
        validator=args.validator,
        postgres=args.postgres,
        test_db=args.test_db,
        all_services=args.all,
    )
