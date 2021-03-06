# -*- coding: utf-8 -*-
"""
# Part1: Training
"""

import os
import numpy as np
import pandas as pd

# Commented out IPython magic to ensure Python compatibility.
# %matplotlib inline

# Python 2/3 compatibility
from __future__ import print_function, division

import itertools
import time

import numpy as np
import matplotlib.pyplot as plt

# Colors from Colorbrewer Paired_12
colors = [[31, 120, 180], [51, 160, 44]]
colors = [(r / 255, g / 255, b / 255) for (r, g, b) in colors]

def plot_losses(train_history, val_history):
    x = np.arange(1, len(train_history) + 1)

    plt.figure(figsize=(8, 6))
    plt.plot(x, train_history, color=colors[0], label="Training loss", linewidth=2)
    plt.plot(x, val_history, color=colors[1], label="Validation loss", linewidth=2)
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend(loc='upper right')
    plt.title("Evolution of the training and validation loss")
    plt.show()

data = pd.read_csv(os.getcwd() +"/cleaned_train.csv", sep=",")
Ids = data.values[:,1]
classes = np.unique(Ids)

len(classes)

#!/usr/bin/env python3

import csv
import os
from PIL import Image
import torch
from torch.utils.data import Dataset


def image_loader(path):
    with open(path, 'rb') as f:
        img = Image.open(f)
        return img.convert('RGB')


def load_labels(path):
    with open(path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)
        return [{
            headers[column_index]: row[column_index]
            for column_index in range(len(row))
        }
                for row in reader]


class CustomDataset(Dataset):

    def __init__(self, root, split='train', incr=None, transform=None):
        self.root = root = os.path.expanduser(root)
        category = 'id'
        self.category = category
        self.split = split
        self.incr = incr

        if incr is None:
          labels = load_labels(os.path.join(root, f'cleaned_{split}.csv'))
        else:
          labels = load_labels(os.path.join(root, split+str(incr)+'.csv'))

        self.entries = [
            (label_entry['Image'], int(label_entry[category]))
            for label_entry in labels
            if os.path.exists(
                os.path.join(self.root, f'{split}/{split}', label_entry['Image']))
        ]
        self.transform = transform

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index):
        image_filename, label = self.entries[index]

        image_filepath = os.path.join(self.root, f'{self.split}/{self.split}', image_filename)
        image = image_loader(image_filepath)
        if self.transform is not None:
            image = self.transform(image)

        return image, label

"""#### Data Augmentation & Data Normalization"""

import torch
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as F

import torchvision
import torchvision.transforms as transforms

num_workers = 2

