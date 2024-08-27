#!/bin/bash

# Disable swap
sudo swapoff -a

# Prevent swap from being enabled on reboot
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Start containerd in the background
sudo containerd &

# Wait for containerd to be fully up and running
sleep 5

set -e

# Get environment variables
K8S_MASTER_IP=${K8S_JOIN_IP}
K8S_TOKEN=${K8S_JOIN_TOKEN}
K8S_CA_CERT_HASH=${K8S_CA_CERT_HASH}
SKIP_CERT_VERIFICATION=${SKIP_CERT_VERIFICATION:-true}

if [[ -z "$K8S_MASTER_IP" || -z "$K8S_TOKEN" ]]; then
    echo "K8S_JOIN_IP and K8S_JOIN_TOKEN are required."
    exit 1
fi

JOIN_COMMAND="kubeadm join ${K8S_MASTER_IP}:6443 --token ${K8S_TOKEN}"

if [[ "$SKIP_CERT_VERIFICATION" == "true" ]]; then
    JOIN_COMMAND+=" --discovery-token-unsafe-skip-ca-verification"
else
    if [[ -z "$K8S_CA_CERT_HASH" ]]; then
        echo "K8S_CA_CERT_HASH is required unless SKIP_CERT_VERIFICATION is set to true."
        exit 1
    fi
    JOIN_COMMAND+=" --discovery-token-ca-cert-hash ${K8S_CA_CERT_HASH}"
fi

# Add preflight error ignore options
JOIN_COMMAND+=" --ignore-preflight-errors=all"

# Run the join command
sudo $JOIN_COMMAND

# Keep the container running
tail -f /dev/null

