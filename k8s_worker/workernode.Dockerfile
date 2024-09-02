# Use Ubuntu 24.04 as the base image
FROM ubuntu:24.04

# Install necessary packages
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    open-iscsi \
    sudo \
    containerd

# Create the directory for APT keyrings if it doesn't exist
RUN mkdir -p /etc/apt/keyrings

# Download the public signing key for Kubernetes repository
RUN curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/k8s.gpg

# Add the Kubernetes APT repository
RUN echo 'deb [signed-by=/etc/apt/keyrings/k8s.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list

# Install Kubernetes components
RUN apt-get update && apt-get install -y kubelet kubeadm kubectl

# Prevent apt-get upgrade from upgrading kubelet, kubeadm, and kubectl
RUN apt-mark hold kubelet kubeadm kubectl

# Install CNI plugins
RUN mkdir -p /opt/cni/bin && \
    curl -L https://github.com/containernetworking/plugins/releases/download/v1.1.1/cni-plugins-linux-amd64-v1.1.1.tgz | tar -C /opt/cni/bin -xz

# Copy the CNI configuration file
COPY 10-bridge.conf /etc/cni/net.d/10-bridge.conf

# Copy a predefined containerd config.toml
COPY config.toml /etc/containerd/config.toml

# Start containerd and ensure it's ready before running the join command
ENTRYPOINT ["/bin/sh", "-c", "containerd & while [ ! -S /var/run/containerd/containerd.sock ]; do sleep 1; done; kubelet & eval $K8S_JOIN_COMMAND && tail -f /dev/null"]
