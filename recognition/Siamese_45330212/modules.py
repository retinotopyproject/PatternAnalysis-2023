# Contains the source code of the components of your model. Each component must be
# implementated as a class or a function
# Import all the necessary libraries
import torchvision
import torch.utils.data as utils
from torchvision import datasets
import torchvision.transforms as transforms
from torch.utils.data import DataLoader,Dataset
from torch.autograd import Variable
import matplotlib.pyplot as plt
import torchvision.utils
import numpy as np
import os
import torch
import torch.nn as nn
import torch.nn.functional as F

# Configuration class to store paths and hyperparameters
class Config():
    # /home/Student/s4533021/siamese_model.pt
    # C:\\Users\\david\\OneDrive\\Documents\\0NIVERSITY\\2023\\SEM2\\COMP3710\\Project\\PatternAnalysis-2023\\recognition\\Siamese_45330212\\AD_NC\\train
    # Directory paths and batch sizes for different processes
    training_dir = '/home/Student/s4533021/AD_NC/train'
    testing_dir = '/home/Student/s4533021/AD_NC/test'
    siamese_train_batch_size = 12
    train_batch_size = 40
    siamese_number_epochs = 19
    train_number_epochs = 19

# --------------
# Model
# Basic building block for ResNet
class BasicBlock(nn.Module):
    expansion = 1 # Expansion factor for channels

    def __init__(self, in_planes, planes, stride=1):
        super(BasicBlock, self).__init__()
        # First convolution layer
        self.conv1 = nn.Conv2d(
            in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)

        # Second convolution layer
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)

        # Shortcut connections
        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion*planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion*planes,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion*planes)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x) # Adding the shortcut
        out = F.relu(out)
        return out

# ResNet architecture
class ResNet(nn.Module):
    # Initialization
    def __init__(self, block, num_blocks):
        super(ResNet, self).__init__()
        self.in_planes = 64

        # Initial Convolution
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)

        # Layers
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)

        # Final Linear Layer
        self.linear = nn.Linear(28672*block.expansion, 6144) # 28672 6144

    # Create a layer with `num_blocks` blocks
    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1]*(num_blocks-1) # First layer may downsample
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers) # Stack them together

    # Forward pass for one input
    def forward_once(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = F.avg_pool2d(out, 4)
        out = out.view(out.size(0), -1)
        # out = self.linear(out)
        return out
    
    # Forward pass for anchor, positive and negative
    def forward(self, anchor, pos, neg):
        # forward pass of anchor
        output_anchor = self.forward_once(anchor)
        # forward pass of pos
        output_pos = self.forward_once(pos)
        # forward pass of neg
        output_neg = self.forward_once(neg)
        return output_anchor, output_pos, output_neg
    
# Binary classifier to identify classes
class BinaryClassifier(nn.Module):
    def __init__(self):
        super(BinaryClassifier, self).__init__()
        self.hidden1 = nn.Linear(28672, 1024)
        self.hidden2 = nn.Linear(1024, 64)
        # self.hidden3 = nn.Linear(256, 64)
        self.output = nn.Linear(64, 2)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.5)  # Adding dropout layer
        self.batch_norm1 = nn.BatchNorm1d(1024)  # Adding batch normalization
        self.batch_norm2 = nn.BatchNorm1d(64) #256
        self.batch_norm3 = nn.BatchNorm1d(64)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.hidden1(x)
        x = self.batch_norm1(x)
        x = self.relu(x)
        x = self.dropout(x)

        x = self.hidden2(x)
        x = self.batch_norm2(x)
        x = self.relu(x)
        x = self.dropout(x)

        # x = self.hidden3(x)
        # x = self.batch_norm3(x)
        # x = self.relu(x)
        # x = self.dropout(x)

        x = self.output(x)
        x = self.sigmoid(x)
        return x

# Function to create a ResNet18 model
def ResNet18():
    return ResNet(BasicBlock, [2, 2, 2, 2])

# Contrastive loss for Siamese networks (Not currently used)
class ContrastiveLoss(torch.nn.Module):
    """
    Contrastive loss function.
    Based on formula provided during symposium.
    """

    def __init__(self, margin=2.0):
        super(ContrastiveLoss, self).__init__()
        self.margin = margin

    def forward(self, output1, output2, label):
        euclidean_distance = F.pairwise_distance(output1, output2)
        loss_contrastive = torch.mean((1-label) * torch.pow(euclidean_distance, 2) +
                                      (label) * torch.pow(torch.clamp(self.margin - euclidean_distance, min=0.0), 2))
        return loss_contrastive

# Triplet loss function for the network
class TripletLoss(torch.nn.Module):
    def __init__(self, margin=1.0):
        super(TripletLoss, self).__init__()
        self.margin = margin
    
    def forward(self, anchor: torch.Tensor, positive: torch.Tensor, negative: torch.Tensor) -> torch.Tensor:
        distance_positive = F.pairwise_distance(anchor, positive)
        distance_negative = F.pairwise_distance(anchor, negative)
        losses = torch.relu(distance_positive - distance_negative + self.margin) #This acts like a max(0, ...) function
        return losses.mean()