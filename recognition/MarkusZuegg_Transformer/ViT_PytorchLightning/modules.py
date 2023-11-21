"""
This file contains the main modules and architecture of the ViT
Attention block / layers of encoder and encoder class
"""
import torch
import torch.nn as nn
from dataset import img_to_patch

class AttentionBlock(nn.Module):
    def __init__(self, embed_dim, hidden_dim, num_heads, dropout=0.0):
        """Attention Block.

        Args:
            embed_dim: Dimensionality of input and attention feature vectors
            hidden_dim: Dimensionality of hidden layer in feed-forward network
            num_heads: Number of heads to use in the Multi-Head Attention block
            dropout: Amount of dropout
        """
        super().__init__()

        self.layer_norm_1 = nn.LayerNorm(embed_dim)
        self.attn = nn.MultiheadAttention(embed_dim, num_heads)
        self.layer_norm_2 = nn.LayerNorm(embed_dim)
        self.linear = nn.Sequential(
            nn.Linear(embed_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, embed_dim),
            nn.Dropout(dropout),)

    def forward(self, x):
        inp_x = self.layer_norm_1(x)
        x = x + self.attn(inp_x, inp_x, inp_x)[0] #only taking first tensor 
        x = x + self.linear(self.layer_norm_2(x))
        return x 
class VisionEncoder(nn.Module):
    def __init__(self,
                embed_dim,
                hidden_dim,
                num_channels,
                num_heads,
                num_layers,
                num_classes,
                patch_size,
                image_size,
                dropout=0.0,):
        """Vision Encoder.

        Args:
            embed_dim: Dimensionality of the input feature vectors
            hidden_dim: Dimensionality of the hidden layer
            num_channels: Number of channels of the input
            num_heads: Number of heads to use in the Multi-Head Attention block
            num_layers: Number of layers to use in the Encoder
            num_classes: Number of classes to predict
            image_size: List of image dimensions (height, width)
            num_patches: Maximum number of patches an image can have
            dropout: Amount of dropout to apply in the feed-forward network
        """
        super().__init__()

        # Initallise variables
        self.patch_size = patch_size
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.num_dropout = dropout

        # Calculating number of patches given patch_size and image dimensions
        num_patches = (image_size[0]//self.patch_size) * (image_size[1]//self.patch_size)

        # =====Layers/Networks===== #
        self.input_layer = nn.Linear(num_channels * (patch_size**2), embed_dim)
        # Encoder layers
        self.encoder = self._make_layers()
        # MLP head used for classification
        self.mlp_head = nn.Sequential(nn.LayerNorm(embed_dim), nn.Linear(embed_dim, num_classes))
        self.dropout = nn.Dropout(dropout)

        # Parameters/Embeddings
        self.cls_token = nn.Parameter(torch.randn(1, 1, embed_dim))
        self.pos_embedding = nn.Parameter(torch.randn(1, 1 + num_patches, embed_dim))
    
    def _make_layers(self):
        """Makes a list of Attention blocks"""
        layers = []
        for _ in range(self.num_layers):
            layers.append(AttentionBlock(self.embed_dim, 
                                         self.hidden_dim, 
                                         self.num_heads, 
                                         dropout=self.num_dropout))
        return nn.Sequential(*layers)

    def forward(self, x):
        """
        Loop that every img batch will be fed through
        """
        # Preprocess input
        x = img_to_patch(x, self.patch_size)
        B, T, _ = x.shape
        x = self.input_layer(x)

        # Add CLS token
        cls_token = self.cls_token.repeat(B, 1, 1)
        x = torch.cat([cls_token, x], dim=1)

        # Add positional encoding
        x = x + self.pos_embedding[:, : T + 1]

        # Apply Transforrmer
        x = self.dropout(x)
        x = x.transpose(0, 1)
        x = self.encoder(x)

        # Perform classification prediction
        cls = x[0]
        out = self.mlp_head(cls)
        return out
