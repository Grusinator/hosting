

from invoke import task
from invoke_tasks.docker import check_docker_installed, start_docker


@task
def setup_master(ctx):
    """Initialize Docker Swarm on the master node and apply Terraform configuration."""
    check_docker_installed()
    start_docker()
    ctx.run("docker swarm init", warn=True)
    ctx.run("cd terraform && terraform init && terraform apply -auto-approve")