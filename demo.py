import torch
from torch.utils.data import DataLoader
import torchvision.models as models
import matplotlib.pyplot as plt
import imageio
import os

from dataset.dataset_class import DemoImagesDataset
from network.model import Generator

from params.params import (
    frame_shape, path_to_pose_img, path_to_pose_video,
    path_to_identity_embedding, path_to_finetuned_model)

"""Hyperparameters and config"""
batch_size = 1
device = torch.device("cuda:0")
cpu = torch.device("cpu")
path_to_images = path_to_pose_img
if not os.path.exists(path_to_images):
    from dataset.preprocess import save_to_file
    save_to_file(path_to_pose_video, path_to_pose_img)

path_to_embedding = path_to_identity_embedding
path_to_save = path_to_finetuned_model

checkpoint = torch.load(path_to_save, map_location=cpu)
ei_hat = torch.load(path_to_embedding, map_location=cpu)
ei_hat = ei_hat['ei'].to(device)

G = Generator(frame_shape)
G.eval()

Ep = models.mobilenet_v2(num_classes=256).to(device)
Ep.eval()

dataset = DemoImagesDataset(path_to_images, device)
dataLoader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

"""Training Init"""
G.load_state_dict(checkpoint['G_state_dict'])
Ep.load_state_dict(checkpoint['Ep_state_dict'])

G.to(device)
Ep.to(device)

"""Main"""
os.makedirs('vis', exist_ok=True)
with imageio.get_writer('vis/gif.gif', mode='I', fps=30) as writer:
    with torch.no_grad():
        for i_batch, x in enumerate(dataLoader):
            print(i_batch)
            x = x.to(device)
            
            ep_hat = Ep(x)
            e_hat = torch.cat([ei_hat.expand(ep_hat.shape[0], 512), ep_hat], dim=1).unsqueeze(-1) #B,768
            
            is_hat = G(e_hat)
            i_hat = is_hat[:,:3]
            s_hat = is_hat[:,3,None]
            
            x_hat = torch.mul(i_hat, s_hat)
            
            outx = torch.cat([i.permute(1,2,0) for i in x], dim=1) * 255
            outxhat = torch.cat([i.permute(1,2,0) for i in x_hat], dim=1) * 255
            out = torch.cat([outx, outxhat], dim=0)
            out = out.type(torch.uint8).to(cpu).numpy()
            plt.imsave("vis/{:07d}.png".format(i_batch), out)
            writer.append_data(out)