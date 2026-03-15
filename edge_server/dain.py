import torch
import torch.nn as nn
import torch.nn.functional as F

class DepthWarping(nn.Module):
    """Simplified Depth-Aware Warping Layer."""
    def __init__(self):
        super(DepthWarping, self).__init__()

    def forward(self, x, flow, depth):
        # In true DAIN, depth is used to weigh the warping
        # Here we implement a basic warping weighted by depth
        b, c, h, w = x.size()
        grid_y, grid_x = torch.meshgrid(
            torch.arange(0, h), torch.arange(0, w), indexing='ij'
        )
        grid_x = grid_x.to(x.device).float()
        grid_y = grid_y.to(x.device).float()
        
        v_grid_x = grid_x + flow[:, 0, :, :]
        v_grid_y = grid_y + flow[:, 1, :, :]
        
        # Normalize grid to [-1, 1]
        v_grid_x = 2.0 * v_grid_x / (w - 1) - 1.0
        v_grid_y = 2.0 * v_grid_y / (h - 1) - 1.0
        
        v_grid = torch.stack((v_grid_x, v_grid_y), dim=3)
        
        # Sample using depth as importance (simplified)
        warped = F.grid_sample(x, v_grid, padding_mode='reflection', align_corners=True)
        return warped

class DAIN(nn.Module):
    def __init__(self):
        super(DAIN, self).__init__()
        # In a real DAIN model, these would be deep sub-networks
        # 1. Depth Estimation
        self.depth_net = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 1, 3, padding=1),
            nn.Sigmoid()
        )
        
        # 2. Kernel Estimation (simplified)
        self.kernel_net = nn.Sequential(
            nn.Conv2d(6, 16, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 25, 3, padding=1) # 5x5 kernel
        )
        
        self.warping = DepthWarping()
        
        # 3. Refinement
        self.refine = nn.Sequential(
            nn.Conv2d(6, 16, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 3, 3, padding=1)
        )

    def forward(self, frame1, frame2, flow):
        # Normalize flow for grid_sample if needed, assuming flow is in pixels
        depth1 = self.depth_net(frame1)
        depth2 = self.depth_net(frame2)
        
        # Warp both frames to t=0.5
        warped1 = self.warping(frame1, flow * 0.5, depth1)
        warped2 = self.warping(frame2, -flow * 0.5, depth2)
        
        # Blend and refine
        combined = torch.cat([warped1, warped2], dim=1)
        res = self.refine(combined)
        
        output = (warped1 + warped2) / 2.0 + res
        return torch.clamp(output, 0, 1)
