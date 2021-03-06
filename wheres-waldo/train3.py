from math import sqrt
import torch
import matplotlib.pyplot as plt
from torch.utils.data.dataset import ConcatDataset
from torchvision.transforms.functional import to_pil_image
from datasets import WaldoDataset
from models import BaselineCNN, SimpleCNN, TransferModel, UNet
from torch.utils.data import DataLoader
from tqdm import tqdm
import wandb
from transforms import Compose, RandomCrop, ToTensor, RandomScale

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

WIDTH, HEIGHT = 32, 32

train_dataset = WaldoDataset(transform=Compose([
  RandomScale((0.8, 1.2)),
  RandomCrop(size=(WIDTH, HEIGHT)),
  ToTensor()
]))

batch_size = 64

test_dataset = WaldoDataset(test=True, transform=ToTensor())
test_data = DataLoader(test_dataset, batch_size=1, shuffle=False)
train_data = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=24)

model = TransferModel().to(device) #BaselineCNN(in_channels=3).to(device)
model.load_state_dict(torch.load("model.torch", map_location=device)) # Load model

num_epochs = 50
learning_rate = 1e-3
optim = torch.optim.Adam(model.parameters(), lr=learning_rate)
#pos_weight = torch.full((HEIGHT, WIDTH), 50).to(device) # Weight positive examples more.
criterion = torch.nn.BCEWithLogitsLoss() 

loss_history = []

wandb.init(project="wheres-waldo", entity="andersthuesen")

wandb.config = {
  'num_epochs': num_epochs,
  'learning_rate': learning_rate
}


try:
  
  for epoch in range(num_epochs):
    print(f"Training epoch {epoch + 1}")

    model.train()
    tqdm_train_data = tqdm(train_data)
    for image, mask, coord, visible in tqdm_train_data:
      image, mask, visible = image.to(device), mask.to(device), visible.float().to(device)

      optim.zero_grad()
      pred_visible = model(image).view(-1)

      loss = criterion(pred_visible, visible)
      loss.backward()

      loss_history.append(loss.item())
      wandb.log({'loss': loss.item()})

      tqdm_train_data.set_description(f"Loss: {loss.item():.4f}")
      optim.step()


    # print(f"Testing epoch {epoch + 1}")
    # model.eval()
    # error = 0
    # for image, _, (x, y) in test_data:
    #   image = image.to(device) # Add 
    #   logits = model(image)

    #   preds = torch.argmax(logits.reshape(logits.shape[0], -1), dim=1)

    #   px = (preds % image.shape[3]).item()
    #   py = (preds / image.shape[2]).item()

    #   error += sqrt((x - px) ** 2 + (y - py) ** 2) / len(test_dataset)

    # print("Mean euclidean distance is {}".format(error))
    # wandb.log({ 'mean-euclidean': error })

except Exception as e:
  print(e)
  pass


torch.save(model.state_dict(), "model.torch")
