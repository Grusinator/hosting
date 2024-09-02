from invoke import task
import os

@task
def deploy_ollama(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    namespace = "ollama"

    print("Deploying Ollama Server...")
    c.run("helm repo add ollama-helm https://otwld.github.io/ollama-helm/")
    c.run("helm repo update ollama-helm")

    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install ollama ollama-helm/ollama --namespace {namespace} --create-namespace \
           --set ollama.gpu.enabled=false \
           --set ollama.models[0]=llama3.1 \
           --set service.type=LoadBalancer")


@task
def deploy_open_webui(c):
    kubeconfig = os.environ.get('KUBECONFIG')
    namespace = "ollama"

    print("Deploying Open WebUI...")
    c.run("helm repo add open-webui https://helm.openwebui.com/")
    c.run("helm repo update")
    c.run(f"KUBECONFIG={kubeconfig} helm upgrade --install open-webui open-webui/open-webui --namespace {namespace} --create-namespace")

