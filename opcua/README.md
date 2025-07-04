# 🏭 p1-shopfloor Kubernetes Setup (Local via Minikube)

This repository contains Kubernetes manifests to deploy [Node-RED](https://nodered.org/) and [MiCube](https://github.com/micube-dev) into a local Minikube cluster using Ingress, Persistent Volumes, and basic authentication for Node-RED.

---

## 📦 Contents

- `deployment.yaml`: Combined Kubernetes manifests for Node-RED and MiCube
- Namespace: `p1-shopfloor`
- Resources: PVCs, Secrets, Deployments, Services, Ingress
- Ingress hostnames: `nodered.example.com`, `micube.example.com`

---

## 🚀 Quick Start with Minikube

### 1. Start Minikube with Ingress

```bash
minikube start --addons=ingress
```

> 💡 This enables the NGINX ingress controller inside the cluster.

---

### 2. Apply Kubernetes Resources

```bash
kubectl apply -f deployment.yaml
```

This will:
- Create the namespace `p1-shopfloor`
- Deploy Node-RED and MiCube with persistent volumes
- Configure Ingress and expose apps via custom hostnames

---

### 3. Setup Hostname Resolution

Edit your local `/etc/hosts` file (or `C:\Windows\System32\drivers\etc\hosts` on Windows):

```plaintext
127.0.0.1 nodered.example.com
```

> This allows you to access your services via custom domains locally.

---

### 4. Run Minikube Tunnel (in a separate terminal)

```bash
minikube tunnel
```

> This forwards LoadBalancer and Ingress traffic to your local machine.

---

### 5. Access the Applications

- 🌐 Node-RED: http://nodered.example.com

---

## 🔐 Node-RED Authentication

- **Username:** `admin`
- **Password:** (bcrypt hashed in `nodered-secret`)

To generate a new bcrypt password hash:

```bash
node -e "console.log(require('bcryptjs').hashSync('yourpassword', 8))"
```

To update the secret:

```bash
kubectl -n p1-shopfloor create secret generic nodered-secret \
  --from-literal=username=admin \
  --from-literal=password='<bcrypt-hash>' \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 🧪 Health Checks

Both apps have:

- **Readiness Probes** – App is ready to receive traffic
- **Liveness Probes** – App is healthy and responsive

---

## 🗂 Persistent Storage

Each app stores data in a persistent volume:

- Node-RED: `/data`

Both use 1Gi `PersistentVolumeClaim`s bound by default dynamic provisioning (via Minikube's hostPath).

---

## 🛠️ Cleanup

To delete all resources:

```bash
kubectl delete -f deployment.yaml
```

To stop Minikube:

```bash
minikube stop
```

---

## 📋 Requirements

- [Minikube](https://minikube.sigs.k8s.io/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- Node.js (optional, for bcrypt hash generation)

---


## 🔌 OPC UA Servers

Two OPC UA-compatible servers are deployed as part of this setup:

- `opcua-server` (default port: **4840**)
- `edge-server` (default port: **4844**)

### 🔄 Port Forwarding for Local Testing

You can forward their ports to your local machine for testing using the following commands:

```bash
# Forward OPC UA Server (port 4840)
kubectl port-forward -n p1-shopfloor pod/opcua-server-xxxxx 4840:4840

# Forward Edge Server (port 4844)
kubectl port-forward -n p1-shopfloor pod/edge-server-xxxxx 4844:4844
```

You can connect to the server using any OPC UA client. The server endpoints are:

```bash
opc.tcp://localhost:4840/freeopcua/server/
```

```bash
opc.tcp://localhost:4844
```

For testing purposes, you can use tools like:
- UaExpert (https://www.unified-automation.com/products/development-tools/uaexpert.html)
- Python-based clients using the asyncua library
- Node-Red Ingestion

---

## 📌 Known Limitations

- TLS is not enabled; use `cert-manager` + `mkcert` if needed
- Hostnames require editing `/etc/hosts`
- MiCube image assumes public container available at `ghcr.io/micube/micube:latest`

---

## ✅ Future Improvements

- Add support for HTTPS with cert-manager
- Integrate logging/monitoring (Prometheus + Grafana)
- Add Helm chart for easier reuse
