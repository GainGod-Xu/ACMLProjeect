from torch import nn
import torch.nn.functional as F
from CMRPModels.Encoder import Encoder
from CMRPModels.Projection import Projection
class CMRPModel(nn.Module):
    def __init__(
        self,
        mr1_model,
        mr2_model,
        CMRPConfig
    ):
        super().__init__()
        self.mr1_encoder = Encoder(mr1_model, CMRPConfig.mr1_model_trainable)
        self.mr2_encoder = Encoder(mr2_model, CMRPConfig.mr2_model_trainable)
        self.mr1_name = CMRPConfig.mr1_name
        self.mr2_name = CMRPConfig.mr2_name
        self.temperature = CMRPConfig.temperature
        self.device = CMRPConfig.device
        self.batch_size = CMRPConfig.batch_size
        self.mr1_projection = Projection(CMRPConfig.mr1_model_embedding, CMRPConfig.projection_dim, CMRPConfig.dropout)
        self.mr2_projection = Projection(CMRPConfig.mr2_model_embedding, CMRPConfig.projection_dim, CMRPConfig.dropout)

    def forward(self, batch):

        # Getting pre-Embeddings(features) of mr1 and mr2 from Encoders (acceptable with different dimension)

        ## (deprecated)
        # batch_mr1 = batch[self.mr1_name]
        # batch_mr2 = batch[self.mr2_name]
        #
        # # do not load smiles data to device.
        # if not self.mr1_name == "smiles":
        #     batch_mr1 = batch_mr1.to(self.device)
        # if not self.mr2_name == "smiles":
        #     batch_mr2 = batch_mr2.to(self.device)
        #
        # mr1_features = self.mr1_encoder(batch_mr1)
        # mr2_features = self.mr2_encoder(batch_mr2)

        mr1_features = self.mr1_encoder(batch[self.mr1_name].to(self.device))
        mr2_features = self.mr2_encoder(batch[self.mr2_name].to(self.device))

        # Getting post-Embeddings of mr1 and mr2 from Projection (mandatory with same dimension)
        mr1_embeddings = self.mr1_projection(mr1_features)
        mr2_embeddings = self.mr2_projection(mr2_features)

        # Calculating the Loss
        logits = (mr1_embeddings @ mr2_embeddings.T) / self.temperature
        mr1_similarity = mr1_embeddings @ mr1_embeddings.T
        mr2_similarity = mr2_embeddings @ mr2_embeddings.T
        targets = F.softmax(
            (mr1_similarity + mr2_similarity) / 2 * self.temperature, dim=-1
        )
        mr1_loss = cross_entropy(logits, targets, reduction='none')
        mr2_loss = cross_entropy(logits.T, targets.T, reduction='none')
        loss = (mr1_loss + mr2_loss)/2  # shape: (batch_size)
        return loss.mean(), mr1_embeddings, mr2_embeddings

def cross_entropy(preds, targets, reduction='none'):
    log_softmax = nn.LogSoftmax(dim=-1)
    loss = (-targets * log_softmax(preds)).sum(1)
    if reduction == "none":
        return loss
    elif reduction == "mean":
        return loss.mean()
