import os

from invoke import task

@task
def deploy_harbor(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    admin_password = os.getenv("ADMIN_PASSWORD")
    domain = os.getenv("DOMAIN")
    harbor_domain = f"harbor.{domain}"

    """Deploy Harbor container registry to the Kubernetes cluster"""
    # Add the Harbor Helm repository
    c.run("helm repo add harbor https://helm.goharbor.io")
    c.run("helm repo update")

    # Deploy Harbor
    c.run(f"""
    KUBECONFIG={kubeconfig} helm upgrade --install harbor harbor/harbor \
        --namespace harbor --create-namespace \
        --set expose.type=ingress \
        --set expose.ingress.hosts.core={harbor_domain} \
        --set externalURL=https://{harbor_domain} \
        --set persistence.enabled=true \
        --set harborAdminPassword={admin_password} \
        --timeout 600s
    """)

    print("Harbor deployment initiated. This may take several minutes to complete.")
    print("You can check the status of the deployment with:")
    print(f"kubectl --namespace harbor get pods -w")
    print(f"\nOnce deployed, you can access Harbor at: https://{harbor_domain}")
    print("Default credentials are:")
    print("Username: admin")
    print(f"Password: {admin_password}")
    print("Please change the password after first login.")



@task
def deploy_docker_registry(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    domain = os.getenv("DOMAIN", "yourdomain.com")
    registry_domain = f"registry.{domain}"

    """Deploy Docker Registry to the Kubernetes cluster"""
    c.run("helm repo add twuni https://helm.twun.io")
    c.run("helm repo update")

    c.run(f"""
    KUBECONFIG={kubeconfig} helm upgrade --install docker-registry twuni/docker-registry \
        --namespace container-registry --create-namespace \
        --set service.type=ClusterIP \
        --set ingress.enabled=true \
        --set ingress.hosts[0].host={registry_domain} \
        --set ingress.hosts[0].paths[0].path=/ \
        --set ingress.hosts[0].paths[0].pathType=Prefix \
        --set persistence.enabled=true \
        --set persistence.size=10Gi \
        --timeout 600s
    """)

    print("Docker Registry deployment initiated. This may take several minutes to complete.")
    print("You can check the status of the deployment with:")
    print("kubectl --namespace container-registry get pods -w")
    print(f"\nOnce deployed, you can access the Docker Registry at: https://{registry_domain}")


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
    # Define the runners config as a multiline string
    runners_config = """[[runners]]
  [runners.kubernetes]
    privileged = true
    image = "ubuntu:22.04"
  [runners.cache]
    Type = "s3"
    Path = "gitlab-runner"
    Shared = true
    [runners.cache.s3]
      ServerAddress = "minio.gitlab.svc.cluster.local"
      BucketName = "runner-cache"
      Insecure = true
    """

    # Deploy GitLab
    c.run(f"""
    KUBECONFIG={kubeconfig} helm upgrade --install gitlab gitlab/gitlab \
        --namespace gitlab --create-namespace \
        --set global.hosts.domain=gitlab.wsh-it.dk \
        --set certmanager-issuer.email={admin_email} \
        --set gitlab-runner.runners.privileged=true \
        --set-string gitlab-runner.runners.config="{runners_config}" \
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


from invoke import task

@task
def deploy_vault(c):
    """Deploy HashiCorp Vault to the Kubernetes cluster using Helm."""

    # Path to your kubeconfig
    kubeconfig = os.environ.get('KUBECONFIG')

    # Add the HashiCorp Helm repository
    c.run("helm repo add hashicorp https://helm.releases.hashicorp.com")
    c.run("helm repo update")

    # Deploy Vault with hardcoded settings directly in the command
    c.run(f"""KUBECONFIG={kubeconfig} helm upgrade --install vault hashicorp/vault \
        --namespace vault --create-namespace \
        --set server.ha.enabled=true \
        --set server.ha.raft.enabled=true \
        --set server.ha.raft.storageClass=standard \
        --set server.ha.raft.setSize=3 \
        --set server.dataStorage.storageClass=standard \
        --set server.dataStorage.size=10Gi \
        --set server.service.type=LoadBalancer \
        --set server.storageBackend=raft \
        --timeout 600s
    """)

