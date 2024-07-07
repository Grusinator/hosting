data "rancher2_cluster" "my_cluster" {
  name = "your-cluster-name"
}

resource "rancher2_project" "my_project" {
  name       = "default"
  cluster_id = data.rancher2_cluster.my_cluster.id
}

resource "rancher2_namespace" "example_ns" {
  name       = "example"
  project_id = rancher2_project.my_project.id
}
