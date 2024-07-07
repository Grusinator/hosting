resource "docker_volume" "registry_data" {
  name = "registry-data"
}

resource "docker_service" "registry" {
  name    = "registry"
  image   = "registry:2"
  networks = [docker_network.swarm_network_id]
  ports {
    target_port    = 5000
    published_port = 5000
  }
  volumes {
    source = docker_volume.registry_data.name
    target = "/var/lib/registry"
  }
}
