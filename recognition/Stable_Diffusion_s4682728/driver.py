from imports import *
from utils import *
from dataset import *
from modules import *
from train import *
from predict import *

############################################################
# SETTING UP

# Set the number of training epochs
EPOCHS = 100
BATCH_SIZE = 16

# Initialize the Diffusion Network model and setup the optimizer
model = DiffusionNetwork().to(device)
optimizer = optim.Adam(model.parameters(), lr=1e-3)

# Define paths for saving the model and plots
save_model_path = f"diffusion_network{EPOCHS}.pth"
save_plot_path = os.path.expanduser(f"~/demo_eiji/sd/plots/training_loss{EPOCHS}.png")
save_image_path = os.path.expanduser(f"~/demo_eiji/sd/images/image_visualization{EPOCHS}.png")

############################################################
# TRAINING THE MODEL

# Train and save the model
train_diffusion_network(model, 
                        optimizer, 
                        epochs=EPOCHS,
                        batch_size=BATCH_SIZE, 
                        save_path=save_model_path, 
                        plot_path=save_plot_path)

############################################################
# GENERATING IMAGES

# Load the trained model parameters
model = DiffusionNetwork() 
model.load_state_dict(torch.load(f"diffusion_network{EPOCHS}.pth")) 
model.to(device)
model.eval()

# Generate images and save the result
image_generation(model, save_path=save_image_path)
