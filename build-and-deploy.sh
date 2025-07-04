#!/bin/bash

# Enhanced Bosch OPC UA Server - Build and Deploy Script
set -e

# Configuration
DOCKER_REGISTRY="yathu25"
DATA_SIDECAR_IMAGE="${DOCKER_REGISTRY}/data-sidecar:latest"
ENHANCED_OPCUA_IMAGE="${DOCKER_REGISTRY}/enhanced-opcua-server:latest"
NAMESPACE="p1-shopfloor"
DATA_PATH="/Users/inderpreet/Documents/sidecar_impl/opcua-server/data"

echo "🏭 Enhanced Bosch OPC UA Server - Build and Deploy"
echo "=================================================="
echo "⚠️  IMPORTANT: This creates a NEW deployment separate from existing opcua-server"
echo "   - Existing: opcua-server (single file)"  
echo "   - Enhanced: enhanced-opcua-server (multi-file with sidecar)"
echo "   - Both can run simultaneously without conflicts"
echo "=================================================="

# Step 1: Build Docker Images
echo "📦 Step 1: Building Docker Images..."

echo "Building data sidecar image..."
cd sidecar
docker build -t $DATA_SIDECAR_IMAGE .
cd ..

echo "Building enhanced OPC UA server image..."
docker build -f EnhancedDockerfile -t $ENHANCED_OPCUA_IMAGE .

echo "✅ Docker images built successfully"

# Step 2: Push Images to Registry (optional)
read -p "🚀 Push images to Docker registry? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Pushing images to registry..."
    docker push $DATA_SIDECAR_IMAGE
    docker push $ENHANCED_OPCUA_IMAGE
    echo "✅ Images pushed to registry"
else
    echo "⏭️  Skipping registry push"
fi

# Step 3: Update Kubernetes Deployment with Correct Data Path
echo "📝 Step 3: Updating Kubernetes deployment..."

# The deployment file already has the correct data path
cp opcua/enhancedOpcuaDeployment.yaml /tmp/enhanced-deployment.yaml

echo "Using deployment with data path: $DATA_PATH"

# Step 4: Deploy to Kubernetes
echo "☸️  Step 4: Deploying to Kubernetes..."

# Ensure namespace exists
kubectl get namespace $NAMESPACE >/dev/null 2>&1 || kubectl create namespace $NAMESPACE

# Apply the deployment
kubectl apply -f /tmp/enhanced-deployment.yaml

echo "✅ Deployment applied to Kubernetes"

# Step 5: Check Deployment Status
echo "🔍 Step 5: Checking deployment status..."

echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/enhanced-opcua-server -n $NAMESPACE

# Show pod status
echo "📊 Pod Status:"
kubectl get pods -n $NAMESPACE -l app=enhanced-opcua-server

# Show logs from both containers
echo "📋 Container Logs:"
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=enhanced-opcua-server -o jsonpath='{.items[0].metadata.name}')

echo "--- Data Sidecar Logs ---"
kubectl logs $POD_NAME -c data-sidecar -n $NAMESPACE --tail=20 || echo "Sidecar not ready yet"

echo "--- Enhanced OPC UA Server Logs ---"
kubectl logs $POD_NAME -c enhanced-opcua-server -n $NAMESPACE --tail=20 || echo "OPC UA server not ready yet"

# Step 6: Verify Both Deployments
echo "🌐 Step 6: Deployment Verification..."
echo "Checking both deployments are running independently:"
echo ""
echo "--- Existing Deployment ---"
kubectl get deployment opcua-server -n $NAMESPACE 2>/dev/null || echo "Existing opcua-server not found (this is normal if not deployed yet)"
echo ""
echo "--- Enhanced Deployment ---"
kubectl get deployment enhanced-opcua-server -n $NAMESPACE
echo ""
echo "--- Services ---"
kubectl get services -n $NAMESPACE | grep opcua || echo "No OPC UA services found"

echo ""
echo "🎉 Deployment Complete!"
echo "================================"
echo "To access the OPC UA server:"
echo "1. Port forward: kubectl port-forward -n $NAMESPACE pod/$POD_NAME 4840:4840"
echo "2. Connect to: opc.tcp://localhost:4840/"
echo ""
echo "To check logs:"
echo "- Sidecar: kubectl logs $POD_NAME -c data-sidecar -n $NAMESPACE -f"
echo "- OPC UA: kubectl logs $POD_NAME -c enhanced-opcua-server -n $NAMESPACE -f"
echo ""
echo "Data will be streamed from all files in: $DATA_PATH"
echo "Excluding M03 and operations: OP00, OP06, OP09, OP13"
echo ""
echo "📖 For detailed deployment comparison, see: DEPLOYMENT_COMPARISON.md"
echo "🔍 To verify both deployments: ./verify-deployments.sh"

# Cleanup
rm -f /tmp/enhanced-deployment.yaml 