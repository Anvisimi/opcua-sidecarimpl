# 🔍 Deployment Comparison: Existing vs Enhanced OPC UA

This document provides a detailed comparison to ensure **complete separation** between your existing and enhanced OPC UA deployments.

## 📊 Resource Comparison

### Kubernetes Resources

| Resource Type | Existing Deployment | Enhanced Deployment | Conflict Risk |
|---------------|-------------------|-------------------|---------------|
| **Deployment Name** | `opcua-server` | `enhanced-opcua-server` | ✅ **None** |
| **Service Name** | `opcua-service` | `enhanced-opcua-service` | ✅ **None** |
| **Pod Labels** | `app: opcua-server` | `app: enhanced-opcua-server` | ✅ **None** |
| **Namespace** | `p1-shopfloor` | `p1-shopfloor` | ✅ **Shared (intended)** |

### Container Details

| Aspect | Existing | Enhanced |
|--------|----------|----------|
| **Container Count** | 1 container | 2 containers (main + sidecar) |
| **Container Names** | `opcua-server` | `enhanced-opcua-server`, `data-sidecar` |
| **Docker Images** | `yathu25/opcua-server:latest` | `yathu25/enhanced-opcua-server:latest`<br/>`yathu25/data-sidecar:latest` |
| **Port Exposure** | `4840` | `4840` (different service selector) |

### Data Sources

| Aspect | Existing | Enhanced |
|--------|----------|----------|
| **Data Source** | Single embedded file: `M01_Aug_2019_OP00_000.h5` | All files from host `/data` folder |
| **Volume Mounts** | None (file embedded in image) | 2 volumes: source-data + shared-data |
| **File Management** | Static | Dynamic with sidecar |

## 🛡️ Safety Guarantees

### ✅ **What's Safe**
- **Different selectors**: Services target different pods
- **Different names**: No naming conflicts
- **Different images**: Completely separate container images
- **Different data**: Existing uses embedded file, enhanced uses host data
- **Independent lifecycles**: Can deploy/delete independently

### ⚠️ **What to Monitor**
- **Resource usage**: Both deployments will consume CPU/memory
- **Port forwarding**: Use different local ports when testing both
- **Data access**: Enhanced deployment reads from host data folder

## 🚀 Deployment Commands

### Deploy Existing (Original Setup)
```bash
kubectl apply -f opcua/opcuaDeployment.yaml
kubectl apply -f opcua/opcuaService.yaml
```

### Deploy Enhanced (New Multi-File Setup)
```bash
./build-and-deploy.sh
```

### Verify Both Are Running
```bash
./verify-deployments.sh
```

## 🔌 Access Methods

### Access Existing OPC UA Server
```bash
kubectl port-forward -n p1-shopfloor service/opcua-service 4840:4840
# Connect to: opc.tcp://localhost:4840/
```

### Access Enhanced OPC UA Server
```bash
kubectl port-forward -n p1-shopfloor service/enhanced-opcua-service 4841:4840
# Connect to: opc.tcp://localhost:4841/
```

## 📋 Verification Checklist

Run these commands to verify complete separation:

```bash
# 1. Check both deployments exist and are separate
kubectl get deployments -n p1-shopfloor | grep opcua

# 2. Check both services exist and are separate  
kubectl get services -n p1-shopfloor | grep opcua

# 3. Check pods are using different labels
kubectl get pods -n p1-shopfloor -l app=opcua-server
kubectl get pods -n p1-shopfloor -l app=enhanced-opcua-server

# 4. Verify no resource conflicts
kubectl describe deployment opcua-server -n p1-shopfloor
kubectl describe deployment enhanced-opcua-server -n p1-shopfloor
```

## 🎯 Expected Output

When both deployments are running successfully:

```bash
$ kubectl get deployments -n p1-shopfloor | grep opcua
opcua-server           1/1     1            1           X days
enhanced-opcua-server  1/1     1            1           X minutes

$ kubectl get services -n p1-shopfloor | grep opcua  
opcua-service           ClusterIP   10.X.X.X   <none>        4840/TCP    X days
enhanced-opcua-service  ClusterIP   10.X.X.X   <none>        4840/TCP    X minutes

$ kubectl get pods -n p1-shopfloor | grep opcua
opcua-server-xxxxx            1/1     Running   0          X days
enhanced-opcua-server-xxxxx   2/2     Running   0          X minutes
```

## ✅ Conclusion

The enhanced deployment is **completely isolated** from your existing deployment. You can:

- **Deploy both simultaneously** ✅
- **Access both independently** ✅  
- **Delete one without affecting the other** ✅
- **Scale each independently** ✅
- **Update each independently** ✅

**No conflicts will occur between the two deployments.** 