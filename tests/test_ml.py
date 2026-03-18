#!/usr/bin/env python3
"""Test script for ML interpolation."""

import sys
import os
import numpy as np
import cv2

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print("=" * 60)
print("Testing ML Frame Interpolation")
print("=" * 60)

# Import main_ml module
from src.edge_server.main_ml import (
    interpolate_frames_ml,
    interpolate_frames_opencv,
    load_ml_models,
    torch_available,
    raft_available,
    dain_available,
    raft_model,
    dain_model,
    device
)

print(f"\n1. Environment Check:")
print(f"   torch_available: {torch_available}")
print(f"   raft_available: {raft_available}")
print(f"   dain_available: {dain_available}")
print(f"   device: {device}")

print(f"\n2. Loading ML models...")
load_ml_models()
print("   Models loaded!")

print(f"\n3. Creating test frames (128x128)...")
frame1 = np.random.randint(50, 200, (128, 128, 3), dtype=np.uint8)
frame2 = np.random.randint(50, 200, (128, 128, 3), dtype=np.uint8)
print(f"   Frame1 shape: {frame1.shape}, dtype: {frame1.dtype}")
print(f"   Frame2 shape: {frame2.shape}, dtype: {frame2.dtype}")

print(f"\n4. Testing OpenCV fallback interpolation...")
try:
    opencv_result = interpolate_frames_opencv(frame1, frame2, num_interpolated=2)
    print(f"   OpenCV result: {len(opencv_result)} frames")
    for i, (frm, conf) in enumerate(opencv_result):
        print(f"      Frame {i}: shape={frm.shape}, conf={conf:.2f}")
except Exception as e:
    print(f"   OpenCV error: {e}")

print(f"\n5. Testing ML interpolation...")
try:
    ml_result = interpolate_frames_ml(frame1, frame2, num_interpolated=2)
    print(f"   ML result: {len(ml_result)} frames")
    for i, (frm, conf) in enumerate(ml_result):
        print(f"      Frame {i}: shape={frm.shape}, conf={conf:.2f}")
except Exception as e:
    import traceback
    print(f"   ML error: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
