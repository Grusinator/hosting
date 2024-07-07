import base64
import os
import platform
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv
from invoke import task
from loguru import logger

load_dotenv()


def check_docker_installed():
    """Check if Docker is installed by running `docker --version`."""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True, text=True)
        print("Docker is installed and running.")
    except subprocess.CalledProcessError:
        print("Docker is not installed or not running correctly. Please install Docker and ensure it is running.")
        exit(1)


def start_docker():
    """Start Docker daemon if it is not running."""
    system = platform.system()
    if system == "Windows":
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if "error during connect" in result.stderr:
            logger.info("Starting Docker Desktop...")
            docker_desktop_path = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
            if os.path.exists(docker_desktop_path):
                logger.info(f"Found Docker Desktop at {docker_desktop_path}, starting it now...")
                subprocess.Popen([docker_desktop_path], shell=True)
            else:
                logger.error(f"Docker Desktop executable not found at {docker_desktop_path}")
                exit(1)
            # Wait for Docker to start
            max_attempts = 30
            for attempt in range(max_attempts):
                result = subprocess.run(["docker", "info"], capture_output=True, text=True)
                if "error during connect" not in result.stderr:
                    logger.info("Docker Desktop is running.")
                    break
                logger.info(f"Waiting for Docker Desktop to start... (attempt {attempt + 1}/{max_attempts})")
                time.sleep(5)
            else:
                logger.error("Docker Desktop did not start in the expected time.")
                exit(1)
    else:
        result = subprocess.run(["systemctl", "is-active", "--quiet", "docker"])
        if result.returncode != 0:
            logger.info("Starting Docker service...")
            subprocess.run(["sudo", "systemctl", "start", "docker"])


@task
def setup_master(ctx):
    """Initialize Docker Swarm on the master node and apply Terraform configuration."""
    check_docker_installed()
    start_docker()
    ctx.run("docker swarm init", warn=True)
    ctx.run("cd terraform && terraform init && terraform apply -auto-approve")


@task
def deploy_docker(ctx):
    """
    Deploy Docker Compose stack to Docker Swarm
    """
    ctx.run("docker stack deploy -c docker-compose-swarm.yml hosting_playground")


@task
def setup_worker(ctx):
    """Add the worker node to the Docker Swarm."""
    check_docker_installed()
    start_docker()
    SWARM_MANAGER_IP = os.getenv("SWARM_MANAGER_IP")
    SWARM_TOKEN = os.getenv("SWARM_TOKEN")
    ctx.run(f"docker swarm join --token {SWARM_TOKEN} {SWARM_MANAGER_IP}:2377")


@task
def deploy(ctx):
    """Deploy the infrastructure using Terraform."""
    check_docker_installed()
    start_docker()
    ctx.run("cd terraform && terraform init && terraform apply -auto-approve")


@task
def push_image(ctx):
    """Build and push Docker image to the local registry."""
    check_docker_installed()
    start_docker()
    ctx.run("docker build -t localhost:5000/my-app:latest .")
    ctx.run("docker push localhost:5000/my-app:latest")


@task
def get_kubeconfig(c):
    # Get the container ID of the k3s server
    result = subprocess.run(['docker-compose', 'ps', '-q', 'k3s-server'], capture_output=True, text=True)
    container_id = result.stdout.strip()

    if not container_id:
        print("k3s-server container not found.")
        return

    # Define paths
    kubeconfig_local_path = os.path.join(os.getcwd(), 'kubeconfig.yaml')
    ca_cert_local_path = os.path.join(os.getcwd(), 'server-ca.crt')

    # Copy kubeconfig file from the container
    subprocess.run(['docker', 'cp', f'{container_id}:/output/kubeconfig.yaml', kubeconfig_local_path])

    # Copy CA certificate from the container
    subprocess.run(
        ['docker', 'cp', f'{container_id}:/var/lib/rancher/k3s/server/tls/server-ca.crt', ca_cert_local_path])

    # Read and encode the CA certificate
    with open(ca_cert_local_path, 'rb') as ca_cert_file:
        ca_cert_content = ca_cert_file.read()
        ca_cert_encoded = base64.b64encode(ca_cert_content).decode('utf-8')

    # Load the kubeconfig file
    with open(kubeconfig_local_path, 'r') as kubeconfig_file:
        kubeconfig = yaml.safe_load(kubeconfig_file)

    # Update the cluster section with the CA certificate
    for cluster in kubeconfig['clusters']:
        cluster['cluster']['certificate-authority-data'] = ca_cert_encoded

    # Save the updated kubeconfig file
    with open(kubeconfig_local_path, 'w') as kubeconfig_file:
        yaml.safe_dump(kubeconfig, kubeconfig_file, default_flow_style=False)

    print(f"Kubeconfig file and CA certificate have been downloaded and updated.")
    print(f"KUBECONFIG path: {kubeconfig_local_path}")


from invoke import task
import subprocess


@task
def get_metallb_logs(c):
    # Define the namespaces and component names
    namespace = "metallb-system"
    components = ["controller", "speaker"]

    # Iterate over the components and fetch logs
    for component in components:
        # Get the pod name for each component
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-l", f"component={component}", "-o",
             "jsonpath={.items[0].metadata.name}"],
            capture_output=True,
            text=True
        )
        pod_name = result.stdout.strip()

        if not pod_name:
            print(f"No pods found for component: {component}")
            continue

        # Fetch logs from the pod
        logs_result = subprocess.run(
            ["kubectl", "logs", pod_name, "-n", namespace],
            capture_output=True,
            text=True
        )
        logs = logs_result.stdout

        # Filter logs for errors
        error_logs = [line for line in logs.split('\n') if "error" in line.lower()]

        # Print the filtered error logs
        if error_logs:
            print(f"\nError logs for {component} ({pod_name}):")
            for log in error_logs:
                print(log)
        else:
            print(f"\nNo error logs found for {component} ({pod_name}).")


@task
def set_kubeconfig_env_var(ctx):
    kubeconfig_path = Path.cwd() / 'kubeconfig.yaml'
    os.environ['KUBECONFIG'] = str(kubeconfig_path)
    ctx.run(f'set KUBECONFIG={kubeconfig_path}')
    ctx.run(f'echo $KUBECONFIG')
    print(f"KUBECONFIG environment variable has been set to: {kubeconfig_path}")
