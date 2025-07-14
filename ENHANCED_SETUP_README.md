# 🏭 Enhanced Multi-File OPC UA Server with Git-Based Sidecar Pattern

> **⚠️ IMPORTANT**: This creates a **NEW deployment** that runs **alongside** your existing OPC UA server without interfering with it.

This enhanced setup extends your existing single-file OPC UA server to automatically load and stream data from **all files** in a git repository using a **Kubernetes sidecar container pattern** with **automatic git-based data loading**.

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
| **Data Source** | Single file: `M01_Aug_2019_OP00_000.h5` | Git repository: `https://github.com/Anvisimi/cncdata_M0102.git` |
| **Data Loading** | Manual file placement | **Automatic git cloning** |
| **Machines** | M01 only | M01, M02 (M03 excluded per requirements) |
| **Operations** | OP00 only | All operations except OP00, OP06, OP09, OP13 |
| **Architecture** | Single container | Git-enhanced sidecar pattern with 2 containers |
| **File Management** | Static | Dynamic file rotation with **881 filtered files** |
| **Streaming Rate** | 10 samples/second | **10 samples/second (maintained)** |

### Git-Enhanced Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Pod                           │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │   Data Sidecar  │    │   Enhanced OPC UA Server       │  │
│  │                 │    │                                 │  │
│  │ • Git Clone     │    │ • Waits for .ready signal      │  │
│  │ • Filter M01/M02│────│ • Direct file discovery        │  │
│  │ • Copy to shared│    │ • Multi-file streaming         │  │
│  │ • Create .ready │    │ • 881 files → 15 days          │  │
│  └─────────────────┘    └─────────────────────────────────┘  │
│           │                           │                     │
│           │                           │                     │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │  Git Repository │    │     Persistent Volume          │  │
│  │                 │    │                                 │  │
│  │ github.com/     │    │ • Filtered H5 files (881)      │  │
│  │ Anvisimi/       │    │ • .ready signal file           │  │
│  │ cncdata_M0102   │    │ • M01, M02 directories         │  │
│  └─────────────────┘    └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **Existing Setup**: Your current OPC UA server should be working (optional)
2. **Kubernetes**: Minikube or any Kubernetes cluster
3. **Docker**: For building container images
4. **Git Repository**: Access to `https://github.com/Anvisimi/cncdata_M0102.git` (public)

**No local data folder required!** - Data is automatically cloned from git repository.

### Step 1: Build and Deploy

```bash
# Make the script executable
chmod +x build-and-deploy.sh

# Run the automated build and deployment
./build-and-deploy.sh
```

### Step 2: Verify Deployment

```bash
# Check pod status (should show 2/2 Running)
kubectl get pods -n p1-shopfloor -l app=enhanced-opcua-server

# View sidecar logs (git cloning and filtering)
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c data-sidecar

# View server logs (file streaming)
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c enhanced-opcua-server
```

### Step 3: Access Enhanced OPC UA Server

```bash
# Port forward to access the server
kubectl port-forward -n p1-shopfloor service/enhanced-opcua-service 4841:4840

# Connect using OPC UA client to: opc.tcp://localhost:4841/
```

## 💾 Git-Based Data Architecture

### **Data Flow Pipeline**
```
Git Repository → Git Clone → Filter & Copy → Shared Volume → OPC UA Streaming
```

1. **Git Repository Source**: `https://github.com/Anvisimi/cncdata_M0102.git`
   - Contains complete CNC machine data (M01, M02, M03)
   - Original: 1,702 files across all machines

2. **Sidecar Git Clone**: `/home/sidecar/git-data-repo` (temporary)
   - Shallow clone (`--depth 1`) for efficiency
   - Automatic cleanup after filtering

3. **Filtering Process**:
   - **Include**: M01, M02 machines only
   - **Exclude**: M03 machine (540 files removed)
   - **Exclude**: Operations OP00, OP06, OP09, OP13 (440 files removed)
   - **Result**: 881 files (826 good + 55 bad)

