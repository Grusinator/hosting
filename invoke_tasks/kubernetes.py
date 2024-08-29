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
def setup_cluster(c, name="my-cluster", api_port=6443):
    """Setup a new Kubernetes cluster with kubeadm and install Traefik"""
    ip = os.getenv("K8S_JOIN_IP")
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

def get_control_plane_node(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    """Retrieve the control plane node name."""
    result = c.run(f"KUBECONFIG={kubeconfig} kubectl get nodes --selector='node-role.kubernetes.io/control-plane' -o jsonpath='{{.items[0].metadata.name}}'", hide=True)
    return result.stdout.strip()

@task
def add_taint(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    """Add taint to the control plane node to prevent scheduling workloads."""
    node_name = get_control_plane_node(c)
    taint_cmd = f"KUBECONFIG={kubeconfig} kubectl taint nodes {node_name} node-role.kubernetes.io/control-plane:NoSchedule"
    c.run(taint_cmd)
    print(f"Taint added to {node_name}")

@task
def remove_taint(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    """Remove taint from the control plane node to allow scheduling workloads."""
    node_name = get_control_plane_node(c)
    remove_taint_cmd = f"KUBECONFIG={kubeconfig} kubectl taint nodes {node_name} node-role.kubernetes.io/control-plane:NoSchedule-"
    c.run(remove_taint_cmd)
    print(f"Taint removed from {node_name}")


@task
def deploy_prometheus_grafana(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    admin_password = os.getenv("ADMIN_PASSWORD")
    print(kubeconfig)
    """Deploy Prometheus and Grafana to the Kubernetes cluster"""
    # Add the Helm repositories for Prometheus and Grafana
    c.run("helm repo add prometheus-community https://prometheus-community.github.io/helm-charts")
    c.run("helm repo add grafana https://grafana.github.io/helm-charts")
    c.run("helm repo update")
    
    # Deploy Prometheus
    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install prometheus prometheus-community/prometheus --namespace monitoring --create-namespace \
           --set server.persistentVolume.storageClass=longhorn \
           --set alertmanager.persistentVolume.storageClass=longhorn \
           --set pushgateway.persistentVolume.storageClass=longhorn")
    
    # Deploy Grafana
    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install grafana grafana/grafana --namespace monitoring --create-namespace \
           --set persistence.enabled=true \
           --set persistence.storageClassName=longhorn \
           --set persistence.size=10Gi \
           --set adminPassword='YourAdminPassword' \
           --set service.type=LoadBalancer \
           --set service.port=80")


@task
def deploy_longhorn(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    """Deploy Longhorn storage to the Kubernetes cluster"""
    # Add the Longhorn Helm repository
    c.run("helm repo add longhorn https://charts.longhorn.io")
    c.run("helm repo update")
    # Deploy Longhorn
    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install longhorn longhorn/longhorn --namespace longhorn-system --create-namespace")
    c.run(f"KUBECONFIG={kubeconfig} kubectl apply -f k8s/cluster/longhorn-storageclass.yaml")
    c.run(f"KUBECONFIG={kubeconfig} kubectl patch storageclass longhorn -p '{{\"metadata\": {{\"annotations\":{{\"storageclass.kubernetes.io/is-default-class\":\"true\"}}}}}}'")



@task
def configure_longhorn_node(c, node_name, storage_path='/mnt/longhorn'):
    """
    Configure Longhorn to use a specific directory for storage on a specific node.
    
    :param node_name: The name of the Kubernetes node to configure.
    :param storage_path: The directory path to use for Longhorn storage (default is /mnt/longhorn).
    """
    kubeconfig = os.environ.get('KUBECONFIG')

    # YAML configuration to specify disk settings for Longhorn
    longhorn_disk_yaml = f"""
    apiVersion: longhorn.io/v1beta1
    kind: Node
    metadata:
      name: {node_name}
    spec:
      disks:
        longhorn-disk:
          path: {storage_path}
          allowScheduling: true
          storageReserved: 1024  # Reserve 1GB for the OS
      allowScheduling: true
    """

    # Create the storage directory on the node if it doesn't exist
    # c.run(f"ssh {node_name} 'sudo mkdir -p {storage_path} && sudo chown -R $(whoami):$(whoami) {storage_path}'")

    # Write the configuration to a temporary YAML file
    yaml_file_path = f"/tmp/{node_name}_longhorn_disk.yaml"
    with open(yaml_file_path, "w") as f:
        f.write(longhorn_disk_yaml)

    # Apply the configuration using kubectl
    c.run(f"KUBECONFIG={kubeconfig} kubectl apply -f {yaml_file_path}")

    # Clean up the temporary YAML file
    os.remove(yaml_file_path)

    print(f"Longhorn configuration applied for node: {node_name}, using storage path: {storage_path}")


@task
def get_prometheus_grafana_password(c):
    kubeconfig = os.environ.get('KUBECONFIG')
        # Get the Grafana admin password
    password_command = f"KUBECONFIG={kubeconfig} kubectl get secret --namespace monitoring grafana -o jsonpath=\"{{.data.admin-password}}\" | base64 --decode"
    result = subprocess.run(password_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    grafana_password = result.stdout.decode().strip()
    if grafana_password:
        print(f"Grafana Admin Password: {grafana_password}")
    else:
        print("Could not retrieve Grafana Admin Password")

    # Provide the access URLs
    print("\nAccess Prometheus via:")
    print("  prometheus-server.monitoring.svc.cluster.local:80")
    print("\nAccess Grafana via:")
    print("  grafana.monitoring.svc.cluster.local:80")
    print("To forward Grafana to localhost:3000, run:")
    print("  kubectl --namespace monitoring port-forward svc/grafana 3000:80")


@task
def deploy_pod_network(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    """Install Calico v3.28 on the Kubernetes cluster"""
    # Add the Calico Helm repository
    c.run("helm repo add projectcalico https://docs.tigera.io/calico/charts")
    # Update the Helm repositories
    c.run("helm repo update")
    
    # Ensure the existing Installation resource has the correct annotations and labels
    installation_name = "default"  # replace with your actual installation name if different
    c.run(f"KUBECONFIG={kubeconfig} kubectl annotate installations.operator.tigera.io {installation_name} meta.helm.sh/release-name=calico meta.helm.sh/release-namespace=tigera-operator --overwrite")
    c.run(f"KUBECONFIG={kubeconfig} kubectl label installations.operator.tigera.io {installation_name} app.kubernetes.io/managed-by=Helm --overwrite")
    
    # Install the Calico operator
    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install --force --debug calico projectcalico/tigera-operator --namespace tigera-operator --create-namespace")
    print("Calico installed successfully")


@task
def deploy_calico(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    
        # Install a Pod network (e.g., Calico, Flannel)
    """Install Calico v3.28 on the Kubernetes cluster"""
    # Install the Tigera Calico operator and custom resource definitions
    c.sudo("kubectl apply --server-side --force-conflicts -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.1/manifests/tigera-operator.yaml")
    print("Tigera Calico operator installed successfully")

    # Install Calico by creating the necessary custom resource
    c.run(f"KUBECONFIG={kubeconfig} kubectl create --validate=false -f k8s/cluster/calico-custom-resources.yaml")
    print("Calico custom resources created successfully")

    # Monitor the status of Calico pods
    c.run("watch kubectl get pods -n calico-system")


@task
def deploy_traefik(c):
    """Deploy Traefik Ingress Controller to the Kubernetes cluster"""
    # Apply Traefik CRD and RBAC
    c.run("helm repo add traefik https://helm.traefik.io/traefik")
    c.run("helm repo update")
    kubeconfig = os.environ.get('KUBECONFIG')
    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install traefik traefik/traefik")
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
def get_kubeconfig(c):
    kubeconfig_path = os.getenv("KUBECONFIG")
    print(f"KUBECONFIG environment variable: {kubeconfig_path}")
    if kubeconfig_path:
        result = c.run(f"cat {kubeconfig_path}", hide=True)
        print(result.stdout)
    else:
        print("KUBECONFIG environment variable not set")

@task
def join_as_worker(c, skip_cert_verification=True):
    k8s_master_ip = os.getenv("K8S_JOIN_IP")
    k8s_token = os.getenv("K8S_JOIN_TOKEN")
    k8s_ca_cert_hash = os.getenv("K8S_CA_CERT_HASH", None)

    if not (k8s_master_ip and k8s_token):
        print("K8S_JOIN_IP and K8S_JOIN_TOKEN are required.")
        return

    join_command = f"kubeadm join {k8s_master_ip}:6443 --token {k8s_token} " \
                   f"{'--discovery-token-unsafe-skip-ca-verification' if skip_cert_verification else f'--discovery-token-ca-cert-hash {k8s_ca_cert_hash}' or ''}"

    c.sudo(join_command)


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


import os
from invoke import task

@task
def clean_containers(c):
    """Remove stale Kubernetes containers"""
    result = c.run("sudo docker ps -a | grep k8s", hide=True, warn=True)
    containers = result.stdout.splitlines()
    
    if not containers:
        print("No stale Kubernetes containers found.")
    else:
        for container in containers:
            container_id = container.split()[0]
            c.sudo(f"docker rm -f {container_id}")
        print("Stale Kubernetes containers removed.")

@task
def clean_network(c):
    """Clean up CNI configurations and reset IP tables"""
    c.sudo("rm -rf /etc/cni/net.d")
    c.sudo("iptables -F")
    c.sudo("iptables -t nat -F")
    c.sudo("ipvsadm --clear")
    print("Network configurations and IP tables reset.")

@task
def stop_kubelet(c):
    """Stop and disable kubelet service"""
    c.sudo("systemctl stop kubelet")
    c.sudo("systemctl disable kubelet")
    print("Kubelet service stopped and disabled.")

@task
def cleanup_kube_files(c):
    """Remove remaining Kubernetes configuration files"""
    c.sudo("rm -rf /etc/kubernetes/")
    c.sudo("rm -rf /var/lib/etcd/")
    c.sudo("rm -rf /var/lib/kubelet/")
    print("Kubernetes configuration files removed.")

@task
def restart_docker(c):
    """Restart Docker service"""
    c.sudo("systemctl restart docker")
    print("Docker service restarted.")

@task
def full_cleanup(c):
    """Perform full cleanup of stale Kubernetes resources and prepare environment"""
    clean_containers(c)
    clean_network(c)
    stop_kubelet(c)
    cleanup_kube_files(c)
    restart_docker(c)
    print("Full cleanup complete. Environment is ready for a new cluster setup.")
