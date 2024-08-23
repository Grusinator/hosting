from invoke import Collection
from invoke_tasks import docker, kubernetes, docker_swarm, terraform

# Create collections from modules
ns = Collection()
ns.add_collection(Collection.from_module(docker))
ns.add_collection(Collection.from_module(kubernetes), name="k8s")
ns.add_collection(Collection.from_module(docker_swarm), name='swarm')
ns.add_collection(Collection.from_module(terraform), name='tf')