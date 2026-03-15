import torch
import torch.nn as nn
import torch.nn.functional as F

class FlowHead(nn.Module):
    def __init__(self, input_dim=128, hidden_dim=256):
        super(FlowHead, self).__init__()
        self.conv1 = nn.Conv2d(input_dim, hidden_dim, 3, padding=1)
        self.conv2 = nn.Conv2d(hidden_dim, 2, 3, padding=1)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.conv2(self.relu(self.conv1(x)))

class UpdateBlock(nn.Module):
    def __init__(self, hidden_dim=128, input_dim=128):
        super(UpdateBlock, self).__init__()
        self.conv1 = nn.Conv2d(input_dim + 2, hidden_dim, 3, padding=1)
        self.conv2 = nn.Conv2d(hidden_dim, hidden_dim, 3, padding=1)
        self.flow_head = FlowHead(hidden_dim)

    def forward(self, net, flow):
        x = torch.cat([net, flow], dim=1)
        net = self.conv2(F.relu(self.conv1(x)))
        dflow = self.flow_head(net)
        return net, dflow

class BasicEncoder(nn.Module):
    def __init__(self, output_dim=128):
        super(BasicEncoder, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, 7, stride=2, padding=3)
        self.conv2 = nn.Conv2d(64, 128, 3, stride=2, padding=1)
        self.conv3 = nn.Conv2d(128, output_dim, 3, stride=2, padding=1)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))
        x = self.relu(self.conv3(x))
        return x

class RAFT(nn.Module):
    def __init__(self):
        super(RAFT, self).__init__()
        self.hidden_dim = 128
        self.context_dim = 128
        
        self.fnet = BasicEncoder(output_dim=256)        
        self.cnet = BasicEncoder(output_dim=256)
        self.update_block = UpdateBlock(hidden_dim=self.hidden_dim)

    def forward(self, image1, image2, iters=12):
        fmap1 = self.fnet(image1)
        fmap2 = self.fnet(image2)
        
        # Simplified correlation (dot product)
        # In full RAFT this is a correlation volume
        corr = torch.sum(fmap1 * fmap2, dim=1, keepdim=True)
        
        # Context network
        cnet = self.cnet(image1)
        net, inp = torch.split(cnet, [self.hidden_dim, self.context_dim], dim=1)
        net = torch.tanh(net)

        coords0 = torch.zeros_like(fmap1[:, :2])
        coords1 = torch.zeros_like(fmap1[:, :2])

        flow_predictions = []
        for i in range(iters):
            coords1 = coords1.detach()
            # Simplified update block input
            net, dflow = self.update_block(net, coords1)
            coords1 = coords1 + dflow
            flow_predictions.append(coords1)

        # Upsample flow (simplified)
        final_flow = F.interpolate(coords1, scale_factor=8, mode='bilinear', align_corners=True)
        return flow_predictions, final_flow
