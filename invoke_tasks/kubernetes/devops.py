import os

from invoke import task


@task
def deploy_harbor(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    admin_password = os.getenv("ADMIN_PASSWORD")
    domain = os.getenv("DOMAIN")

    """Deploy Harbor container registry to the Kubernetes cluster"""
    # Add the Harbor Helm repository
    c.run("helm repo add harbor https://helm.goharbor.io")
    c.run("helm repo update")

    # Deploy Harbor
    c.run(f"""
    KUBECONFIG={kubeconfig} helm upgrade --install harbor harbor/harbor \
        --namespace harbor --create-namespace \
        --set expose.type=ingress \
        --set expose.ingress.hosts.core={domain} \
        --set externalURL=https://{domain} \
        --set persistence.enabled=true \
        --set harborAdminPassword={admin_password} \
        --timeout 600s
    """)

    print("Harbor deployment initiated. This may take several minutes to complete.")
    print("You can check the status of the deployment with:")
    print(f"kubectl --namespace harbor get pods -w")
    print(f"\nOnce deployed, you can access Harbor at: https://harbor.{domain}")
    print("Default credentials are:")
    print("Username: admin")
    print(f"Password: {admin_password}")
    print("Please change the password after first login.")



@task
def deploy_dokku(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    """Deploy Dokku to the Kubernetes cluster"""
    # Add the Dokku Helm repository
    c.run("helm repo add dokku https://dokku.github.io/dokku")
    c.run("helm repo update")

    # Deploy Dokku
    c.run(f"""
    KUBECONFIG={kubeconfig} helm upgrade --install dokku dokku/dokku \
        --namespace dokku --create-namespace \
        --set service.type=LoadBalancer \
        --set service.annotations."external-dns\\.alpha\\.kubernetes\\.io/hostname"=dokku.wsh-it.dk \
        --set ingress.enabled=true \
        --set ingress.annotations."kubernetes\\.io/ingress\\.class"=traefik \
        --set ingress.hosts[0].host=dokku.wsh-it.dk \
        --set ingress.hosts[0].paths[0].path=/ \
        --set persistence.enabled=true \
        --timeout 600s
    """)

    print("Dokku deployment initiated. This may take several minutes to complete.")
    print("You can check the status of the deployment with:")
    print("kubectl --namespace dokku get pods -w")
    print("\nOnce deployed, you can access Dokku at: https://dokku.wsh-it.dk")
    print("To use Dokku, you'll need to set up SSH access and configure your local Dokku CLI.")
    print("Refer to the Dokku documentation for post-installation steps and usage instructions.")


@task
def deploy_gitlab(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    """Deploy GitLab to the Kubernetes cluster using Helm"""
    # Add the GitLab Helm repository
    c.run("helm repo add gitlab https://charts.gitlab.io/")
    c.run("helm repo update")

    admin_email = os.getenv("ADMIN_EMAIL")
    # Deploy GitLab
    c.run(f"""
    KUBECONFIG={kubeconfig} helm upgrade --install gitlab gitlab/gitlab \
        --namespace gitlab --create-namespace \
        --set global.hosts.domain=gitlab.wsh-it.dk \
        --set certmanager-issuer.email={admin_email} \
         --set gitlab-runner.runners.privileged=true \
        --set gitlab-runner.runners.config.cache.type=s3 \
        --set gitlab-runner.runners.config.cache.s3.serverAddress=minio.gitlab.svc.cluster.local \
        --set gitlab-runner.runners.config.cache.s3.bucketName=runner-cache \
        --set gitlab-runner.runners.config.cache.s3.insecure=true \
        --timeout 600s
    """)

    print("GitLab deployment initiated. This may take several minutes to complete.")
    print("You can check the status of the deployment with:")
    print("kubectl --namespace gitlab get pods -w")


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
