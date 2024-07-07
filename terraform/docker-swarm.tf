resource "docker_network" "swarm_network" {
  name = "swarm_network"
}

resource "docker_service" "swarm_manager" {
  name    = "swarm_manager"
  image   = "docker:latest"
  networks = [docker_network.swarm_network.id]
}

resource "docker_service" "swarm_worker" {
  count   = 2
  name    = "swarm_worker_${count.index}"
  image   = "docker:latest"
  networks = [docker_network.swarm_network.id]
}

output "swarm_network_id" {
  value = docker_network.swarm_network.id
}
