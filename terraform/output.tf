output "swarm_network_id" {
  value = module.docker-swarm.swarm_network_id
}

output "registry_url" {
  value = "localhost:5000"
}

output "prometheus_url" {
  value = "http://localhost:9090"
}

output "grafana_url" {
  value = "http://localhost:3000"
}

