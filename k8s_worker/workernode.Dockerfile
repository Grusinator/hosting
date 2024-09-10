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
    containerd \
    iptables \
    software-properties-common  # Install this package for add-apt-repository command

# Set up Docker repository and install the latest Docker
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - \
    && add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    && apt-get update \
    && apt-get install -y docker-ce docker-ce-cli containerd.io \
    && apt-get clean

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

# Copy the kubelet configuration file
COPY kubelet-config.yaml /etc/kubelet/kubelet-config.yaml

# Create /etc/docker directory if it doesn't exist and set the storage driver to overlay2
RUN mkdir -p /etc/docker && \
    echo '{"data-root": "/var/lib/docker-alt", "storage-driver": "overlay2"}' > /etc/docker/daemon.json


# Add the 'docker' group if it doesn't exist and add the root user to the 'docker' group
RUN getent group docker || groupadd docker && \
    usermod -aG docker root

# Copy the start script
COPY start.sh /usr/local/bin/start.sh

# Make the script executable
RUN chmod +x /usr/local/bin/start.sh

# Expose Docker socket
VOLUME /var/lib/docker
EXPOSE 2375

# Use the script as the entrypoint
ENTRYPOINT ["/usr/local/bin/start.sh"]

