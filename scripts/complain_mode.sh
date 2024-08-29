#!/bin/bash

# List of profiles to put in complain mode
profiles=(
  "/usr/sbin/cups-browsed"
  "/usr/sbin/cupsd"
  "/usr/local/bin/etcd"
  "/usr/local/bin/kube-scheduler"
  "/usr/local/bin/kube-apiserver"
  "/usr/local/bin/kube-controller-manager"
  "/bin/node_exporter"
  "/usr/bin/operator"
  "/kube-state-metrics"
  "/usr/local/bin/traefik"
  "/bin/pushgateway"
  "/usr/bin/kube-controllers"
  "/usr/share/grafana/bin/grafana"
  "/coredns"
  "/usr/bin/bash"
  "/usr/sbin/nginx"
  "/usr/local/sbin/longhorn-manager"
  "/csi-resizer"
  "/csi-provisioner"
  "/csi-snapshotter"
  "/csi-attacher"
  "/livenessprobe"
  "/bin/prometheus-config-reloader"
  "/bin/alertmanager"
  "/bin/prometheus"
  "/usr/bin/sleep"
)

# Put each profile in complain mode
for profile in "${profiles[@]}"; do
  sudo aa-complain "$profile"
done

echo "All profiles set to complain mode."
