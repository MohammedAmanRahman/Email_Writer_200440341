"""
Complaint Text Classifier - Neural Networks Module
Implements LSTM and MLP architectures for comparative analysis.
"""
import torch
import torch.nn as nn
import numpy as np
import json
import os
from pathlib import Path


class TextPreprocessor:
    """Tokenizes and encodes complaint text for model input."""

    def __init__(self, vocab_size=10000, max_length=200):
        self.vocab_size = vocab_size
        self.max_length = max_length
        self.word2idx = {"<PAD>": 0, "<UNK>": 1}
        self.idx2word = {0: "<PAD>", 1: "<UNK>"}
        self.word_counts = {}
        self.fitted = False

    def fit(self, texts):
        """Build vocabulary from training texts."""
        for text in texts:
            for word in text.lower().split():
                word = ''.join(c for c in word if c.isalnum())
                if word:
                    self.word_counts[word] = self.word_counts.get(word, 0) + 1

        # Keep top vocab_size words
        sorted_words = sorted(self.word_counts.items(), key=lambda x: -x[1])
        for idx, (word, _) in enumerate(sorted_words[:self.vocab_size - 2], start=2):
            self.word2idx[word] = idx
            self.idx2word[idx] = word

        self.fitted = True

    def encode(self, text):
        """Convert text to padded integer sequence."""
        words = text.lower().split()
        words = [''.join(c for c in w if c.isalnum()) for w in words]
        words = [w for w in words if w]

        indices = [self.word2idx.get(w, 1) for w in words[:self.max_length]]
        # Pad
        while len(indices) < self.max_length:
            indices.append(0)
        return indices

    def encode_batch(self, texts):
        """Encode a batch of texts."""
        return torch.tensor([self.encode(t) for t in texts], dtype=torch.long)

    def save(self, path):
        data = {
            "vocab_size": self.vocab_size,
            "max_length": self.max_length,
            "word2idx": self.word2idx,
        }
        with open(path, "w") as f:
            json.dump(data, f)

    def load(self, path):
        with open(path, "r") as f:
            data = json.load(f)
        self.vocab_size = data["vocab_size"]
        self.max_length = data["max_length"]
        self.word2idx = data["word2idx"]
        self.idx2word = {int(v): k for k, v in self.word2idx.items()}
        self.fitted = True


class LSTMClassifier(nn.Module):
    """
    LSTM-based text classifier for complaint categorization.
    Architecture: Embedding -> LSTM -> Dropout -> FC -> Softmax
    """
    def __init__(self, vocab_size, embedding_dim, hidden_dim, output_dim,
                 n_layers=2, dropout=0.3, bidirectional=True):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.lstm = nn.LSTM(
            embedding_dim, hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0,
            bidirectional=bidirectional
        )
        direction_factor = 2 if bidirectional else 1
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim * direction_factor, output_dim)

    def forward(self, x):
        embedded = self.dropout(self.embedding(x))
        lstm_out, (hidden, _) = self.lstm(embedded)
        if self.lstm.bidirectional:
            hidden = torch.cat((hidden[-2], hidden[-1]), dim=1)
        else:
            hidden = hidden[-1]
        hidden = self.dropout(hidden)
        return self.fc(hidden)


class MLPClassifier(nn.Module):
    """
    MLP-based text classifier for comparison with LSTM.
    Architecture: Embedding (averaged) -> FC -> ReLU -> Dropout -> FC -> Softmax
    """
    def __init__(self, vocab_size, embedding_dim, hidden_dim, output_dim, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.fc1 = nn.Linear(embedding_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc3 = nn.Linear(hidden_dim // 2, output_dim)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        embedded = self.embedding(x)
        # Average pooling over sequence length (ignoring padding)
        mask = (x != 0).unsqueeze(-1).float()
        pooled = (embedded * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        out = self.dropout(self.relu(self.fc1(pooled)))
        out = self.dropout(self.relu(self.fc2(out)))
        return self.fc3(out)


# Default configuration
DEFAULT_CONFIG = {
    "vocab_size": 10000,
    "embedding_dim": 128,
    "hidden_dim": 256,
    "max_length": 200,
    "n_layers": 2,
    "dropout": 0.3,
    "bidirectional": True,
    "learning_rate": 0.001,
    "batch_size": 64,
    "epochs": 20,
}
