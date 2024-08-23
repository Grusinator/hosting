from invoke import task
import os
import subprocess

from invoke import task
from pyngrok import ngrok
import time

from dotenv import load_dotenv

from invoke_tasks.docker import check_docker_installed, start_docker

load_dotenv()  # This loads the variables from .env


@task
def deploy_hosting_setup(ctx):
    """
    Deploy Docker Compose stack to Docker Swarm
    """
    ctx.run("docker stack deploy -c docker-compose-swarm.yml hosting_infrastructure")

@task
def remove_hosting_setup(ctx):
    """
    Remove the Docker Compose stack from Docker Swarm
    """
    ctx.run("docker stack rm hosting_infrastructure")
    print("Hosting infrastructure has been removed from the swarm.")


@task
def setup_master_node(ctx):
    """Initialize Docker Swarm on the master node using env vars."""
    check_docker_installed()
    start_docker()
    master_ip = os.getenv("SWARM_MASTER_IP")
    if not master_ip:
        raise ValueError("SWARM_MASTER_IP environment variable must be set")
    
    ctx.run(f"docker swarm init --advertise-addr {master_ip}")
    print("Swarm master initialized.")

@task
def get_worker_join_token(ctx):
    """Fetch and print the worker join token for the swarm in .env format."""
    check_docker_installed()
    start_docker()
    result = ctx.run("docker swarm join-token worker -q", hide=True)
    worker_token = result.stdout.strip()
    master_ip = os.getenv("SWARM_MASTER_IP")
    if not master_ip:
        raise ValueError("SWARM_MASTER_IP environment variable must be set")
    
    print("# Docker Swarm Configuration")
    print(f"SWARM_JOIN_TOKEN={worker_token}")
    print(f"SWARM_MASTER_IP={master_ip}")
    print("\n# To join a worker to this swarm, use these environment variables and run:")
    print("# docker swarm join --token $SWARM_JOIN_TOKEN $SWARM_MASTER_IP:2377")

@task
def setup_worker_node(ctx):
    """Join a worker node to the Docker Swarm using env vars."""
    check_docker_installed()
    start_docker()
    join_token = os.getenv("SWARM_JOIN_TOKEN")
    master_ip = os.getenv("SWARM_MASTER_IP")
    if not join_token or not master_ip:
        raise ValueError("SWARM_JOIN_TOKEN and SWARM_MASTER_IP environment variables must be set")
    
    ctx.run(f"docker swarm join --token {join_token} {master_ip}:2377")
    print("Worker node joined the swarm.")

@task
def deploy_to_swarm(ctx, compose_file):
    """Deploy a Docker Compose file to the swarm."""
    check_docker_installed()
    start_docker()
    stack_name = os.path.splitext(os.path.basename(compose_file))[0]
    ctx.run(f"docker stack deploy -c {compose_file} {stack_name}")
    print(f"Stack {stack_name} deployed to the swarm.")

@task
def remove_deployment(ctx, compose_file):
    """Remove a deployed stack from the swarm."""
    check_docker_installed()
    start_docker()
    stack_name = os.path.splitext(os.path.basename(compose_file))[0]
    ctx.run(f"docker stack rm {stack_name}")
    print(f"Stack {stack_name} removed from the swarm.")

@task
def list_nodes(ctx):
    """List all nodes in the Docker Swarm."""
    check_docker_installed()
    start_docker()
    ctx.run("docker node ls")

@task
def remove_node(ctx):
    """Remove the current node from the Docker Swarm."""
    check_docker_installed()
    start_docker()
    ctx.run("docker swarm leave --force")
    print("Node removed from the swarm.")

@task
def status(ctx):
    """Check the status of the Docker Swarm."""
    check_docker_installed()
    start_docker()
    ctx.run("echo Swarm status:")
    ctx.run("docker info --format '{{.Swarm.LocalNodeState}}'")


@task
def start_ngrok(c):
    """
    Start ngrok tunnel for port 80
    """
    print("Starting ngrok tunnel for port 80...")
    http_tunnel = ngrok.connect(80, "http")
    print(f"Ngrok tunnel established: {http_tunnel.public_url}")
    print("Use the following URLs to access your services:")
    print(f"Registry UI: https://registry-ui.wsh-it.dk.{http_tunnel.public_url[8:]}")
    print(f"Traefik dashboard: https://traefik.wsh-it.dk.{http_tunnel.public_url[8:]}")
    print(f"Registry: https://registry.wsh-it.dk.{http_tunnel.public_url[8:]}")
    print("Press Ctrl+C to stop the ngrok tunnel")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping ngrok tunnel...")
        ngrok.kill()

from invoke import task
import platform
import os

@task
def update_hosts(c, hostname="wsh-it.dk"):
    """
    Update hosts file for local testing
    """
    hosts_entry = f"127.0.0.1 registry-ui.{hostname} traefik.{hostname} registry.{hostname}"
    
    if platform.system() == "Windows":
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    else:
        hosts_path = "/etc/hosts"
    
    try:
        with open(hosts_path, "a") as hosts_file:
            hosts_file.write(f"\n{hosts_entry}\n")
        print("Hosts file updated successfully.")
    except PermissionError:
        print("Permission denied. Please run this task with administrator privileges.")
    except Exception as e:
        print(f"An error occurred: {e}")