4. **Shared Volume**: `/shared-data` (persistent)
   - Filtered H5 files in organized structure
   - `.ready` signal file for synchronization

5. **OPC UA Server**:
   - Waits for `.ready` signal (max 5 minutes timeout)
   - Direct file discovery with proper sorting
   - Sequential streaming: ~24.5 minutes per file
   - **Total streaming time**: ~15 days for all 881 files

### **Synchronization Mechanism**

| Component | Action | Signal |
|-----------|--------|---------|
| **Sidecar** | Git clone + filter + copy | Creates `/shared-data/.ready` |
| **OPC UA Server** | `wait_for_sidecar_ready()` | Waits for `.ready` file |
| **Result** | Server starts file discovery | Begin streaming 881 files |

## 📁 File Structure

```
opcua-server/
├── sidecar/
│   ├── DataSidecar.py          # Git-enhanced sidecar container
│   └── Dockerfile              # Sidecar image with git support
├── opcua/
│   └── enhancedOpcuaDeployment.yaml  # K8s deployment with git config
├── EnhancedBoschDataServer.py  # Enhanced server with .ready signal waiting
├── EnhancedDockerfile          # Enhanced server container image
├── build-and-deploy.sh         # Automated build/deploy script
├── ENHANCED_SETUP_README.md    # This file
├── BoschDataServer.py          # Original server (unchanged)
└── Dockerfile                  # Original container (unchanged)
```

## ⚙️ Git Configuration

### Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `DATA_GIT_REPO_URL` | `https://github.com/Anvisimi/cncdata_M0102.git` | Git repository URL |
| `SHARED_DATA_PATH` | `/shared-data` | Shared volume mount path |

### Data Selection (per TechSpikeDataPipeline.md)

```python
# In DataSidecar.py
self.included_machines = ["M01", "M02"]  # Exclude M03
self.excluded_operations = ["OP00", "OP06", "OP09", "OP13"]
```

**Result**: 881 files from 1,702 original files (48% reduction)

### OPC UA Variables

The enhanced server maintains **backward compatibility** with your existing Node-RED setup while adding new metadata:

#### Original Variables (Unchanged)
```
VibrationXBatch: [float array]    # 10 samples per batch
VibrationYBatch: [float array]    # 10 samples per batch
VibrationZBatch: [float array]    # 10 samples per batch
TotalSamples: int                 # Samples in current file (~58,800)
CurrentSampleIndex: int           # Current position in file
Timestamp: float                  # Unix timestamp
```

#### New Enhanced Variables
```
TotalFiles: int               # 881 (total filtered files)
CurrentFileIndex: int         # Current file being streamed (0-880)
CurrentFileName: string       # e.g., "M01_Aug_2019_OP01_000.h5"
CurrentMachine: string        # Current machine (M01, M02)
CurrentOperation: string      # Current operation (OP01, OP02, etc.)
CurrentQuality: string        # Current quality (good, bad)
```

## 🔄 Git-Enhanced Data Flow

### **Phase 1: Git Data Loading (Sidecar)**
1. **Git Clone**: `git clone --depth 1 https://github.com/Anvisimi/cncdata_M0102.git`
2. **Filter & Copy**: Process 1,702 files → keep 881 files
3. **Signal Ready**: Create `/shared-data/.ready` file
4. **Cleanup**: Remove git clone directory to save space

### **Phase 2: OPC UA Streaming (Main Container)**
1. **Wait for Signal**: `wait_for_sidecar_ready(timeout=300)`
2. **File Discovery**: `discover_files_from_shared_data()` with sorting
3. **Sequential Streaming**: 
   - 10 samples/batch, 4 batches/second
   - ~24.5 minutes per file
   - Automatic file rotation
4. **Continuous Loop**: Restart after completing all 881 files

### **Streaming Behavior**

