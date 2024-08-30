import os
from invoke import task

@task
def deploy_nginx(c, release_name="my-nginx", namespace="default"):
    """Deploy Nginx using local Helm chart"""
    kubeconfig = os.getenv('KUBECONFIG')
    print(f"Using KUBECONFIG: {kubeconfig}")
    
    # Deploy Nginx using local Helm chart
    c.run(f"helm upgrade --install {release_name} ./nginx-server "
          f"--namespace {namespace} "
          f"--set ingress.enabled=true "
          f"--set ingress.hosts[0].host=test-server.wsh-it.dk "
          f"--set ingress.hosts[0].paths[0].path=/ "
          f"--set ingress.hosts[0].paths[0].pathType=Prefix")
    
    print(f"Nginx deployed successfully using local Helm chart as '{release_name}' in namespace '{namespace}'")

@task
def delete_nginx(c, release_name="my-nginx", namespace="default"):
    """Delete the Nginx deployment using Helm"""
    c.run(f"helm uninstall {release_name} --namespace {namespace}")
    print(f"Nginx deployment '{release_name}' deleted from namespace '{namespace}'")

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
