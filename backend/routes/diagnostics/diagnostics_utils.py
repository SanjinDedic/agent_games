import json
import logging
import os
import platform
import re
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import psutil

from backend.docker_utils.compose_utils import (
    check_service_health,
    get_container_logs,
    get_running_services,
    run_docker_compose_command,
)

logger = logging.getLogger(__name__)


def get_service_logs(service_name: str, tail: Optional[int] = 100, since: Optional[str] = None) -> str:
    """
    Get logs for a specific service
    
    Args:
        service_name: Name of the service to get logs for
        tail: Number of log lines to return (default: 100)
        since: ISO 8601 timestamp to get logs since (default: None)
        
    Returns:
        Logs as a string
    """
    cmd = ["logs", service_name]
    
    if tail:
        cmd.extend(["--tail", str(tail)])
    
    if since:
        cmd.extend(["--since", since])
        
    result = run_docker_compose_command(cmd)
    return result.stdout if result.returncode == 0 else f"Error retrieving logs: {result.stderr}"


def get_all_service_logs(tail: Optional[int] = 100, since: Optional[str] = None) -> Dict[str, str]:
    """
    Get logs for all running services
    
    Args:
        tail: Number of log lines to return (default: 100)
        since: ISO 8601 timestamp to get logs since (default: None)
        
    Returns:
        Dictionary mapping service names to their logs
    """
    running_services = get_running_services()
    logs = {}
    
    for service in running_services:
        logs[service] = get_service_logs(service, tail, since)
        
    return logs


def get_container_id(service_name: str) -> str:
    """Get the Docker container ID for a service"""
    result = run_docker_compose_command(["ps", "-q", service_name])
    return result.stdout.strip()


def get_container_stats(container_id: str) -> Dict:
    """
    Get detailed stats for a container using docker stats command
    """
    try:
        # Use docker stats with --no-stream to get a single reading
        result = subprocess.run(
            ["docker", "stats", container_id, "--no-stream", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the JSON output
        stats = json.loads(result.stdout)
        return stats
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.error(f"Error getting container stats for {container_id}: {e}")
        return {}


def get_service_resource_usage(service_name: str) -> Dict:
    """
    Get resource usage for a specific service
    
    Returns:
        Dictionary with resource usage information
    """
    container_id = get_container_id(service_name)
    if not container_id:
        return {
            "container_id": "unknown",
            "name": service_name,
            "status": "not found",
            "cpu_percent": 0.0,
            "memory_usage": "0B",
            "memory_percent": 0.0,
            "network_io": {"rx": "0B", "tx": "0B"},
            "disk_io": {"read": "0B", "write": "0B"},
            "uptime": "0s"
        }

    try:
        # Get container information
        inspect_result = subprocess.run(
            ["docker", "inspect", container_id],
            capture_output=True,
            text=True,
            check=True
        )
        inspect_data = json.loads(inspect_result.stdout)[0]
        
        # Get container stats
        stats = get_container_stats(container_id)
        
        # Parse the stats
        name = service_name
        status = inspect_data["State"]["Status"]
        
        # Calculate uptime
        if status == "running":
            start_time_str = inspect_data["State"]["StartedAt"]
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            uptime = datetime.now().astimezone() - start_time
            uptime_str = format_timedelta(uptime)
        else:
            uptime_str = "not running"
        
        # Extract values from stats
        cpu_percent = float(stats.get("CPUPerc", "0%").rstrip("%") or 0)
        memory_usage = stats.get("MemUsage", "0B / 0B").split(" / ")[0]
        memory_percent = float(stats.get("MemPerc", "0%").rstrip("%") or 0)
        
        # Extract network IO
        network_rx = "0B"
        network_tx = "0B"
        if "NetIO" in stats:
            net_parts = stats["NetIO"].split(" / ")
            if len(net_parts) == 2:
                network_rx = net_parts[0]
                network_tx = net_parts[1]
        
        # Extract disk IO
        disk_read = "0B"
        disk_write = "0B"
        if "BlockIO" in stats:
            block_parts = stats["BlockIO"].split(" / ")
            if len(block_parts) == 2:
                disk_read = block_parts[0]
                disk_write = block_parts[1]
        
        return {
            "container_id": container_id,
            "name": name,
            "status": status,
            "cpu_percent": cpu_percent,
            "memory_usage": memory_usage,
            "memory_percent": memory_percent,
            "network_io": {"rx": network_rx, "tx": network_tx},
            "disk_io": {"read": disk_read, "write": disk_write},
            "uptime": uptime_str
        }
    except Exception as e:
        logger.error(f"Error getting resource usage for {service_name}: {e}")
        return {
            "container_id": container_id,
            "name": service_name,
            "status": "error",
            "cpu_percent": 0.0,
            "memory_usage": "0B",
            "memory_percent": 0.0,
            "network_io": {"rx": "0B", "tx": "0B"},
            "disk_io": {"read": "0B", "write": "0B"},
            "uptime": "error"
        }


def get_all_services_resource_usage() -> Dict[str, Dict]:
    """
    Get resource usage for all running services
    
    Returns:
        Dictionary mapping service names to their resource usage
    """
    running_services = get_running_services()
    usage = {}
    
    for service in running_services:
        usage[service] = get_service_resource_usage(service)
        
    return usage


def get_system_resources() -> Dict:
    """
    Get overall system resource usage
    
    Returns:
        Dictionary with system resource information
    """
    # Get CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.5)
    
    # Get memory usage
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    memory_available = format_bytes(memory.available)
    
    # Get disk usage for root partition
    disk = psutil.disk_usage('/')
    disk_percent = disk.percent
    disk_available = format_bytes(disk.free)
    
    # Get load average
    if platform.system() != "Windows":  # Load average not available on Windows
        load_avg = os.getloadavg()
    else:
        load_avg = [0.0, 0.0, 0.0]
    
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "memory_available": memory_available,
        "disk_percent": disk_percent,
        "disk_available": disk_available,
        "load_average": load_avg
    }


def get_service_status(service_name: str) -> Dict:
    """
    Get status information for a service
    
    Args:
        service_name: Name of the service to check
        
    Returns:
        Dictionary with service status information
    """
    is_healthy, health_message = check_service_health(service_name)
    
    # Get container status
    container_id = get_container_id(service_name)
    status = "stopped"
    
    if container_id:
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", container_id],
                capture_output=True,
                text=True,
                check=True
            )
            status = result.stdout.strip()
        except subprocess.CalledProcessError:
            status = "unknown"
    
    return {
        "name": service_name,
        "status": status,
        "health": health_message,
        "is_healthy": is_healthy
    }


