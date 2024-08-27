# Use Ubuntu 24.04 as the base image
FROM ubuntu:24.04

# Install necessary packages
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    sudo \
    containerd

# Create the directory for APT keyrings if it doesn't exist
RUN mkdir -p /etc/apt/keyrings

# Download the public signing key for Kubernetes repository
RUN curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/k8s.gpg

# Add the Kubernetes APT repository
RUN echo 'deb [signed-by=/etc/apt/keyrings/k8s.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

# Install Kubernetes components
RUN apt-get update && apt-get install -y kubelet kubeadm kubectl

# Prevent apt-get upgrade from upgrading kubelet, kubeadm, and kubectl
RUN apt-mark hold kubelet kubeadm kubectl

# Install CNI plugins
RUN mkdir -p /opt/cni/bin && \
    curl -L https://github.com/containernetworking/plugins/releases/download/v1.1.1/cni-plugins-linux-amd64-v1.1.1.tgz | sudo tar -C /opt/cni/bin -xz

# Copy a predefined containerd config.toml
COPY config.toml /etc/containerd/config.toml

# Copy the join script into the container
COPY join_worker.sh /usr/local/bin/join_worker.sh

# Make the script executable
RUN chmod +x /usr/local/bin/join_worker.sh


# Set the entrypoint to the join script
ENTRYPOINT ["/usr/local/bin/join_worker.sh"]
