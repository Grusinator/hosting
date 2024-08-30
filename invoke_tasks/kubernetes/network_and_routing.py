import os

from invoke import task


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
    domain = os.getenv('DOMAIN')
    c.run("helm repo add traefik https://helm.traefik.io/traefik")
    c.run("helm repo update")
    kubeconfig = os.environ.get('KUBECONFIG')
    c.run(f"""
        KUBECONFIG={kubeconfig} helm upgrade --install traefik traefik/traefik \
        --namespace kube-system --create-namespace \
        --set ingress.enabled=true \
        --set ingress.hosts[0]=traefik.{domain} \
        --set ingress.annotations."traefik\.ingress\.kubernetes\.io/router\.entrypoints"=web \
        --set ingress.paths[0]=/ \
        --set ingress.pathType=Prefix
    """)
    print("Traefik Ingress Controller installed successfully")