# Data augmentation and normalization for training
# Just normalization for validation
transforms_train = transforms.Compose([
        transforms.Resize([224,224]), # Resizing the image
        transforms.RandomHorizontalFlip(), # Flip the data horizontally
        transforms.RandomVerticalFlip(), # Flip the data vertically 
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
transforms_val = transforms.Compose([
        transforms.Resize([224,224]),
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
transforms_oversampling = transforms.Compose([
        transforms.Resize([230,230]),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(15),
        transforms.CenterCrop(224),
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225))
    ])

train_set = CustomDataset(root = os.getcwd()+'/', transform=transforms_train)
for i in range(1,10):
  for j in range(i,10):
    train_set += CustomDataset(root = os.getcwd()+'/', incr=i, transform=transforms_oversampling)
train_loader = torch.utils.data.DataLoader(train_set, batch_size=128,  shuffle=True, num_workers=num_workers)
val_set = CustomDataset(root = os.getcwd()+'/', transform=transforms_val)
val_loader = torch.utils.data.DataLoader(val_set, batch_size=128,  shuffle=True, num_workers=num_workers)

len(train_set)

len(classes)

def imshow(inp):
    """Imshow for Tensor."""
    inp = inp.numpy().transpose((1, 2, 0))
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    inp = std * inp + mean
    inp = np.clip(inp, 0, 1)
    plt.imshow(inp)
    plt.pause(0.001)  # pause a bit so that plots are updated


# Get a batch of training data
inputs, labels = next(iter(train_loader))

# Make a grid from batch
out = torchvision.utils.make_grid(inputs[:4])

# print labels
print(' '.join('{:>10}'.format(classes[labels[j]]) for j in range(4)))

# image show
imshow(out)

"""#### Models"""

def _weights_init(m):
    classname = m.__class__.__name__
    if isinstance(m, nn.Linear) or isinstance(m, nn.Conv2d):
        init.kaiming_normal_(m.weight)

class LambdaLayer(nn.Module):
    def __init__(self, lambd):
        super(LambdaLayer, self).__init__()
        self.lambd = lambd

    def forward(self, x):
        return self.lambd(x)


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1, option='A'):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != planes:
            if option == 'A':
                """
                For CIFAR10 ResNet paper uses option A.
                """
                self.shortcut = LambdaLayer(lambda x:
                                            F.pad(x[:, :, ::2, ::2], (0, 0, 0, 0, planes//4, planes//4), "constant", 0))
            elif option == 'B':
                self.shortcut = nn.Sequential(
                     nn.Conv2d(in_planes, self.expansion * planes, kernel_size=1, stride=stride, bias=False),
                     nn.BatchNorm2d(self.expansion * planes)
                )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out


class ResNet(nn.Module):
    def __init__(self, block, num_blocks, num_classes=4246):
        super(ResNet, self).__init__()
        self.in_planes = 16

        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(16)
        self.layer1 = self._make_layer(block, 16, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 32, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 64, num_blocks[2], stride=2)
        self.linear = nn.Linear(64, num_classes)

        self.apply(_weights_init)

    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1]*(num_blocks-1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion

        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = F.avg_pool2d(out, out.size()[3])
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out

import torchvision.models as models

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# net = models.resnet152(pretrained=False) #Method 2
# net = models.resnet50(pretrained=False) #Method 3
net = models.resnet50(pretrained=True) #Method 4, best one
num_ftrs = net.fc.in_features

net.fc = nn.Linear(num_ftrs, 4246)

# net = ResNet(BasicBlock, [3, 3, 3]) #Method 1
net = net.to(device)

"""#### Loss function & Optimizer"""

import torch.optim as optim

def createLossAndOptimizer(net, learning_rate):
    # it combines softmax with negative log likelihood loss
    criterion = nn.CrossEntropyLoss()  
    optimizer = optim.SGD(net.parameters(), lr=learning_rate, momentum=0.9, weight_decay=1e-4)
    #optimizer = optim.Adam(net.parameters(), lr=learning_rate)
    return criterion, optimizer

"""#### Training Model 
Batch size = 128, number of epochs = 20, starting learning rate = 0.01

Save the trained model
"""

def train(net, batch_size, n_epochs, learning_rate):
    """
    Train a neural network and print statistics of the training
    
    :param net: (PyTorch Neural Network)
    :param batch_size: (int)
    :param n_epochs: (int)  Number of iterations on the training set
    :param learning_rate: (float) learning rate used by the optimizer
    """
    print("===== HYPERPARAMETERS =====")
    print("batch_size=", batch_size)
    print("n_epochs=", n_epochs)
    print("Starting learning_rate=", learning_rate)
    print("=" * 30)
    
    n_minibatches = len(train_loader)

    criterion, optimizer = createLossAndOptimizer(net, learning_rate)
    # Init variables used for plotting the loss
    train_history = []
    val_history = []

    training_start_time = time.time()
    best_error = np.inf
    best_model_path = os.getcwd()+"/best_model.pth"
    
    # Move model to gpu if possible
    net = net.to(device)
    scheduler = optim.lr_scheduler.MultiStepLR(optimizer, milestones=[17,19], gamma=0.1) # Decay LR by a factor of 0.1 after epoch 3 and 7
    for epoch in range(n_epochs):  # loop over the dataset multiple times

        running_loss = 0.0
        print_every = n_minibatches // 10
        start_time = time.time()
        total_train_loss = 0
        
        for i, (inputs, labels) in enumerate(train_loader):

            # Move tensors to correct device
            inputs, labels = inputs.to(device), labels.to(device)

            # zero the parameter gradients
            optimizer.zero_grad()

            # forward + backward + optimize
            with torch.set_grad_enabled(True):
                outputs = net(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()

            # print statistics
            running_loss += loss.item()
            total_train_loss += loss.item()

            # print every 10th of epoch
            if (i + 1) % (print_every + 1) == 0:    
                print("Epoch {}, {:d}% \t train_loss: {:.2f} took: {:.2f}s".format(
                      epoch + 1, int(100 * (i + 1) / n_minibatches), running_loss / print_every,
                      time.time() - start_time))
                running_loss = 0.0
                start_time = time.time()

        train_history.append(total_train_loss / len(train_loader))

        total_val_loss = 0
        # Do a pass on the validation set
        # We don't need to compute gradient,
        # we save memory and computation using torch.no_grad()
        with torch.no_grad():
          for inputs, labels in val_loader:
              # Move tensors to correct device
              inputs, labels = inputs.to(device), labels.to(device)
              # Forward pass
              predictions = net(inputs)
              val_loss = criterion(predictions, labels)
              total_val_loss += val_loss.item()
            
        val_history.append(total_val_loss / len(val_loader))
        # Save model that performs best on validation set
        if total_val_loss < best_error:
            best_error = total_val_loss
            torch.save(net.state_dict(), best_model_path)

        print("Validation loss = {:.2f}".format(total_val_loss / len(val_loader)))
        scheduler.step()

    print("Training Finished, took {:.2f}s".format(time.time() - training_start_time))
    
    # Load best model
    net.load_state_dict(torch.load(best_model_path))
    
    return train_history, val_history

# train the model
train_history, val_history = train(net, batch_size=128, n_epochs=20, learning_rate=0.01)

plot_losses(train_history, val_history)

"""See next part for testing and prediction """