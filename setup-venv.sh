#!/bin/bash

# PyTorch wheel URLs
CUDA_URL="https://download.pytorch.org/whl/cu126"
ROCM_URL="https://download.pytorch.org/whl/rocm7.1"
CPU_URL="https://download.pytorch.org/whl/cpu"

rm -rf .venv
python -m venv .venv
source .venv/bin/activate

# Detect GPU type and install appropriate PyTorch version
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    # NVIDIA GPU detected
    echo "NVIDIA GPU detected - installing CUDA version"
    pip install torch torchvision --extra-index-url "$CUDA_URL"
elif command -v rocminfo &> /dev/null && rocminfo &> /dev/null; then
    # AMD GPU detected via rocminfo
    echo "AMD GPU detected - installing ROCm version"
    pip install torch torchvision --index-url "$ROCM_URL"
elif lspci | grep -i "advanced micro devices" &> /dev/null; then
    # AMD GPU detected via lspci
    echo "AMD GPU detected - installing ROCm version"
    pip install torch torchvision --index-url "$ROCM_URL"
else
    echo "No GPU detected - installing CPU-only version"
    pip install torch torchvision --index-url "$ROCM_URL"
fi
