#!/usr/bin/env python
import os
import string
import random
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

# From HW2
from typing import List, Tuple, Dict, Union
import pandas as pd
import torch
from torch.utils.data import TensorDataset, DataLoader
import torch.nn as nn
from torch.optim import Adam
from sentence_transformers import SentenceTransformer

import dataloader

# Conversion table for numbers to characters
idx_to_char = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h', 8: 'i',
               9: 'j', 10: 'k', 11: 'l', 12: 'm', 13: 'n', 14: 'o', 15: 'p', 16: 'q',
               17: 'r', 18: 's', 19: 't', 20: 'u', 21: 'v', 22: 'w', 23: 'x', 24: 'y',
               25: 'z', 26: ' ', 27: '!', 28: '"', 29: '#', 30: '$', 31: '%', 32: '&',
               33: "'", 34: '(', 35: ')', 36: '*', 37: '+', 38: ',', 39: '-', 40: '.',
               41: '/', 42: '<unk>'}
            #, 43: '1', 44: '2', 45: '3', 46: '4', 47: '5', 48: '6',49: '7', 50: '8', 51: '9', 52: '0'}

# Actual model
class MyModel(nn.Module):

    def __init__(self, sentence_dim: int, word_dim: int, hidden_dim: int, output_dim: int):
        """
        Initialize the Feed-Foward model.
        Inputs:
        - sentence_dim: The dimension of the sentence embeddings
        - word_dim: The dimension of the final word embedding
        - hidden_dim: The dimension of the hidden layer
        - output_dim: The dimension of the output (e.g. number of ASCII characters)
        """

        super(MyModel, self).__init__()
        sentence_dim = 768
        word_dim = len(idx_to_char)
        hidden_dim = 1000
        output_dim = len(idx_to_char)

        # Define the architecture of the model
        self.fc1 = torch.nn.Linear(sentence_dim + word_dim, hidden_dim)
        self.act1 = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(hidden_dim, output_dim)

    def forward(self, context: torch.Tensor, curr_word: torch.Tensor) -> torch.Tensor:
        """
        Perform a forward pass through the network.
        Inputs:
        - context: torch.Tensor: The sentence embeddings of the context
        - curr_word: torch.Tensor: The embeddings of the characters of the current word
        Returns:
        - torch.Tensor: The logits for each of the answers
        """
        context = context.view(1, 768)
        curr_word = curr_word.view(1, len(idx_to_char))

        _input = torch.cat((context, curr_word), dim=1)  # concatenate sentence and word embeddings
        logit = self.fc2(self.act1(self.fc1(_input)))  # calculate logit
        return logit

    @classmethod
    def load_training_data(cls):
        st_model = SentenceTransformer("all-mpnet-base-v2")  # Make a model

        _train_data = pd.read_csv('data_new/train_cutoff_sentences.csv', encoding='utf-8')
        sentences = _train_data['sentence'].tolist()  # Load training data as a list

        # Split sentences into dictionary with 'context' and 'word'
        total_embeddings = []
        for entry in sentences:
            splits = entry.split()
            merged = ' '.join(splits[:-1])
            context_embedded = dataloader.get_st_embeddings([merged], st_model)  # Get context embeddings
            word = splits[-1] # Empty string in the case that the last character is a whitespace
            word_embedded = dataloader.get_word_embeddings(word)
            total_embeddings.append({'context': context_embedded, 'word': word_embedded})

        # TODO: save the embedded sentences so we don't have to compute this every time

        chars = _train_data['label'].tolist()  # Load characters (answers) as a list
        return dataloader.get_dataloader(total_embeddings, chars, 1)  # Return dataloader for training

    @classmethod
    def load_test_data(cls, fname):
        data = []
        with open(fname, 'r', encoding='utf-8') as f: 
            for line in f:
                line = line.replace("’","'")
                inp = line[:-1]  # the last character is a newline
                data.append(inp)
        return data

    @classmethod
    def write_pred(cls, preds, fname):
        with open(fname, 'wt') as f:
            for p in preds:
                f.write('{}\n'.format(p))

    def run_train(self, data, work_dir):
        # Hyperparameters for training
        lr: float = 1e-3
        batch_size: int = 32
        eval_batch_size: int = 128
        n_epochs: int = 100

        print("Beginning Training with Parameters:\n---Learning Rate: {l}"
              "\n---Batch Size: {b}\n---Eval Batch Size: {e}\n---Epochs: {E}\n"
              .format(l=lr, b=batch_size, e=eval_batch_size, E=n_epochs))

        train_loader = data

        loss_fn = torch.nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters(), 1e-3)

        progress = 0

        for epoch in range(n_epochs):  # Iterate over the epochs
            sys.stdout.write('\r[{0}{1} {2}%] Epoch: {3}'.format('#' * (int(progress / 10)),
                             '-' * (int(n_epochs / 10) - int(progress / 10)), progress, epoch))

            model.train()  # Set the model to training mode
            for batch in train_loader:  # Iterate over the batches of the training data
                optimizer.zero_grad()  # This is done to zero-out any existing gradients stored from previous steps

                # Get the embeddings for context, question, answerA, answerB, answerC
                context_batch = batch["context"]
                word_batch = batch["word"]

                # Get the characters
                char_batch = batch["char"]

                # Calculate model logits and loss
                batch_logits = model(context_batch, word_batch)
                batch_loss = loss_fn(batch_logits, char_batch)

                # Perform a backward pass and update the weights
                batch_loss.backward()

                # Perform a step of optimization
                optimizer.step()
            progress += 1
        print()
        self.save(work_dir)

    def run_pred(self, data):
        # your code here
        preds = []
        st_model = SentenceTransformer("all-mpnet-base-v2")
        for inp in data:
            # print(inp)
            split = inp.split()
            if len(split) > 1:
                sentence = ' '.join(split[:-1])
            else:
                sentence = ''
            word = split[-1]
            context = dataloader.get_st_embeddings([sentence], st_model)
            word = dataloader.get_word_embeddings(word)

            logits = model(context, word)
            (_, top_indices) = torch.topk(logits, k=3)
            top_chars = [idx_to_char[i.item()] for i in top_indices[0]]
            preds.append(''.join(list(top_chars)))
        # print(preds)
        return preds

    def save(self, work_dir):
        # Save the model
        torch.save(self.state_dict(), f'{work_dir}/model.checkpoint')

        # # this particular model has nothing to save, but for demonstration purposes we will save a blank file
        # with open(os.path.join(work_dir, 'model.checkpoint'), 'wt') as f:
        #     f.write('dummy save')

    @classmethod
    def load(cls, work_dir):
        # Load the model
        nn_model = MyModel(
            sentence_dim=768,  # Change this to 768 if you want to train with sentence transformer embeddings
            word_dim=len(idx_to_char),
            hidden_dim=200,  # You can change this to any number of hidden units you want
            output_dim=len(idx_to_char)  # You can change this to the number of classes for the multiclass case
        )
        nn_model.load_state_dict(torch.load(f'{work_dir}/model.checkpoint'))
        return nn_model

        # this particular model has nothing to load, but for demonstration purposes we will load a blank file
        with open(os.path.join(work_dir, 'model.checkpoint')) as f:
            dummy_save = f.read()
        return MyModel()


