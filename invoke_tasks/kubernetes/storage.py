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
