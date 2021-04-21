# -*- coding: utf-8 -*-
"""projetCNN.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1JjGJzYXmf4-utSfB7-6Iy_6nv5A6O5BV
"""

pip install ptflops \
pip install pthflops \
pip install torchsummaryX

import time
import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms

import matplotlib.pyplot as plt
from torchsummaryX import summary
from prettytable import PrettyTable
from ptflops import get_model_complexity_info

"""## Variables globales"""

# Taille des batchs
size_batch = 16
nb_epoch = 120

"""### Affichage des informations du GPU alloué"""

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
!nvidia-smi

"""### Fonction qui calcule et détaille le nombre de paramètres (poids + biais) du modèle en fonction de ses couches"""

def count_parameters(model):
    print('\n')
    table = PrettyTable(["Modules", "Parameters"])
    total_params = 0
    for name, parameter in model.named_parameters():
        if not parameter.requires_grad: continue
        param = parameter.numel()
        table.add_row([name, param])
        total_params+=param

    table.add_row(['------------','------------'])
    table.add_row(['TOTAL',total_params])
    print(table) 
    print('\n')

"""### Création des ensembles d'entrainements et de tests :
  - Taille des batchs : voir la variable globale "size_batch"
  - Augmentation des données (Horizontal flip + Crop) uniquement pour le train set
"""

# Data augmentation 
# Only for training set
transform_train = transforms.Compose([ transforms.RandomHorizontalFlip(),
                                       transforms.RandomCrop(32, padding=4),
                                       transforms.ToTensor(),
                                       transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])

transform = transforms.Compose( [transforms.ToTensor(), 
                                 transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])

#Training set
trainset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transform_train)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=size_batch , shuffle=True, num_workers=2)

#Testing set
testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform)
testloader = torch.utils.data.DataLoader(testset, batch_size=size_batch, shuffle=False, num_workers=2)

