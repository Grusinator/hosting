#!/bin/bash
# This script is used to setup a worker node on a bare metal linux machine

# Exit immediately if a command exits with a non-zero status
set -e



# Update and install necessary packages
sudo apt-get update && sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    sudo \
    containerd \
    docker.io \
    open-iscsi \ # longhorn dependency

apt install -y git

# Create the directory for APT keyrings if it doesn't exist
sudo mkdir -p /etc/apt/keyrings

# Download the public signing key for the Kubernetes repository
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/k8s.gpg

# install kubeadm, kubelet, and kubectl
echo 'deb [signed-by=/etc/apt/keyrings/k8s.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update && sudo apt-get install -y kubelet kubeadm kubectl

# Prevent apt-get upgrade from upgrading kubelet, kubeadm, and kubectl
sudo apt-mark hold kubelet kubeadm kubectl

# Install CNI plugins
sudo mkdir -p /opt/cni/bin
curl -L https://github.com/containernetworking/plugins/releases/download/v1.1.1/cni-plugins-linux-amd64-v1.1.1.tgz | sudo tar -C /opt/cni/bin -xz


# Clone the repo
git clone https://github.com/grusinator/hosting.git ~/hosting
cd ~/hosting/k8s_worker

# Load environment variables from a file on the disk
export K8S_JOIN_TOKEN=dummy-token
export K8S_JOIN_IP=192.168.32.13
export SKIP_CERT_VERIFICATION=true  # Set to false if you don't want to skip cert verification


# Copy the CNI configuration file (adjust the path as necessary)
sudo cp 10-bridge.conf /etc/cni/net.d/10-bridge.conf

# Copy a predefined containerd config.toml (adjust the path as necessary)
sudo cp config.toml /etc/containerd/config.toml


# Make the join script executable
sudo chmod +x join_worker.sh

# Execute the join worker script
bash join_worker.sh

echo "Worker node setup complete and joined to the Kubernetes cluster."
