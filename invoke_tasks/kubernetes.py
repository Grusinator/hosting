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
def setup_cluster(c, name="my-cluster", ip="localhost", api_port=6443):
    """Setup a new Kubernetes cluster with kubeadm and install Traefik"""
    
    # Initialize the Kubernetes cluster with kubeadm
    cmd = f"kubeadm init --apiserver-advertise-address={ip} --apiserver-bind-port={api_port} --pod-network-cidr=10.244.0.0/16"
    c.sudo(cmd)
    print(f"Cluster '{name}' initialized successfully")

    # Set up kubeconfig for kubectl usage
    kubeconfig_path = Path.home() / ".kube" / "config"
    c.sudo(f"mkdir -p {kubeconfig_path.parent}")
    c.sudo(f"cp /etc/kubernetes/admin.conf {kubeconfig_path}")
    c.sudo(f"chown $(id -u):$(id -g) {kubeconfig_path}")
    print(f"Kubeconfig written to {kubeconfig_path}")

    # Install a Pod network (e.g., Calico, Flannel)
    c.sudo("kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml")
    print("Pod network installed successfully")

    # Apply Traefik CRD and RBAC
    c.sudo("kubectl apply -f k8s/cluster/traefik-crd.yaml")
    c.sudo("kubectl apply -f k8s/cluster/traefik-rbac.yaml")
    
    # Apply Traefik deployment
    c.sudo("kubectl apply -f k8s/cluster/traefik-deployment.yaml")
    
    print("Traefik Ingress Controller installed successfully")


@task
def delete_cluster(c, name="my-cluster"):
    """Delete the Kubernetes cluster"""
    
    # Tear down the cluster
    c.sudo("kubeadm reset -f")
    c.sudo("rm -rf ~/.kube/config")
    print(f"Cluster '{name}' deleted successfully")



@task
def delete_cluster(c, name="my-cluster"):
    """Delete the Kubernetes cluster"""
    
    # Tear down the cluster
    c.sudo("kubeadm reset -f")
    c.sudo("rm -rf ~/.kube/config")
    print(f"Cluster '{name}' deleted successfully")



@task
def join_as_worker(c):
    # Get environment variables
    k8s_master_ip = os.getenv("K8S_JOIN_IP")
    k8s_token = os.getenv("K8S_JOIN_TOKEN")

    if not k8s_master_ip or not k8s_token:
        print("Environment variables K8S_JOIN_IP and K8S_JOIN_TOKEN are required.")
        return

    # Construct the kubeadm join command with unsafe skip for CA verification
    join_command = f"k3s agent --server https://{k8s_master_ip}:6443 --token {k8s_token}"

    # Execute the join command with sudo
    c.sudo(join_command, pty=True)

@task
def deploy_nginx(c):
    """Deploy Nginx with a custom configuration"""
    # c.run("kubectl apply -f k8s/example_deployments/nginx/nginx-configmap.yaml")
    c.run("kubectl apply -f k8s/example_deployments/nginx/nginx-deployment.yaml")
    c.run("kubectl apply -f k8s/example_deployments/nginx/nginx-service.yaml")
    c.run("kubectl apply -f k8s/example_deployments/nginx/nginx-ingress.yaml")
    print("Nginx deployed successfully")

@task
def delete_nginx(c):
    """Delete the Nginx deployment"""
    c.run("kubectl delete -f nginx-ingress.yaml")
    c.run("kubectl delete -f nginx-service.yaml")
    c.run("kubectl delete -f nginx-deployment.yaml")
    c.run("kubectl delete -f nginx-configmap.yaml")
    print("Nginx deployment deleted")


@task
def deploy_job(c, job_file):
    """Deploy a Kubernetes job"""
    c.run(f"kubectl apply -f {job_file}")
    print(f"Job from {job_file} deployed successfully")

@task
def list_jobs(c):
    """List all Kubernetes jobs"""
    c.run("kubectl get jobs")

@task
def delete_job(c, job_name):
    """Delete a Kubernetes job"""
    c.run(f"kubectl delete job {job_name}")
    print(f"Job '{job_name}' deleted successfully")

@task
def get_job_logs(c, job_name):
    """Get logs for a specific job"""
    c.run(f"kubectl logs job/{job_name}")

@task
def create_docker_registry(c):
    """Create a local Docker registry"""
    c.run("docker run -d -p 5000:5000 --name registry registry:2")
    print("Local Docker registry created on port 5000")

@task
def push_image_to_registry(c, image_name, tag="latest"):
    """Push a Docker image to the local registry"""
    local_image = f"localhost:5000/{image_name}:{tag}"
    c.run(f"docker tag {image_name}:{tag} {local_image}")
    c.run(f"docker push {local_image}")
    print(f"Image {image_name}:{tag} pushed to local registry")




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
def set_kubeconfig_env(c):
    """Set the KUBECONFIG environment variable to the local kubeconfig file"""
    kubeconfig_path = os.path.join(os.getcwd(), 'k8s/kubeconfig.yaml')
    if os.path.exists(kubeconfig_path):
        os.environ['KUBECONFIG'] = kubeconfig_path
        print(f"KUBECONFIG environment variable set to: {kubeconfig_path}")
        
        # For Windows
        if platform.system() == "Windows":
            c.run(f'setx KUBECONFIG "{kubeconfig_path}"')
        # For Unix-like systems (Linux, macOS)
        else:
            c.run(f'echo "export KUBECONFIG={kubeconfig_path}" >> ~/.bashrc')
            c.run(f'echo "export KUBECONFIG={kubeconfig_path}" >> ~/.zshrc')
        
        print("KUBECONFIG environment variable has been set for future sessions.")
    else:
        print(f"Error: kubeconfig file not found at {kubeconfig_path}")


@task
def get_cluster_ip(c):
    """Get the IP address of the cluster for connecting worker nodes"""
    result = c.run("kubectl get nodes -o wide", hide=True)
    lines = result.stdout.split('\n')
    if len(lines) > 1:
        # Split the second line (first node) by whitespace and get the internal IP
        node_info = lines[1].split()
        if len(node_info) >= 6:
            internal_ip = node_info[5]
            print(f"Cluster IP for connecting worker nodes: {internal_ip}")
        else:
            print("Unable to parse node information")
    else:
        print("No nodes found in the cluster")