classes = ('plane', 'car', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck')


# functions to show an image
def imshow(img):
    img = img / 2 + 0.5
    npimg = img.numpy()
    plt.imshow(np.transpose(npimg, (1, 2, 0)))
    plt.show()


# get some random training images
dataiter = iter(trainloader)
images, labels = dataiter.next()

"""### Création du modèle CNN, calcul de ses paramètres, et details de ses couches :
  - 3 blocs avec 2 couches de convolution pour chaque bloc (stride et padding à 1).
  - Max pooling (2,2) après chaque bloc.
  - 3 couches linéaires (fully connected layers).
  - Dropout avant chaque couche fully connected (5% - 25%). 
"""

# CNN class
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        #Convolution layer
        self.conv1 = nn.Conv2d(3, 24,  kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv2d(24, 24, kernel_size=3, stride=1, padding=1) 
        #---------------------------------------------------------------
        self.conv3 = nn.Conv2d(24, 32, kernel_size=3, stride=1, padding=1)      
        self.conv4 = nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1)
        #---------------------------------------------------------------
        self.conv5 = nn.Conv2d(32, 48, kernel_size=3, stride=1, padding=1)
        self.conv6 = nn.Conv2d(48, 48, kernel_size=3, stride=1, padding=1)

        #fully connected layer
        self.fc1 = nn.Linear(in_features=4*4*48, out_features=220)
        self.fc2 = nn.Linear(in_features=220, out_features=120) 
        self.fc3 = nn.Linear(in_features=120, out_features=10)

        #pooling
        self.pool = nn.MaxPool2d(2, 2)

        #Drop out
        self.dropout5 = nn.Dropout(0.05)
        self.dropout25 = nn.Dropout(0.25)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = self.pool(F.relu(self.conv2(x)))

        x = F.relu(self.conv3(x))
        x = self.pool(F.relu(self.conv4(x)))

        x = F.relu(self.conv5(x))
        x = self.pool(F.relu(self.conv6(x)))

        x = x.view(-1, 4*4*48)
        x = self.dropout5(x)
        x = F.relu(self.fc1(x))
        x = self.dropout25(x)
        x = F.relu(self.fc2(x))
        x = self.dropout25(x)
        x = F.log_softmax(self.fc3(x),dim = 1)
        return x

net = Net().to(device)

## Loss function
criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(net.parameters(), lr=0.001, momentum=0.9)

"""## Description et statistiques du modèle: 
  - Affichage des différentes couches du modèle
  - Affichage du nombre de paramètres de chaque couche en détails (weights/biais)
  - Affichage du nombre de MACs de chaque couche (multiply-accumulate operations)
  - Affichage du nombre total de MACs/FLOPs
"""

count_parameters(net)
get_model_complexity_info(net, (3, 32, 32), as_strings=True, print_per_layer_stat=True, verbose=True)

summary(net, torch.randn(1, 3, 32, 32).to(device)) 
print('\n')

"""## Fonction d'évalution du modèle (lancée après chaque époque d'entrainement) :
  - Evaluation du modèle
  - Affichage de la précision après l'époque
  - Affichage du loss après l'epoque
  - Affichage de la durée de l'epoque

"""

def evaluation(epoch=-1):
  correct = 0
  total = 0
  with torch.no_grad():
      for data in testloader:
          images, labels = data
          images = images.to(device)
          labels = labels.to(device)

          outputs = net(images)
          _, predicted = torch.max(outputs.data, 1)
          total += labels.size(0)
          correct += (predicted == labels).sum().item()

  if epoch < 0:
    print('[ INIT. ]  accuracy : %d%% ' % ((100 * correct / total)))

  return 100 * correct / total

"""
## Fonction qui permet de calculer la précision du réseau pour chaque classe d'images


"""

def class_accuracy():
  class_correct = list(0. for i in range(10))
  class_total = list(0. for i in range(10))
  with torch.no_grad():
      for data in testloader:
          images, labels = data
          images = images.to(device)
          labels = labels.to(device)
          outputs = net(images)
          _, predicted = torch.max(outputs, 1)
          c = (predicted == labels).squeeze()
          for i in range(4):
              label = labels[i]
              class_correct[label] += c[i].item()
              class_total[label] += 1


  for i in range(10):
      print('Accuracy of %5s : %2d %%' % (
          classes[i], 100 * class_correct[i] / class_total[i]))

"""## Entrainement du modèle
  - Evalution après chaque époque.
  - Affichage de la précision (train & test) + loss à chaque époque
  - Calcule du temps d'execution de chaque époque + temps total t'entrainement 
  - Renvoie les valeurs precisions (train/test) et de loss sous forme de vecteurs.
"""

def train(nb_epoch):
  train_accuracies = []
  test_accuracies = []
  losses = []
  print("start training ...\n")
  evaluation()                                              # First Evaluation (before training)  
  s_time = time.time()
  for epoch in range(nb_epoch):
      start = time.time()
      running_loss = 0.0
      correct = 0
      for i, data in enumerate(trainloader, 0):

          inputs, labels = data                           
          inputs = inputs.to(device)                     
          labels = labels.to(device)             

          optimizer.zero_grad()

          outputs = net(inputs)                     
          loss = criterion(outputs, labels)           
          loss.backward()                              
          optimizer.step()                       

          running_loss += loss.item()            

          _, predicted = torch.max(outputs.data, 1)
          correct += (predicted == labels).sum().item()    


      test_acc = evaluation(epoch+1)                        # Test accuracy
      train_acc = 100 * correct / len(trainset)             # Train accuracy

      print('[epoch %d] train accuracy: %.0f%%  test accuracy: %.0f%%  loss: %.3f  duration: %.2f ' % ( epoch+1, 
                                                                                                        train_acc, test_acc, 
                                                                                                        running_loss / len(trainloader), 
                                                                                                        time.time() - start ) )

      # storing accuracies and loss
      test_accuracies.append(test_acc)
      train_accuracies.append(train_acc)
      losses.append(running_loss / len(trainloader))

  print('\nTraining finished in', time.strftime('%Hh %Mmin %Ssec', time.gmtime(time.time() - s_time )) )
  return (train_accuracies, test_accuracies, losses)

train_acc, test_acc, losses = train(nb_epoch)

evaluation()
print('\n')
class_accuracy()