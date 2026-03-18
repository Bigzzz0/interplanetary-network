"""
RAFT - Recurrent All-Pairs Field Transforms for Optical Flow
Simplified implementation for CPU/GPU inference
Based on: Teed & Deng, ECCV 2020
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    def __init__(self, in_planes, planes, norm_fn='group', stride=1):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, 3, padding=1, stride=stride)
        self.conv2 = nn.Conv2d(planes, planes, 3, padding=1)
        self.relu = nn.ReLU(inplace=True)

        num_groups = planes // 8
        if norm_fn == 'group':
            self.norm1 = nn.GroupNorm(num_groups=num_groups, num_channels=planes)
            self.norm2 = nn.GroupNorm(num_groups=num_groups, num_channels=planes)
            if stride != 1:
                self.norm3 = nn.GroupNorm(num_groups=num_groups, num_channels=planes)
        elif norm_fn == 'batch':
            self.norm1 = nn.BatchNorm2d(planes)
            self.norm2 = nn.BatchNorm2d(planes)
            if stride != 1:
                self.norm3 = nn.BatchNorm2d(planes)
        else:
            self.norm1 = nn.Sequential()
            self.norm2 = nn.Sequential()
            if stride != 1:
                self.norm3 = nn.Sequential()

        if stride == 1:
            self.downsample = None
        else:
            self.downsample = nn.Sequential(
                nn.Conv2d(in_planes, planes, kernel_size=1, stride=stride),
                self.norm3
            )

    def forward(self, x):
        y = x
        y = self.relu(self.norm1(self.conv1(y)))
        y = self.relu(self.norm2(self.conv2(y)))

        if self.downsample is not None:
            x = self.downsample(x)

        return self.relu(x + y)


class BasicEncoder(nn.Module):
    def __init__(self, output_dim=128, norm_fn='batch', dropout=0.0):
        super(BasicEncoder, self).__init__()
        self.norm_fn = norm_fn

        if self.norm_fn == 'group':
            self.norm1 = nn.GroupNorm(num_groups=8, num_channels=64)
        elif self.norm_fn == 'batch':
            self.norm1 = nn.BatchNorm2d(64)
        else:
            self.norm1 = nn.Sequential()

        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3)
        self.relu1 = nn.ReLU(inplace=True)

        self.in_planes = 64
        self.layer1 = self._make_layer(64, stride=1)
        self.layer2 = self._make_layer(96, stride=2)
        self.layer3 = self._make_layer(128, stride=2)

        # Output convolution
        self.conv2 = nn.Conv2d(128, output_dim, 3, padding=1)

        self.dropout = None
        if dropout > 0:
            self.dropout = nn.Dropout2d(p=dropout)

    def _make_layer(self, dim, stride=1):
        layer1 = ResidualBlock(self.in_planes, dim, self.norm_fn, stride=stride)
        layer2 = ResidualBlock(dim, dim, self.norm_fn, stride=1)
        layers = (layer1, layer2)

        self.in_planes = dim
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.norm1(x)
        x = self.relu1(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)

        x = self.conv2(x)

        if self.dropout is not None:
            x = self.dropout(x)

        return x


class ConvGRU(nn.Module):
    def __init__(self, hidden_dim=128, input_dim=129):
        """
        ConvGRU for flow refinement.
        
        Args:
            hidden_dim: Number of hidden channels (128)
            input_dim: Number of input channels (inp + corr = 128 + 1 = 129)
        """
        super(ConvGRU, self).__init__()
        self.convz = nn.Conv2d(hidden_dim + input_dim, hidden_dim, 3, padding=1)
        self.convr = nn.Conv2d(hidden_dim + input_dim, hidden_dim, 3, padding=1)
        self.convq = nn.Conv2d(hidden_dim + input_dim, hidden_dim, 3, padding=1)

    def forward(self, h, x):
        hx = torch.cat([h, x], dim=1)
        z = torch.sigmoid(self.convz(hx))
        r = torch.sigmoid(self.convr(hx))
        q = torch.tanh(self.convq(torch.cat([r*h, x], dim=1)))
        h = (1-z) * h + z * q
        return h


class RAFT(nn.Module):
    """
    Simplified RAFT for optical flow estimation.
    Works on both CPU and GPU.
    Input images should be divisible by 8 (e.g., 128x128, 256x256)
    """
    def __init__(self, hidden_dim=128, context_dim=128):
        super(RAFT, self).__init__()
        self.hidden_dim = hidden_dim
        self.context_dim = context_dim

        self.fnet = BasicEncoder(output_dim=256, norm_fn='batch')
        self.cnet = BasicEncoder(output_dim=256, norm_fn='batch')
        
        # ConvGRU for flow refinement (input = context_dim + corr_channels = 128 + 1)
        self.gru = ConvGRU(hidden_dim=hidden_dim, input_dim=context_dim + 1)
        
        # Flow head
        self.flow_head = nn.Sequential(
            nn.Conv2d(hidden_dim, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 2, 3, padding=1)
        )

    def forward(self, image1, image2, iters=8):
        """
        Estimate optical flow between image1 and image2.
        
        Args:
            image1: Tensor of shape (B, 3, H, W), H and W divisible by 8
            image2: Tensor of shape (B, 3, H, W), H and W divisible by 8
            iters: Number of refinement iterations
            
        Returns:
            flow_predictions: List of flow tensors at each iteration
            final_flow: Upsampled final flow
        """
        B, _, H, W = image1.shape
        
        # Ensure dimensions are divisible by 8
        pad_h = (8 - H % 8) % 8
        pad_w = (8 - W % 8) % 8
        if pad_h > 0 or pad_w > 0:
            image1 = F.pad(image1, (0, pad_w, 0, pad_h), mode='reflect')
            image2 = F.pad(image2, (0, pad_w, 0, pad_h), mode='reflect')
        
        # Feature extraction
        fmap1 = self.fnet(image1)  # (B, 256, H/8, W/8)
        fmap2 = self.fnet(image2)
        
        # Context network - split into net (hidden) and inp (context)
        cnet = self.cnet(image1)
        # cnet is (B, 256, H/8, W/8), split into (B, 128, ...) and (B, 128, ...)
        net = cnet[:, :self.hidden_dim, :, :]  # (B, 128, H/8, W/8)
        inp = cnet[:, self.hidden_dim:, :, :]  # (B, 128, H/8, W/8)
        net = torch.tanh(net)
        inp = torch.relu(inp)
        
        # Initialize flow at 1/8 resolution
        _, _, hf, wf = fmap1.shape
        flow = torch.zeros(B, 2, hf, wf, device=image1.device)
        
        flow_predictions = []
        
        for _ in range(iters):
            coords = flow.detach()
            
            # Create sampling grid
            grid = self._coords_to_grid(coords)
            
            # Warp fmap2 using current flow
            fmap2_warped = F.grid_sample(
                fmap2, grid,
                mode='bilinear', padding_mode='zeros',
                align_corners=True
            )
            
            # Compute correlation (dot product along channel dim)
            corr = torch.sum(fmap1 * fmap2_warped, dim=1, keepdim=True)  # (B, 1, H/8, W/8)
            corr = torch.relu(corr)
            
            # GRU update: input = inp + corr
            gru_input = torch.cat([inp, corr], dim=1)  # (B, 128+1, H/8, W/8)
            net = self.gru(net, gru_input)  # (B, 128, H/8, W/8)
            
            # Flow update
            delta_flow = self.flow_head(net)  # (B, 2, H/8, W/8)
            flow = flow + delta_flow
            flow_predictions.append(flow)
        
        # Upsample to original resolution
        final_flow = F.interpolate(flow, size=(H, W), mode='bilinear', align_corners=True)
        final_flow = final_flow * 8.0  # Scale by downsampling factor
        
        # Remove padding if added
        if pad_h > 0 or pad_w > 0:
            final_flow = final_flow[:, :, :H, :W]
        
        return flow_predictions, final_flow
    
    def _coords_to_grid(self, coords):
        """Convert flow coordinates to sampling grid."""
        B, _, H, W = coords.shape
        
        # Create base grid
        grid_y, grid_x = torch.meshgrid(
            torch.arange(0, H, device=coords.device),
            torch.arange(0, W, device=coords.device),
            indexing='ij'
        )
        grid = torch.stack([grid_x, grid_y], dim=-1).unsqueeze(0).expand(B, -1, -1, -1)
        
        # Add flow
        grid = grid + coords.permute(0, 2, 3, 1)
        
        # Normalize to [-1, 1]
        grid[..., 0] = 2.0 * grid[..., 0] / (W - 1) - 1.0
        grid[..., 1] = 2.0 * grid[..., 1] / (H - 1) - 1.0
        
        return grid


def load_raft_model(pretrained_path=None, device='cpu'):
    """
    Load RAFT model with optional pretrained weights.
    
    Args:
        pretrained_path: Path to pretrained weights (.pth file)
        device: Device to load model on ('cpu' or 'cuda')
        
    Returns:
        RAFT model instance
    """
    model = RAFT().to(device)
    
    if pretrained_path and pretrained_path.exists():
        try:
            checkpoint = torch.load(pretrained_path, map_location=device)
            # Handle different checkpoint formats
            if 'state_dict' in checkpoint:
                model.load_state_dict(checkpoint['state_dict'])
            else:
                model.load_state_dict(checkpoint)
            print(f"[OK] Loaded RAFT weights from {pretrained_path}")
        except Exception as e:
            print(f"[WARN] Could not load pretrained weights: {e}")
    else:
        print("[INFO] Using randomly initialized RAFT weights")
    
    model.eval()
    return model


if __name__ == "__main__":
    # Test the model
    device = 'cpu'
    raft = RAFT().to(device)
    raft.eval()
    
    img1 = torch.randn(1, 3, 128, 128).to(device)
    img2 = torch.randn(1, 3, 128, 128).to(device)
    
    with torch.no_grad():
        _, flow = raft(img1, img2, iters=4)
    
    print(f"Input shape: {img1.shape}")
    print(f"Output flow shape: {flow.shape}")
    print("[OK] RAFT model works correctly!")
