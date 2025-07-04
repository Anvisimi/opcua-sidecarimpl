#!/bin/bash

# Verification Script for OPC UA Deployments
echo "🔍 OPC UA Deployments Verification"
echo "=================================="

NAMESPACE="p1-shopfloor"

echo ""
echo "📋 Checking namespace..."
kubectl get namespace $NAMESPACE 2>/dev/null || {
    echo "❌ Namespace $NAMESPACE not found"
    exit 1
}

echo ""
echo "📦 Deployments in $NAMESPACE:"
echo "------------------------------"

# Check existing deployment
echo "1. Existing OPC UA Server:"
if kubectl get deployment opcua-server -n $NAMESPACE &>/dev/null; then
    echo "   ✅ opcua-server deployment found"
    kubectl get deployment opcua-server -n $NAMESPACE -o custom-columns="NAME:.metadata.name,READY:.status.readyReplicas,UP-TO-DATE:.status.updatedReplicas,AVAILABLE:.status.availableReplicas"
    
    # Check pods
    EXISTING_PODS=$(kubectl get pods -n $NAMESPACE -l app=opcua-server --no-headers 2>/dev/null | wc -l)
    echo "   📊 Pods running: $EXISTING_PODS"
else
    echo "   ℹ️  opcua-server deployment not found (not deployed yet)"
fi

echo ""
echo "2. Enhanced OPC UA Server:"
if kubectl get deployment enhanced-opcua-server -n $NAMESPACE &>/dev/null; then
    echo "   ✅ enhanced-opcua-server deployment found"
    kubectl get deployment enhanced-opcua-server -n $NAMESPACE -o custom-columns="NAME:.metadata.name,READY:.status.readyReplicas,UP-TO-DATE:.status.updatedReplicas,AVAILABLE:.status.availableReplicas"
    
    # Check pods and containers
    ENHANCED_PODS=$(kubectl get pods -n $NAMESPACE -l app=enhanced-opcua-server --no-headers 2>/dev/null | wc -l)
    echo "   📊 Pods running: $ENHANCED_PODS"
    
    if [ $ENHANCED_PODS -gt 0 ]; then
        POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=enhanced-opcua-server -o jsonpath='{.items[0].metadata.name}')
        echo "   📋 Containers in pod $POD_NAME:"
        kubectl get pod $POD_NAME -n $NAMESPACE -o jsonpath='{.spec.containers[*].name}' | tr ' ' '\n' | sed 's/^/      - /'
    fi
else
    echo "   ❌ enhanced-opcua-server deployment not found"
fi

echo ""
echo "🌐 Services in $NAMESPACE:"
echo "-------------------------"
kubectl get services -n $NAMESPACE -l 'app in (opcua-server,enhanced-opcua-server)' 2>/dev/null || {
    echo "No OPC UA services found"
}

echo ""
echo "🔌 Port Information:"
echo "-------------------"
echo "Existing OPC UA:  opc.tcp://localhost:4840/ (if opcua-service exists)"
echo "Enhanced OPC UA:  opc.tcp://localhost:4840/ (if enhanced-opcua-service exists)"
echo ""
echo "💡 To access locally:"
echo "   kubectl port-forward -n $NAMESPACE service/opcua-service 4840:4840"
echo "   kubectl port-forward -n $NAMESPACE service/enhanced-opcua-service 4841:4840"
echo ""

echo "✅ Verification complete!"
echo ""
echo "🔍 Key Points:"
echo "  - Both deployments use different names and labels"
echo "  - Both deployments can run simultaneously"
echo "  - Each has its own service with different selectors"
echo "  - No resource conflicts should occur" 