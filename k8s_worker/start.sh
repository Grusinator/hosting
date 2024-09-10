#!/bin/sh
set -e

# Start Docker daemon in the background
/usr/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://0.0.0.0:2375 --storage-driver=overlay2 --data-root=/var/lib/docker-alt &

# Wait until Docker daemon is ready
while (! docker info > /dev/null 2>&1); do
  echo "Waiting for Docker to start..."
  sleep 10
done

echo "Docker started successfully"

# Start containerd
containerd &

# Wait for containerd to be ready
while [ ! -S /var/run/containerd/containerd.sock ]; do
    sleep 1
done

# Start kubelet
kubelet --config=/etc/kubelet/kubelet-config.yaml &

eval $K8S_JOIN_COMMAND

# Ensure the script does not exit immediately
tail -f /dev/null
