import os
from dotenv import load_dotenv
from invoke import task

load_dotenv()


@task
def deploy_nginx(c):
    """Deploy Nginx with a custom configuration"""
    kubeconfig = os.getenv('KUBECONFIG')
    print(kubeconfig)
    # c.run("kubectl apply -f k8s/example_deployments/nginx/nginx-configmap.yaml")
    c.run(f"kubectl apply -f k8s/example_deployments/nginx/nginx-deployment.yaml")
    c.run(f"kubectl apply -f k8s/example_deployments/nginx/nginx-service.yaml")
    c.run(f"kubectl apply -f k8s/example_deployments/nginx/nginx-ingress.yaml")
    print("Nginx deployed successfully")


@task
def delete_nginx(c):
    """Delete the Nginx deployment"""
    c.run("kubectl delete -f nginx-ingress.yaml")
    c.run("kubectl delete -f nginx-service.yaml")
    c.run("kubectl delete -f nginx-deployment.yaml")
    # c.run("kubectl delete -f nginx-configmap.yaml")
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
