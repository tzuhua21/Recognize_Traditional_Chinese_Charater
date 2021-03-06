# -*- coding: utf-8 -*-
"""Rec_Traditional_Chinese_Character_ResNet50.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Y1R2YiU3hV4T_mOouEqU9K89TRPbqedZ
"""

from google.colab import drive
drive.mount('/content/drive')

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/drive/MyDrive/
# 把資料生成工具 clone 下來
!git clone https://github.com/rachellin0105/Single_char_image_generator.git
# %cd Single_char_image_generator

# Single_char_image_generator/chars.txt 是字典，預設有102字，可以在上面增減字。這邊因為是示範，我們只留前10個字。
!head -n 10 chars.txt > temp.txt
!mv temp.txt chars.txt

# 安裝它需要的套件
!python -m pip install -r requirements.txt

# 用一行指令執行生成 
!python OCR_image_generator_single_ch.py --num_per_word=111

!mkdir test
!python OCR_image_generator_single_ch.py --num_per_word=21 --output_dir='test'

import torch
from torchvision import datasets, transforms, models
from torch import nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt
from tqdm import tqdm
import os
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt

if torch.cuda.is_available():
  device = torch.device('cuda:0')
  print('GPU')
else:
  device = torch.device('cpu')
  print('CPU')

class ChineseCharDataset(Dataset):
  def __init__(self, data_file, root_dir, dict_file):
    # data_file:  標註檔的路徑 (標註檔內容: ImagePath, GroundTruth)
    # root_dir: ImagePath所在的資料夾路徑
    # dict_file: 字典的路徑

    # 使用 pandas 將生成的單字labels.txt當作csv匯入進來
    self.char_dataframe = pd.read_csv(data_file, index_col=False, encoding='utf-8', header=None)
    self.root_dir = root_dir
    with open(dict_file, 'r', encoding='utf-8') as f:
      # 將資料集包含的字集匯入進來
      word_list = [line for line in f.read().split('\n') if line.strip() != '']
      self.dictionary = {word_list[i]: i for i in range(0, len(word_list))}

    print(self.char_dataframe)
    print(self.dictionary)

  def __len__(self):
    return len(self.char_dataframe)

  def __getitem__(self, idx):
    
    # 取得第idx張圖片的path，並將圖片打開
    image_path = os.path.join(self.root_dir, self.char_dataframe.iloc[idx, 0])
    image = Image.open(image_path)

    # 取得 Ground Truth 並轉換成數字
    char = self.char_dataframe.iloc[idx, 1]
    char_num = self.dictionary[char]

    
    return (transforms.ToTensor()(image), torch.Tensor([char_num]))

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/drive/MyDrive/Single_char_image_generator/

# 宣告好所有要傳入 ChineseCharDataset 的引數
data_file_path = '/content/drive/MyDrive/Single_char_image_generator/output/labels.txt'
root_dir = '/content/drive/MyDrive/Single_char_image_generator/'
dict_file_path = '/content/drive/MyDrive/Single_char_image_generator/chars.txt'

test_data_file_path = '/content/drive/MyDrive/Single_char_image_generator/test/labels.txt'


# 模型儲存位置
save_path = '/content/drive/MyDrive/Single_char_image_generator/checkpoint.pt'

# 宣告我們自訂的Dataset，把它包到 Dataloader 中以便我們訓練使用
char_dataset = ChineseCharDataset(data_file_path, root_dir, dict_file_path)
test_dataset = ChineseCharDataset(test_data_file_path, root_dir, dict_file_path)
char_dataloader = DataLoader(char_dataset, batch_size=12, shuffle=True, num_workers=4)
testloader = DataLoader(test_dataset, batch_size=12, shuffle=False, num_workers=2 )

# --- Training ---

# 我們使用torchvision提供的 ResNet-18 當作我們的AI模型。 
#net = models.resnet50(num_classes=10) # num_classes 為類別數量(幾種不一樣的字)
net = models.resnet50(pretrained=True)
#net = myNet()
net = net.to(device) # 傳入GPU
net.train()

optimizer = optim.Adam(net.parameters())

# 訓練總共Epochs數
epochs = 100

each_loss = []
best_acc = 0
no_improve = 0
pbar = tqdm(range(1, epochs + 1))
for i in pbar:
    losses = 0
    for idx, data in enumerate(char_dataloader):
        image, label = data
        image = image.to(device)
        label = label.squeeze() # 將不同batch壓到同一個dimension
        label = label.to(device, dtype=torch.long)
        
        optimizer.zero_grad()
        result = net(image)

        # 計算損失函數
        loss = F.cross_entropy(result, label)
        losses += loss.item()
        #if idx % 10 == 0:  # 每10個batch輸出一次
        #print(f'epoch {i}- loss: {loss.item()}')

        # 計算梯度，更新模型參數
        loss.backward()
        optimizer.step()

    avgloss = losses / len(char_dataloader)
    each_loss.append(avgloss)

    # Eval
    correct = 0
    total = 0

    with torch.no_grad():
        for data in testloader:
            image, label = data
            image = image.to(device)
            label = label.to(device)
    
            outputs = net(image)

            _, predicted = torch.max(outputs.data, 1)
            total += label.size(0)
            correct += (predicted.view(-1) == label.view(-1)).sum().item()
    epoch_acc = correct / total
    pbar.set_description(f'Epoch {i} / Avg Training loss: {avgloss} / Eval ACC = {(100 * epoch_acc):.2f}% / Best acc = {(100 * best_acc):.2f}%')

    if epoch_acc >= best_acc:
      best_acc = epoch_acc
      no_improve = 0
      # 儲存模型
      torch.save({
        'epoch': i,
        'model_state_dict': net.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),  
      }, save_path)
    else:
      no_improve += 1
    
    if no_improve >= 10:
      print(f'Model no improve for {no_improve} times!! Early Stop!')
      break


    print(f'{i}th epoch end. Avg loss: {avgloss}')

# 儲存模型
# torch.save({
#   'epoch': epochs,
#   'model_state_dict': net.state_dict(),
#   'optimizer_state_dict': optimizer.state_dict(),  
# }, save_path)

# 畫出訓練過程圖表 (Y_axis - loss / X_axis - epoch)
plt.plot(each_loss, '-b', label='loss')
plt.xlabel('epoch')
plt.ylabel('loss')
plt.legend()

correct = 0
total = 0

with torch.no_grad():
    for data in testloader:
        image, label = data
        image = image.to(device)
        label = label.to(device)
 
        outputs = net(image)

        _, predicted = torch.max(outputs.data, 1)
        total += label.size(0)
        correct += (predicted.view(-1) == label.view(-1)).sum().item()

print('Accuracy of the network on the test images: %d %%' % (100 * correct / total))
print(correct)
print(total)