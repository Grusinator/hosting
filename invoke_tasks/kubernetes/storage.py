import os

from invoke import task


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
