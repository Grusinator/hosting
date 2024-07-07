terraform {
  required_providers {
    rancher2 = {
      source  = "rancher/rancher2"
      version = "~> 1.15"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 2.13"
    }
  }
}

provider "rancher2" {
  api_url   = var.rancher_api_url
  token_key = var.rancher_api_token
}

provider "docker" {}

variable "rancher_api_url" {
  description = "Rancher API URL"
}

variable "rancher_api_token" {
  description = "Rancher API token"
}

variable "swarm_manager_ip" {
  description = "Swarm manager IP address"
}

variable "swarm_token" {
  description = "Swarm token for joining nodes"
}

module "docker-swarm" {
  source = "./modules/docker-swarm"
}

module "docker-registry" {
  source = "./modules/docker-registry"
}

module "monitoring" {
  source = "./modules/monitoring"
}

module "rancher" {
  source = "./modules/rancher"
}