- **Rate**: 10 samples per second (maintains compatibility)
- **Batch Size**: 10 samples per batch
- **File Rotation**: Automatic when file is completed
- **File Order**: Chronological + sequential (Feb 2019 → Aug 2019 → Feb 2020 → Aug 2021)
- **Total Time**: ~15 days for complete cycle

## 🐛 Troubleshooting

### Common Issues

#### 1. Sidecar Git Clone Failure
```bash
# Check sidecar logs for git errors
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c data-sidecar

# Common causes: Network issues, git repository access
# Solution: Check git repo URL and network connectivity
```

#### 2. OPC UA Server Timeout Waiting for Sidecar
```bash
# Check if .ready file exists
kubectl exec -n p1-shopfloor deployment/enhanced-opcua-server -c enhanced-opcua-server -- ls -la /shared-data/.ready

# Check server logs for timeout messages
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c enhanced-opcua-server
```

#### 3. No Files Found After Git Clone
```bash
# Check shared volume contents
kubectl exec -n p1-shopfloor deployment/enhanced-opcua-server -c enhanced-opcua-server -- find /shared-data -name "*.h5" | wc -l

# Should show: 881 files
```

### Log Analysis

#### Sidecar Logs (Successful Git-Based Loading)
```
INFO:__main__:Starting Git-Enhanced Data Sidecar
INFO:__main__:Git repository URL: https://github.com/Anvisimi/cncdata_M0102.git
INFO:__main__:Cloning data from git repository: https://github.com/Anvisimi/cncdata_M0102.git
INFO:__main__:Successfully cloned data repository to /home/sidecar/git-data-repo
INFO:__main__:Processing M01 from git repository...
INFO:__main__:Found operations for M01: ['OP01', 'OP02', 'OP03', 'OP04', 'OP05', 'OP07', 'OP08', 'OP10', 'OP11', 'OP12', 'OP14']
INFO:__main__:Processing M02 from git repository...
INFO:__main__:Found operations for M02: ['OP01', 'OP02', 'OP03', 'OP04', 'OP05', 'OP07', 'OP08', 'OP10', 'OP11', 'OP12', 'OP14']
INFO:__main__:Git data copy complete - total files copied: 881
INFO:__main__:Created .ready file to signal completion to main container
INFO:__main__:Data setup complete! 881 files ready in shared volume
```

#### Enhanced Server Logs (Successful Streaming)
```
INFO:__main__:Waiting for sidecar to complete data loading (timeout: 300s)...
INFO:__main__:Sidecar has completed data loading!
INFO:__main__:Discovering files from /shared-data
INFO:__main__:Found 881 HDF5 files
INFO:__main__:Discovered 881 files after filtering and sorting
INFO:__main__:Files by machine: ['M01', 'M02']
INFO:__main__:Files by quality - Good: 826, Bad: 55
INFO:__main__:Enhanced server running at opc.tcp://0.0.0.0:4840/
INFO:__main__:Total files to stream: 881
INFO:__main__:Streaming files from machines: ['M01', 'M02']
INFO:__main__:Operations included: ['OP01', 'OP02', 'OP03', 'OP04', 'OP05', 'OP07', 'OP08', 'OP10', 'OP11', 'OP12', 'OP14']
```

## 🔧 Customization

### Modify Git Repository Source
Edit `opcua/enhancedOpcuaDeployment.yaml`:
```yaml
env:
- name: DATA_GIT_REPO_URL
  value: "https://github.com/your-org/your-data-repo.git"
```

### Change Included/Excluded Operations
Edit `sidecar/DataSidecar.py`:
```python
self.included_machines = ["M01", "M02", "M03"]  # Add M03 if needed
self.excluded_operations = ["OP00", "OP06"]     # Modify excluded operations
```

### Adjust Git Clone Timeout
Edit `sidecar/DataSidecar.py`:
```python
# In clone_data_repository():
result = subprocess.run([
    "git", "clone", "--depth", "1", self.git_repo_url, self.git_clone_path
], capture_output=True, text=True, timeout=600)  # Change from 300 to 600 seconds
```

