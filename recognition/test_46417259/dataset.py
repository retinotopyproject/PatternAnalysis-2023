import torch
import torch.utils.data
import torchvision.datasets as dset
import torchvision.transforms.v2 as transforms
import torchvision.utils as vutils
import numpy as np
import matplotlib.pyplot as plt
import random

# global variables
batch_size = 128
workers = 0

# file paths
train_path = '/Users/minhaosun/Documents/COMP3710_local/data/AD_NC/train'
test_path = '/Users/minhaosun/Documents/COMP3710_local/data/AD_NC/test'

# transforms
train_transforms = transforms.Compose([
    transforms.ToTensor(),
    transforms.CenterCrop(240),
])

test_transforms = transforms.Compose([
    transforms.ToTensor(),
    transforms.CenterCrop(240),
])

class PairedDataset(torch.utils.data.Dataset):
    def __init__(self, image_folder:dset.ImageFolder, show_debug_info:bool, random_seed=None) -> None:
        super().__init__()
        self.image_folder = image_folder
        self.image_folder_size = len(self.image_folder)
        self.debug_mode = show_debug_info

        # for reproducibility
        if random_seed is not None:
            random.seed(random_seed)
            torch.random.seed(random_seed)

    def __len__(self) -> int:
        return self.image_folder_size

    def __getitem__(self, index: int):
        img1, label1 = self.image_folder[index]
        similarity = random.randint(0, 1)

        match_found = False
        while not match_found:
            choice = random.randint(0, self.image_folder_size - 1)
            # make sure we do not pair the same image against itself
            if choice == index:
                continue

            img2, label2 = self.image_folder[choice]
            if similarity == 1:
                match_found = label1 == label2
            else:
                match_found = label1 != label2

        # only include the filepaths in the dataset if specifically requested
        if self.debug_mode:
            filepath1 = self.image_folder.imgs[index][0]
            filepath2 = self.image_folder.imgs[choice][0]
            return img1, img2, similarity, filepath1[-20:-5], filepath2[-20:-5]
        # otherwise save some memory
        return img1, img2, similarity
    
    def showing_debug_info(self) -> bool:
        return self.debug_mode


def load_train() -> torch.utils.data.DataLoader:
    # load the trainset
    trainset = dset.ImageFolder(root=train_path,
                                transform=train_transforms
                            )
    print(f'trainset has classes {trainset.class_to_idx} and {len(trainset)} images')

    trainloader = torch.utils.data.DataLoader(trainset, batch_size=batch_size,
                                            shuffle=True, num_workers=workers)
    
    return trainloader

def load_test() -> torch.utils.data.DataLoader:
    # load the testset
    testset = dset.ImageFolder(root=test_path,
                            transform=test_transforms
                            )
    print(f'testset has classes {testset.class_to_idx} and {len(testset)} images')

    testloader = torch.utils.data.DataLoader(testset, batch_size=batch_size,
                                            shuffle=True, num_workers=workers)
    
    return testloader

def test_visualise_data(dataloader: torch.utils.data.DataLoader):
    # Plot some training images
    next_batch = next(iter(dataloader))
    print(next_batch[0][0].shape)
    # plt.figure(figsize=(8,8))
    # plt.axis("off")
    # plt.title("Training Images")
    # plt.imshow(np.transpose(vutils.make_grid(train_batch[0].to(device)[:64], padding=2, normalize=True).cpu(),(1,2,0)))
    # plt.show()

    # the following data visualisation code is modified based on code at
    # https://github.com/pytorch/tutorials/blob/main/beginner_source/basics/data_tutorial.py
    # published under the BSD 3-Clause "New" or "Revised" License
    # full text of the license can be found in this project at BSD_new.txt
    figure = plt.figure(figsize=(8, 8))
    cols, rows = 3, 3

    labels_map = {0: 'AD', 1: 'NC'}

    for i in range(1, cols * rows + 1):
        figure.add_subplot(rows, cols, i)
        plt.title(labels_map[next_batch[1][i].tolist()])
        plt.axis("off")
        plt.imshow(np.transpose(next_batch[0][i].squeeze(), (1,2,0)), cmap="gray")
    plt.show()

def visualise_paired_data(dataset: PairedDataset):
    if not dataset.showing_debug_info():
        raise NotImplementedError("PairedDataset must be initialised with show_debug_info=True")

    testloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size,
                                            shuffle=True, num_workers=workers)
        
    next_batch = next(iter(testloader))
    print(next_batch[0][0].shape)
    print(next_batch[0][1].shape)

    cols, rows = 3, 3
    fig, axs = plt.subplots(rows, cols * 2)
    labels_map = {0: 'diff', 1: 'same'}

    for i in range(rows):
        for j in range(cols):
            axs[i,j*2].imshow(np.transpose(next_batch[0][i*rows+j].squeeze(), (1,2,0)), cmap="gray")
            axs[i,j*2+1].imshow(np.transpose(next_batch[1][i*rows+j].squeeze(), (1,2,0)), cmap="gray")
            axs[i,j*2].set_title(f"""{labels_map[next_batch[2][i*rows+j].tolist()]}, {next_batch[3][i*rows+j]}""")
            axs[i,j*2+1].set_title(next_batch[4][i*rows+j])
            axs[i,j*2].axis("off")
            axs[i,j*2+1].axis("off")
    plt.show()

def test_paired_dataset():
    source = dset.ImageFolder(root=train_path,
                                transform=train_transforms
                            )
    test = PairedDataset(source, show_debug_info=True)
    print(len(test))
    print(len(source))
    visualise_paired_data(test)


# Decide which device we want to run on
device = torch.device("cuda:0" if torch.cuda.is_available() else "mps")
print("Device: ", device)

test_paired_dataset()

# load_train()
# test_visualise_data(load_train())
# test_visualise_data(load_test())
