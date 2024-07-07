resource "docker_volume" "prometheus_data" {
  name = "prometheus-data"
}

resource "docker_service" "prometheus" {
  name    = "prometheus"
  image   = "prom/prometheus"
  networks = [docker_network.swarm_network_id]
  ports {
    target_port    = 9090
    published_port = 9090
  }
  volumes {
    source = docker_volume.prometheus_data.name
    target = "/prometheus"
  }
}

resource "docker_volume" "grafana_data" {
  name = "grafana-data"
}

resource "docker_service" "grafana" {
  name    = "grafana"
  image   = "grafana/grafana"
  networks = [docker_network.swarm_network_id]
  ports {
    target_port    = 3000
    published_port = 3000
  }
  volumes {
    source = docker_volume.grafana_data.name
    target = "/var/lib/grafana"
  }
}