if __name__ == '__main__':
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('mode', choices=('train', 'test'), help='what to run')
    parser.add_argument('--work_dir', help='where to save', default='work')
    parser.add_argument('--test_data', help='path to test data', default='example/input.txt')
    parser.add_argument('--test_output', help='path to write test predictions', default='pred.txt')
    args = parser.parse_args()

    random.seed(0)

    if args.mode == 'train':
        if not os.path.isdir(args.work_dir):
            print('Making working directory {}'.format(args.work_dir))
            os.makedirs(args.work_dir)
        print('Instantiating model')
        model = MyModel(768, 43, 200, 43)
        print('Loading training data')
        train_data = MyModel.load_training_data()
        print('Training')
        model.run_train(train_data, args.work_dir)
        print('Saving model')
        model.save(args.work_dir)
    elif args.mode == 'test':
        print('Loading model')
        model = MyModel.load(args.work_dir)
        print('Loading test data from {}'.format(args.test_data))
        test_data = MyModel.load_test_data(args.test_data)
        print('Making predictions')
        pred = model.run_pred(test_data)
        print('Writing predictions to {}'.format(args.test_output))
        assert len(pred) == len(test_data), 'Expected {} predictions but got {}'.format(len(test_data), len(pred))
        model.write_pred(pred, args.test_output)
    else:
        raise NotImplementedError('Unknown mode {}'.format(args.mode))
