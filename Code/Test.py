# -*- coding: utf-8 -*-
"""
# Part2: Testing
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

import torch
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as F

import torchvision
import torchvision.transforms as transforms

num_workers = 2

transforms_val = transforms.Compose([
        transforms.Resize([224,224]),
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

val_set = CustomDataset(root = os.getcwd()+'/', transform=transforms_val)
val_loader = torch.utils.data.DataLoader(val_set, batch_size=128, num_workers=num_workers, shuffle=True)
test_set = CustomDataset(root = os.getcwd()+'/', split='test', transform=transforms_val)
test_loader = torch.utils.data.DataLoader(test_set, batch_size=128, num_workers=num_workers, shuffle=True)

len(test_set)

"""#### Load Trained Net"""

import torchvision.models as models

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

net = models.resnet50(pretrained=False)
num_ftrs = net.fc.in_features

net.fc = nn.Linear(num_ftrs, 4246)

net.load_state_dict(torch.load(os.getcwd()+"/best_model.pth"))

net = net.to(device) # Move model to gpu if possible

"""#### Mean Average Precision Computation 

Mean average precision of the network on the 9060 validation images is 
0.9987398822663722.
"""

def map5(data_loader):
  """
  The Mean Average Precision @ 5
  """
  scores = 0.0
  net.eval()
  for images, labels in data_loader:
    images, labels = images.to(device), labels.to(device)
    with torch.no_grad():
      output = net(images)
      _,indices5 = output.topk(5)  
    for i in range(len(labels)):
      if indices5[i][0] == labels[i]:
        scores += 1.0
      elif indices5[i][1] == labels[i]:
        scores += 1/2
      elif indices5[i][2] == labels[i]:
        scores += 1/3
      elif indices5[i][3] == labels[i]:
        scores += 1/4
      elif indices5[i][4] == labels[i]:
        scores += 1/5

  scores = scores / 9060
  return scores

map5(val_loader)

"""#### Label Prediction """

def imshow(inp):
    """Imshow for Tensor."""
    inp = inp.numpy().transpose((1, 2, 0))
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    inp = std * inp + mean
    inp = np.clip(inp, 0, 1)
    plt.imshow(inp)
    plt.pause(0.001)  # pause a bit so that plots are updated
    
try:
  images, labels = next(iter(val_loader))
except EOFError:
  pass

# print images
print("Ground truth:\n")

imshow(torchvision.utils.make_grid(images[:4]))

print(' '.join('{:>10}'.format(classes[labels[j]]) for j in range(4)))

outputs = net(images[:4].to(device))
print(outputs.size())

_, predicted = torch.max(outputs, 1)

print("Predicted:\n")
imshow(torchvision.utils.make_grid(images[:4]))

print(' '.join('{:>10}'.format(classes[predicted[j]]) for j in range(4)))

preds = []
for images, labels in test_loader:
  images, labels = images.to(device), labels.to(device)
  with torch.no_grad():
    output = net(images)
    _,indices5 = output.topk(5)
  for i in indices5:
    predicted = classes[i[0]]+' '+classes[i[1]]+' '+classes[i[2]]+' '+classes[i[3]]+' '+classes[i[4]]
    preds.append(predicted)

"""#### Submit File Generation """

submit = pd.read_csv(os.getcwd()+"/cleaned_test.csv", sep=",")
submit['Id'] = preds
submit = submit.drop(columns='id')
submit

submit.to_csv("submit.csv", index=False)