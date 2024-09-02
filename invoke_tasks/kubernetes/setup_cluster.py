import os
import platform
from pathlib import Path
from invoke import task

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
def get_kubeconfig(c):
    kubeconfig_path = os.getenv("KUBECONFIG")
    print(f"KUBECONFIG environment variable: {kubeconfig_path}")
    if kubeconfig_path:
        with open(kubeconfig_path, 'r') as file:
            print(file.read())
    else:
        print("KUBECONFIG environment variable not set")

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
def clean_namespace(c, namespace):
    kubeconfig = os.environ.get('KUBECONFIG')

    print(f"Cleaning up namespace: {namespace}")

    resource_types = [
        "deployments",
        "services",
        "daemonsets",
        "statefulsets",
        "replicasets",
        "pods",
        "configmaps",
        "secrets",
        "serviceaccounts",
        "persistentvolumeclaims",
        "ingresses",
        "roles",
        "rolebindings",
        "clusterrolebindings"  # Be careful with cluster-wide resources
    ]

    for resource in resource_types:
        print(f"Deleting {resource} in {namespace}...")
        c.run(f"KUBECONFIG={kubeconfig} kubectl delete {resource} --all -n {namespace} --ignore-not-found", warn=True)

    print(f"Namespace {namespace} cleaned up.")



@task
def delete_cluster(c, name="my-cluster"):
    """Delete the Kubernetes cluster"""

    # Tear down the cluster
    c.sudo("kubeadm reset -f")
    c.sudo("rm -rf ~/.kube/config")
    print(f"Cluster '{name}' deleted successfully")


@task
def start_worker_in_docker(c):
    path = "k8s_worker/docker-compose-k8s-worker.yaml"
    c.run(f"docker-compose -f {path} up --build")


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
def generate_join_command(c):
    # Set the kubeconfig path if necessary
    kubeconfig = os.getenv('KUBECONFIG')

    # Generate the join command using kubeadm
    result = c.sudo(f"KUBECONFIG={kubeconfig} kubeadm token create --print-join-command", hide=True)

    # Extract the join command
    join_command = result.stdout.strip()

    if join_command:
        print("Kubernetes Join Command:")
        print(join_command)
    else:
        print("Error: Unable to generate the join command.")


