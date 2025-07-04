# 🏭 Enhanced Multi-File OPC UA Server with Sidecar Pattern

> **⚠️ IMPORTANT**: This creates a **NEW deployment** that runs **alongside** your existing OPC UA server without interfering with it.

This enhanced setup extends your existing single-file OPC UA server to stream data from **all files** in the `/data` folder using a **Kubernetes sidecar container pattern**.

## 🛡️ **Deployment Independence**

| Resource | Existing | Enhanced | Status |
|----------|----------|----------|---------|
| **Deployment** | `opcua-server` | `enhanced-opcua-server` | ✅ **No Conflict** |
| **Service** | `opcua-service` | `enhanced-opcua-service` | ✅ **No Conflict** |
| **Images** | `yathu25/opcua-server:latest` | `yathu25/enhanced-opcua-server:latest`<br/>`yathu25/data-sidecar:latest` | ✅ **No Conflict** |

**Both deployments can run simultaneously in the same namespace!**

## 📋 Overview

### Current vs Enhanced Setup

| Aspect | Current Setup | Enhanced Setup |
|--------|---------------|----------------|
| **Data Source** | Single file: `M01_Aug_2019_OP00_000.h5` | All files in `/data` folder |
| **Machines** | M01 only | M01, M02 (M03 excluded per requirements) |
| **Operations** | OP00 only | All operations except OP00, OP06, OP09, OP13 |
| **Architecture** | Single container | Sidecar pattern with 2 containers |
| **File Management** | Static | Dynamic file rotation |
| **Streaming Rate** | 10 samples/second | **10 samples/second (maintained)** |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Pod                           │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │   Data Sidecar  │    │   Enhanced OPC UA Server       │  │
│  │                 │    │                                 │  │
│  │ • File Discovery│    │ • Reads from shared volume     │  │
│  │ • Copy to shared│────│ • Multi-file streaming        │  │
│  │ • Create manifest│   │ • File rotation                │  │
│  │ • Monitor changes│   │ • 10 streams/second            │  │
│  └─────────────────┘    └─────────────────────────────────┘  │
│           │                           │                     │
│           │                           │                     │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │  Source Data    │    │        Shared Volume            │  │
│  │  (Host Path)    │    │      (EmptyDir)                 │  │
│  │                 │    │                                 │  │
│  │ /data/M01/...   │    │ • Copied HDF5 files            │  │
│  │ /data/M02/...   │    │ • file_manifest.json           │  │
│  └─────────────────┘    └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **Existing Setup**: Your current OPC UA server should be working
2. **Kubernetes**: Minikube or any Kubernetes cluster
3. **Docker**: For building container images
4. **Data Access**: `/data` folder accessible from Kubernetes

### Step 1: Build and Deploy

```bash
# Make the script executable
chmod +x build-and-deploy.sh

# Run the automated build and deployment
./build-and-deploy.sh
```

### Step 2: Verify Deployment

```bash
# Check pod status
kubectl get pods -n p1-shopfloor -l app=enhanced-opcua-server

# View logs
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c data-sidecar
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c enhanced-opcua-server
```

### Step 3: Verify Both Deployments

```bash
# Run verification script to check both deployments
./verify-deployments.sh
```

### Step 4: Access OPC UA Servers

```bash
# Access existing OPC UA server (if deployed)
kubectl port-forward -n p1-shopfloor service/opcua-service 4840:4840

# Access enhanced OPC UA server (different port to avoid conflicts)
kubectl port-forward -n p1-shopfloor service/enhanced-opcua-service 4841:4840

# Connect using OPC UA client
# Existing:  opc.tcp://localhost:4840/
# Enhanced:  opc.tcp://localhost:4841/
```

## 💾 Volume Structure

The sidecar pattern uses **two volumes** for data management:

### **Source Data Volume** (Host Path)
- **Path**: `/Users/inderpreet/Documents/sidecar_impl/opcua-server/data`
- **Purpose**: Mount your original data folder (read-only)
- **Contains**: Original HDF5 files (M01/, M02/, M03/)
- **Access**: Sidecar container reads from here

### **Shared Data Volume** (EmptyDir)
- **Purpose**: Temporary shared storage between containers
- **Contains**: 
  - Copied & organized HDF5 files
  - `file_manifest.json` (metadata for main container)
- **Access**: 
  - Sidecar: Read-write (copies files here)
  - Main container: Read-only (streams from here)

### **Data Flow**:
```
Host /data → Source Volume → Sidecar → Shared Volume → OPC UA Server
```

The diagram above shows the complete volume structure and sequential processing flow.

## 📁 File Structure

```
opcua-server/
├── sidecar/
│   ├── DataSidecar.py          # Sidecar container script
│   └── Dockerfile              # Sidecar container image
├── opcua/
│   ├── enhancedOpcuaDeployment.yaml  # Enhanced K8s deployment
│   └── README.md               # Original setup guide
├── EnhancedBoschDataServer.py  # Enhanced OPC UA server
├── EnhancedDockerfile          # Enhanced server container image
├── build-and-deploy.sh         # Automated build/deploy script
├── verify-deployments.sh       # Verify both deployments script
├── BoschDataServer.py          # Original server (unchanged)
├── Dockerfile                  # Original container (unchanged)
└── data/                       # Your HDF5 data files
    ├── M01/
    │   ├── OP01/good/*.h5
    │   ├── OP02/good/*.h5
    │   └── ...
    └── M02/
        ├── OP01/good/*.h5
        ├── OP02/good/*.h5
        └── ...
```

## ⚙️ Configuration

