import os
import subprocess

from invoke import task


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
