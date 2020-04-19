import torch
import torch.nn as nn
import torch.nn.functional as F


class KCNN(torch.nn.Module):
    """
    Knowledge-aware CNN (KCNN) based on Kim CNN.
    Input a news sentence (e.g. its title), produce its embedding vector.
    """
    def __init__(self, config):
        super(KCNN, self).__init__()
        self.config = config
        self.word_embedding = nn.Embedding(self.config.num_word_tokens,
                                           self.config.word_embedding_dim)
        self.transform_matrix = nn.Parameter(
            torch.empty(self.config.entity_embedding_dim,
                        self.config.word_embedding_dim))
        self.transform_bias = nn.Parameter(
            torch.empty(self.config.word_embedding_dim))

        self.conv_filters = nn.ModuleDict({
            str(x): nn.Conv2d(3, self.config.filter_out_channels,
                              (x, self.config.word_embedding_dim))
            for x in self.config.window_sizes
        })

        self.transform_matrix.data.uniform_(-0.1, 0.1)
        self.transform_bias.data.uniform_(-0.1, 0.1)

    def forward(self, news):
        """
        Args:
          news:
            {
                "word": [Tensor(batch_size) * num_words_a_sentence],
                "entity":[Tensor(batch_size) * num_words_a_sentence]
            }

        Returns:
          batch_size * (len(window_sizes) * filter_out_channels)
        """
        word = torch.stack(news["word"]).transpose(0, 1)  # 64, 10
        word_vector = self.word_embedding(word)  # 64, 10, 100
        entity = torch.stack(news["entity"]).transpose(0, 1)  # 64, 10
        # TODO ei and ei2 are set as zero if wi has no corresponding entity

        # TODO
        entity_vector = torch.rand(
            self.config.batch_size, self.config.num_words_a_sentence,
            self.config.entity_embedding_dim)  # 64, 10, 80
        context_vector = torch.rand(
            self.config.batch_size, self.config.num_words_a_sentence,
            self.config.entity_embedding_dim)  # 64, 10, 80
        transformed_entity_vector = torch.tanh(
            torch.matmul(entity_vector, self.transform_matrix) +
            self.transform_bias)  # 64, 10, 100
        transformed_context_vector = torch.tanh(
            torch.matmul(context_vector, self.transform_matrix) +
            self.transform_bias)  # 64, 10, 100
        multi_channel_vector = torch.stack([
            word_vector, transformed_entity_vector, transformed_context_vector
        ],
                                           dim=1)  # 64, 3, 10, 100

        pooled_vectors = []
        for x in self.config.window_sizes:
            convoluted = self.conv_filters[str(x)](
                multi_channel_vector).squeeze(dim=3)  # 64, 120, 11-x
            activated = F.relu(convoluted)  # 64, 120, 11-x
            # 64, 120 # TODO: vs nn.MaxPool1d
            pooled = activated.max(dim=-1)[0]
            pooled_vectors.append(pooled)
        final_vector = torch.cat(pooled_vectors, dim=1)  # 64 * 480
        return final_vector