### Data Selection (per TechSpikeDataPipeline.md)

- **Included Machines**: M01, M02
- **Excluded Machine**: M03 (deferred to major version)
- **Excluded Operations**: OP00, OP06, OP09, OP13
- **File Processing**: Sequential per operation (good files, then bad files within each operation)

### OPC UA Variables

The enhanced server maintains **backward compatibility** with your existing Node-RED setup while adding new metadata:

#### Original Variables (Unchanged)
```
VibrationXBatch: [float array]
VibrationYBatch: [float array] 
VibrationZBatch: [float array]
TotalSamples: int
CurrentSampleIndex: int
Timestamp: float
```

#### New Enhanced Variables
```
TotalFiles: int               # Total number of files to stream
CurrentFileIndex: int         # Current file being streamed (0-based)
CurrentFileName: string       # Current file name
CurrentMachine: string        # Current machine (M01, M02)
CurrentOperation: string      # Current operation (OP01, OP02, etc.)
CurrentQuality: string        # Current quality (good, bad)
```

## 🔄 Data Flow

1. **Sidecar Discovery**: Discovers HDF5 files in `/data` following the requirements
2. **File Copy**: Copies files to shared volume with organized structure
3. **Manifest Creation**: Creates `file_manifest.json` with file metadata
4. **OPC UA Streaming**: Enhanced server reads manifest and streams files sequentially
5. **File Rotation**: Automatically rotates to next file after completing current file
6. **Continuous Loop**: Cycles through all available files

### Streaming Behavior

- **Rate**: 10 samples per second (maintained from original)
- **Batch Size**: 10 samples per batch (maintained from original)
- **File Rotation**: Automatic when file is completed
- **File Order**: Sequential per operation (completes all files in one operation before moving to next)
- **Operation Coverage**: All included operations per machine

## 🐛 Troubleshooting

### Common Issues

#### 1. Sidecar Not Finding Files
```bash
# Check if data path is correctly mounted
kubectl exec -n p1-shopfloor deployment/enhanced-opcua-server -c data-sidecar -- ls -la /source-data

# Check sidecar logs
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c data-sidecar
```

#### 2. OPC UA Server Not Starting
```bash
# Check if manifest file exists
kubectl exec -n p1-shopfloor deployment/enhanced-opcua-server -c enhanced-opcua-server -- ls -la /shared-data

# Check server logs
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c enhanced-opcua-server
```

#### 3. No Files Streaming
```bash
# Check manifest content
kubectl exec -n p1-shopfloor deployment/enhanced-opcua-server -c enhanced-opcua-server -- cat /shared-data/file_manifest.json
```

### Log Analysis

#### Sidecar Logs (Successful)
```
INFO:__main__:Starting Data Sidecar Container
INFO:__main__:Discovered files for 2 machines
INFO:__main__:Copied 450 files to shared volume
INFO:__main__:Created file manifest: /shared-data/file_manifest.json
```

#### Enhanced Server Logs (Successful)
```
INFO:__main__:Enhanced server running at opc.tcp://0.0.0.0:4840/
INFO:__main__:Total files to stream: 450
INFO:__main__:Files by quality - Good: 380, Bad: 70
INFO:__main__:Streaming batch 0 from M01_OP01 (good) - File 1/450
```

## 🔧 Customization

### Modify Included/Excluded Operations

Edit `sidecar/DataSidecar.py`:
```python
self.included_machines = ["M01", "M02"]  # Add/remove machines
self.excluded_operations = ["OP00", "OP06", "OP09", "OP13"]  # Modify excluded operations
```

### Change Streaming Rate

Edit `EnhancedBoschDataServer.py`:
```python
BATCH_SIZE = 10  # Change batch size
# In streaming_task():
await asyncio.sleep(1.0)  # Change to desired interval (e.g., 0.1 for 10Hz)
```

### Adjust Sync Interval

Edit `opcua/enhancedOpcuaDeployment.yaml`:
```yaml
env:
- name: SYNC_INTERVAL
  value: "300"  # Change sync interval (seconds)
```

## 📊 Monitoring

### Key Metrics to Monitor

1. **File Discovery**: Number of files found by sidecar
2. **Streaming Progress**: Current file and sample indices
3. **Resource Usage**: Memory and CPU of both containers
4. **Error Rates**: Failed file loads or streaming errors

### Monitoring Commands

```bash
# Real-time logs
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c enhanced-opcua-server -f

# Resource usage
kubectl top pods -n p1-shopfloor -l app=enhanced-opcua-server

# Detailed pod status
kubectl describe pod -n p1-shopfloor -l app=enhanced-opcua-server
```

## 🎯 Expected Results

After successful deployment, your enhanced OPC UA server will:

1. ✅ **Stream from 22 machine-operation combinations** (M01 & M02, excluding specified operations)
2. ✅ **Maintain 10 streams per second** to your Kafka pipeline
3. ✅ **Automatically rotate through all available files**
4. ✅ **Provide rich metadata** about current file, machine, and operation
5. ✅ **Maintain compatibility** with your existing Node-RED flattening
6. ✅ **Scale horizontally** if needed (multiple replicas)

The enhanced setup supports your goal of generating **9 features per machine-operation** as outlined in the TechSpikeDataPipeline.md:
- 3 RMS values (X, Y, Z)
- 3 Peak values (X, Y, Z)  
- 3 Kurtosis values (X, Y, Z)

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review pod logs for both containers
3. Verify data path mounting
4. Ensure file permissions are correct

The sidecar pattern ensures **separation of concerns** and **scalability** while maintaining your existing 10 streams/second pipeline to Kafka. 