def get_all_services_status() -> Dict[str, Dict]:
    """
    Get status information for all services
    
    Returns:
        Dictionary mapping service names to their status information
    """
    running_services = get_running_services()
    statuses = {}
    
    for service in running_services:
        statuses[service] = get_service_status(service)
        
    return statuses


# Utility functions
def format_bytes(bytes_value: int) -> str:
    """
    Format bytes to a human-readable string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.2f}{unit}"
        bytes_value /= 1024
    return f"{bytes_value:.2f}PB"


def format_timedelta(td: timedelta) -> str:
    """
    Format a timedelta to a human-readable string
    """
    seconds = td.total_seconds()
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{int(minutes)}m {int(seconds % 60)}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{int(hours)}h {int(minutes)}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{int(days)}d {int(hours)}h"


def parse_docker_stats_output(output: str) -> List[Dict]:
    """
    Parse the output of docker stats command
    """
    # Example output:
    # CONTAINER ID   NAME                CPU %     MEM USAGE / LIMIT     MEM %     NET I/O           BLOCK I/O         PIDS
    # 1a2b3c4d5e6f   container1         0.12%     24.8MiB / 7.669GiB    0.32%     1.12MB / 1.65MB   0B / 0B           12
    # 7g8h9i0j1k2l   container2         1.22%     44.1MiB / 7.669GiB    0.56%     2.23MB / 3.65MB   12MB / 0B         15
    
    result = []
    lines = output.strip().split('\n')
    
    # Skip the header line
    for line in lines[1:]:
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) >= 7:
            container_id = parts[0]
            name = parts[1]
            cpu_percent = float(parts[2].rstrip('%'))
            
            mem_parts = parts[3].split(' / ')
            mem_usage = mem_parts[0]
            mem_limit = mem_parts[1] if len(mem_parts) > 1 else "unknown"
            
            mem_percent = float(parts[4].rstrip('%'))
            
            net_parts = parts[5].split(' / ')
            net_in = net_parts[0]
            net_out = net_parts[1] if len(net_parts) > 1 else "0B"
            
            block_parts = parts[6].split(' / ')
            block_read = block_parts[0]
            block_write = block_parts[1] if len(block_parts) > 1 else "0B"
            
            pids = int(parts[7]) if len(parts) > 7 else 0
            
            result.append({
                'container_id': container_id,
                'name': name,
                'cpu_percent': cpu_percent,
                'memory_usage': mem_usage,
                'memory_limit': mem_limit,
                'memory_percent': mem_percent,
                'network_io': {'rx': net_in, 'tx': net_out},
                'disk_io': {'read': block_read, 'write': block_write},
                'pids': pids
            })
            
    return result