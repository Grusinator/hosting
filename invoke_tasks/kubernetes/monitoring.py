import os
import subprocess

from invoke import task

import time


namespace = "monitoring"

@task
def deploy_prometheus(c):
    kubeconfig = os.environ.get('KUBECONFIG')

    print("Deploying Prometheus...")
    c.run("helm repo add prometheus-community https://prometheus-community.github.io/helm-charts")
    c.run("helm repo update prometheus-community")

    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install prometheus prometheus-community/prometheus --namespace {namespace} --create-namespace \
           --set server.persistentVolume.storageClass=longhorn \
           --set alertmanager.persistentVolume.storageClass=longhorn \
           --set pushgateway.persistentVolume.storageClass=longhorn")

    print("Prometheus deployed.")

@task
def deploy_grafana(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    admin_password = os.getenv("ADMIN_PASSWORD")

    print("Deploying Grafana...")
    c.run("helm repo add grafana https://grafana.github.io/helm-charts")
    c.run("helm repo update grafana")

    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install grafana grafana/grafana --namespace {namespace} --create-namespace \
           --set persistence.enabled=true \
           --set persistence.storageClassName=longhorn \
           --set persistence.size=10Gi \
           --set adminPassword='{admin_password}' \
           --set service.type=LoadBalancer \
           --set service.port=80")

    print("Grafana deployed.")


@task
def deploy_dashboard(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    admin_password = os.getenv("ADMIN_PASSWORD")
    namespace = "monitoring"

    print("Deploying Kubernetes Dashboard...")
    c.run("helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/")
    c.run("helm repo update kubernetes-dashboard")

    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard --namespace {namespace} --create-namespace \
           --set extraArgs[0]='--authentication-mode=basic' \
           --set extraArgs[1]='--token-ttl=0' \
           --set extraEnv[0].name='KUBERNETES_DASHBOARD_USERNAME' \
           --set extraEnv[0].value='admin' \
           --set extraEnv[1].name='KUBERNETES_DASHBOARD_PASSWORD' \
           --set extraEnv[1].value='{admin_password}' \
           --set service.type=LoadBalancer")

    print("Kubernetes Dashboard deployed.")

    print("Checking if Service Account exists...")
    sa_exists = c.run(f"KUBECONFIG={kubeconfig} kubectl get serviceaccount dashboard-admin-sa -n {namespace} --ignore-not-found", warn=True, hide=True).stdout.strip()

    if not sa_exists:
        print("Service Account does not exist. Creating Service Account...")
        c.run(f"KUBECONFIG={kubeconfig} kubectl create serviceaccount dashboard-admin-sa -n {namespace}")
        c.run(f"KUBECONFIG={kubeconfig} kubectl create clusterrolebinding dashboard-admin-sa-binding --clusterrole=cluster-admin --serviceaccount={namespace}:dashboard-admin-sa")
    else:
        print("Service Account already exists. Skipping creation.")

    print("Fetching Service Account Token...")
    time.sleep(5)  # Wait a few seconds to ensure the secret is created

    secret_name = c.run(f"KUBECONFIG={kubeconfig} kubectl get secrets -n {namespace} | grep dashboard-admin-sa | awk '{{print $1}}'", hide=True).stdout.strip()

    if secret_name:
        token = c.run(f"KUBECONFIG={kubeconfig} kubectl get secret {secret_name} -n {namespace} -o jsonpath={{.data.token}} | base64 --decode", hide=True).stdout.strip()
        print(f"Service Account Token: {token}")
    else:
        print("Error: Service account token secret not found.")

    print(f"Admin user: admin")
    print(f"Admin password: {admin_password}")


@task
def deploy_monitoring_stack(c):
    deploy_prometheus(c)
    deploy_grafana(c)
    deploy_dashboard(c)


@task
def remove_dashboard(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    namespace = "monitoring"

    print("Removing old Kubernetes Dashboard deployment if it exists...")
    c.run(f"KUBECONFIG={kubeconfig} kubectl delete deployment kubernetes-dashboard -n {namespace} --ignore-not-found", warn=True)
    c.run(f"KUBECONFIG={kubeconfig} kubectl delete service kubernetes-dashboard -n {namespace} --ignore-not-found", warn=True)
    c.run(f"KUBECONFIG={kubeconfig} kubectl delete serviceaccount dashboard-admin-sa -n {namespace} --ignore-not-found", warn=True)
    c.run(f"KUBECONFIG={kubeconfig} kubectl delete clusterrolebinding dashboard-admin-sa-binding --ignore-not-found", warn=True)




@task
def get_prometheus_grafana_password(c):
    kubeconfig = os.environ.get('KUBECONFIG')
        # Get the Grafana admin password
    password_command = f"KUBECONFIG={kubeconfig} kubectl get secret --namespace {namespace} grafana -o jsonpath=\"{{.data.admin-password}}\" | base64 --decode"
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
def deploy_teleport(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    namespace = "teleport"
    cluster_name = "kubernetes-teleport"

    print("Deploying Teleport Server...")
    c.run("helm repo add teleport https://charts.releases.teleport.dev")
    c.run("helm repo update")

    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install teleport teleport/teleport-cluster --namespace {namespace} --create-namespace \
           --set clusterName={cluster_name} \
           --set proxyService.type=LoadBalancer \
           --set authService.enabled=true \
           --set proxyService.enabled=true \
           --set kubeService.enabled=true")

