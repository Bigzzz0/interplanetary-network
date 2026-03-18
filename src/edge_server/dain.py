"""
DAIN - Depth-Aware Video Frame Interpolation
Simplified implementation for CPU/GPU inference
Based on: Bao et al., CVPR 2019
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class DepthWarping(nn.Module):
    """
    Depth-Aware Warping Layer.
    Uses depth maps to weight the warping process, reducing ghosting artifacts.
    """
    def __init__(self):
        super(DepthWarping, self).__init__()

    def forward(self, x, flow, depth=None):
        """
        Warp image using optical flow, optionally weighted by depth.
        
        Args:
            x: Input image tensor (B, C, H, W)
            flow: Optical flow tensor (B, 2, H, W)
            depth: Optional depth map (B, 1, H, W)
            
        Returns:
            warped: Warped image tensor
        """
        B, C, H, W = x.size()
        
        # Create meshgrid
        grid_y, grid_x = torch.meshgrid(
            torch.arange(0, H, device=x.device),
            torch.arange(0, W, device=x.device),
            indexing='ij'
        )
        grid_x = grid_x.float().unsqueeze(0).unsqueeze(0).expand(B, -1, -1, -1)
        grid_y = grid_y.float().unsqueeze(0).unsqueeze(0).expand(B, -1, -1, -1)
        
        # Apply flow
        v_grid_x = grid_x + flow[:, 0:1, :, :]
        v_grid_y = grid_y + flow[:, 1:2, :, :]
        
        # Normalize grid to [-1, 1]
        v_grid_x = 2.0 * v_grid_x / (W - 1) - 1.0
        v_grid_y = 2.0 * v_grid_y / (H - 1) - 1.0
        
        v_grid = torch.stack((v_grid_x.squeeze(1), v_grid_y.squeeze(1)), dim=3)
        
        # Sample using grid_sample
        warped = F.grid_sample(x, v_grid, padding_mode='border', align_corners=True)
        
        # If depth is provided, use it to weight the output
        if depth is not None:
            # Depth-aware blending (simplified)
            depth_norm = depth / (depth.max() + 1e-6)
            warped = warped * (1 + depth_norm)
        
        return warped


class ResBlock(nn.Module):
    """Residual block for feature extraction."""
    def __init__(self, in_channels, out_channels, stride=1):
        super(ResBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, stride=stride, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        
        self.downsample = None
        if stride != 1 or in_channels != out_channels:
            self.downsample = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1, stride=stride),
                nn.BatchNorm2d(out_channels)
            )

    def forward(self, x):
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        if self.downsample:
            residual = self.downsample(x)
        out += residual
        out = self.relu(out)
        return out


class DAIN(nn.Module):
    """
    Simplified DAIN for depth-aware frame interpolation.
    Works on both CPU and GPU.
    """
    def __init__(self):
        super(DAIN, self).__init__()
        
        # 1. Depth Estimation Network
        self.depth_net = nn.Sequential(
            nn.Conv2d(3, 32, 7, stride=2, padding=3),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(64, 32, 4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(32, 1, 4, stride=2, padding=1),
            nn.Sigmoid()
        )
        
        # 2. Motion Estimation (simplified)
        self.motion_net = nn.Sequential(
            nn.Conv2d(6, 64, 7, stride=2, padding=3),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 64, 4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(64, 2, 4, stride=2, padding=1)
        )
        
        # 3. Kernel Estimation (for refinement)
        self.kernel_net = nn.Sequential(
            nn.Conv2d(6, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 25, 3, padding=1)  # 5x5 kernel
        )
        
        # 4. Refinement Network
        self.refine_net = nn.Sequential(
            ResBlock(6, 64),
            ResBlock(64, 64),
            nn.Conv2d(64, 3, 3, padding=1)
        )
        
        self.warping = DepthWarping()

    def forward(self, frame1, frame2, flow=None, t=0.5):
        """
        Interpolate between frame1 and frame2 at time t.
        
        Args:
            frame1: First frame tensor (B, 3, H, W)
            frame2: Second frame tensor (B, 3, H, W)
            flow: Pre-computed optical flow (optional)
            t: Interpolation time (0 to 1)
            
        Returns:
            interpolated: Interpolated frame tensor
        """
        # Estimate depth maps
        depth1 = self.depth_net(frame1)
        depth2 = self.depth_net(frame2)
        
        # Use provided flow or estimate from frames
        if flow is None:
            concatenated = torch.cat([frame1, frame2], dim=1)
            flow = self.motion_net(concatenated)
        
        # Warp frames to intermediate time t
        flow_forward = flow * t
        flow_backward = -flow * (1 - t)
        
        warped1 = self.warping(frame1, flow_forward, depth1)
        warped2 = self.warping(frame2, flow_backward, depth2)
        
        # Blend warped frames
        blended = warped1 * (1 - t) + warped2 * t
        
        # Concatenate for refinement
        combined = torch.cat([warped1, warped2], dim=1)
        
        # Estimate refinement kernel
        kernel = self.kernel_net(combined)
        
        # Apply refinement
        residual = self.refine_net(combined)
        
        # Final output
        output = blended + residual
        output = torch.clamp(output, 0, 1)
        
        return output


def load_dain_model(pretrained_path=None, device='cpu'):
    """
    Load DAIN model with optional pretrained weights.
    
    Args:
        pretrained_path: Path to pretrained weights (.pth file)
        device: Device to load model on ('cpu' or 'cuda')
        
    Returns:
        DAIN model instance
    """
    model = DAIN().to(device)
    
    if pretrained_path and pretrained_path.exists():
        try:
            checkpoint = torch.load(pretrained_path, map_location=device)
            model.load_state_dict(checkpoint)
            print(f"[OK] Loaded DAIN weights from {pretrained_path}")
        except Exception as e:
            print(f"[WARN] Could not load pretrained weights: {e}")
    else:
        print("[INFO] Using randomly initialized DAIN weights")
    
    model.eval()
    return model
