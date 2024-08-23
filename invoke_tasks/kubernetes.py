import base64
import os
import platform
import subprocess
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv
from invoke import task
from loguru import logger

load_dotenv()




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