### Change Streaming Rate
Edit `EnhancedBoschDataServer.py`:
```python
BATCH_SIZE = 10  # Change batch size
# In streaming_task():
await asyncio.sleep(0.25)  # Change to desired interval (e.g., 1.0 for 1Hz)
```

## 📊 Monitoring

### Key Metrics to Monitor

1. **Git Clone Status**: Successful repository cloning
2. **File Filtering**: 881 files from 1,702 original
3. **Streaming Progress**: Current file and sample indices
4. **Resource Usage**: Memory and CPU of both containers
5. **Synchronization**: `.ready` file creation and detection

### Monitoring Commands

```bash
# Real-time streaming logs
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c enhanced-opcua-server -f

# Git clone progress logs
kubectl logs -n p1-shopfloor -l app=enhanced-opcua-server -c data-sidecar -f

# Resource usage
kubectl top pods -n p1-shopfloor -l app=enhanced-opcua-server

# Detailed pod status
kubectl describe pod -n p1-shopfloor -l app=enhanced-opcua-server

# File count verification
kubectl exec -n p1-shopfloor deployment/enhanced-opcua-server -c enhanced-opcua-server -- find /shared-data -name "*.h5" | wc -l
```

### Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Total Files** | 881 | After filtering from 1,702 |
| **Good Quality** | 826 files | 93.8% of filtered files |
| **Bad Quality** | 55 files | 6.2% of filtered files |
| **Streaming Rate** | 10 samples/second | 4 batches/second × 10 samples/batch |
| **Time per File** | ~24.5 minutes | 58,800 samples ÷ 40 samples/second |
| **Total Cycle Time** | ~15 days | 881 files × 24.5 minutes |

## 🎯 Expected Results

After successful deployment, your git-enhanced OPC UA server will:

1. ✅ **Automatically clone data** from `https://github.com/Anvisimi/cncdata_M0102.git`
2. ✅ **Filter to 881 files** from 1,702 original files (M01/M02 only, excluded operations)
3. ✅ **Stream chronologically** with proper file sorting (Feb 2019 → Aug 2019 → Feb 2020 → Aug 2021)
4. ✅ **Maintain 10 streams per second** to your existing Kafka pipeline
5. ✅ **Automatically rotate through all files** in ~15-day cycles
6. ✅ **Provide rich metadata** about current file, machine, operation, and quality
7. ✅ **Maintain full compatibility** with your existing Node-RED data flattening
8. ✅ **Scale horizontally** if needed (multiple replicas with independent data loads)

The git-enhanced setup eliminates manual data loading while supporting your goal of generating **9 features per machine-operation** as outlined in the TechSpikeDataPipeline.md:
- 3 RMS values (X, Y, Z)
- 3 Peak values (X, Y, Z)  
- 3 Kurtosis values (X, Y, Z)

## 📞 Support

If you encounter issues:

1. **Check git connectivity**: Ensure cluster can access `https://github.com/Anvisimi/cncdata_M0102.git`
2. **Review sidecar logs**: Look for git clone errors or filtering issues
3. **Verify synchronization**: Check for `.ready` file creation and detection
4. **Monitor resource usage**: Ensure sufficient storage for 881 files
5. **Test file counts**: Should see exactly 881 H5 files after filtering

The git-based sidecar pattern provides **automatic data loading**, **version control**, and **reproducible deployments** while maintaining your existing 10 streams/second pipeline to Kafka.

## 🔄 Automatic Updates

The system supports automatic data updates:

1. **Data Changes**: If the git repository is updated, restart the pod to re-clone
2. **Configuration Changes**: Modify environment variables and redeploy
3. **Scaling**: Multiple replicas will each perform independent git clones
4. **Backup Strategy**: Git repository serves as both source and backup

This git-enhanced approach provides **infrastructure as code** for your data pipeline with full traceability and reproducibility. 