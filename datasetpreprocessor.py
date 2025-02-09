import pandas as pd
import numpy as np
from datasets import load_dataset
import re
import csv

sentence_per_article = 20
train_articles = 2000
dev_articles = 0.1 * train_articles

# dataset = load_dataset("wikipedia", "20220301.en")
data_dir = "data_new"

def load_data():
    dataset = load_dataset("wikipedia", "20220301.en", trust_remote_code=True)
    # dataset = load_dataset("wikipedia", "20220301.simple", trust_remote_code=True)
    return dataset


def cutoff_sentence(dataset):
    train_valid = dataset['train'].train_test_split(test_size=0.1)
    train_data = train_valid['train']
    dev_data = train_valid['test']

    train_sentences = []
    train_labels = []
    article_counter = 0
    for article in train_data:
        article_counter += 1
        if article_counter > train_articles:
            break
        text = article["text"]
        sentences = text.split(".") # turn into regex that splits based on .[whitespace or new line]
        sentence_counter = 0
        for s in sentences:
            sentence_counter += 1
            if sentence_counter > sentence_per_article:
                 break
            s = re.sub('[\n]+', '', s) # Remove newlines
            s = re.sub("' '+", ' ', s) # Standardize spaces
            s = re.sub('[0-9]+', '', s) # Remove numbers?
            s = s.strip() # Strip leading whitespace
            sen_len = len(s)
            if sen_len > 5 and s[0].isupper():
                cutoff = np.random.randint(5, sen_len)
                train_sentences.append(s[0:cutoff])
                train_labels.append(s[cutoff].lower())

    dev_sentences = []
    dev_labels = []
    article_counter = 0
    for article in dev_data:
        article_counter += 1
        if article_counter > dev_articles: break
        text = article["text"]
        sentences = text.split('.')# re.split('.', text) #REGEX SPLIT, REMOVE NEW LINES, .[\n\r\s]+'
        sentence_counter = 0
        for s in sentences:
            sentence_counter += 1
            if sentence_counter > sentence_per_article: break
            # Sentence cleaning
            s = re.sub('[\n]+', '', s) # Remove newlines
            s = re.sub("' '+", ' ', s) # Standardize spaces
            s = re.sub('[0-9]+', '', s) # Remove numbers
            s = s.strip() # Strip leading whitespace

            sen_len = len(s)
            if sen_len > 5 and s[0].isupper(): # Keep only sentences that start with an uppercase character
                cutoff = np.random.randint(1, sen_len)
                dev_sentences.append(s[0:cutoff])
                dev_labels.append(s[cutoff].lower())

    return train_sentences, train_labels, dev_sentences, dev_labels

def create_train(sentences, labels):
    train_df = pd.DataFrame(data={'sentence': sentences, 'label': labels})
    train_df.to_csv(f'{data_dir}/train_cutoff_sentences.csv', index=False)


def create_dev(sentences, labels):
    with open(f'{data_dir}/dev_input.txt', mode='w', encoding='utf-8') as input:
             input.write("\n".join(sentences) + "\n")
    with open(f'{data_dir}/dev_labels.txt', mode='w', encoding='utf-8') as output:
             output.write("\n".join(labels) + "\n")

# # Turns CSV file into two txt files for prediction analysis
# def dev_to_test_format():
#         dev_data = pd.read_csv('data/dev_cutoff_sentences.csv', encoding='utf-8')
#         sentences = dev_data['sentence'].tolist()  # Load training data as a list
#         chars = dev_data['label'].tolist()  # Load characters (answers) as a list
#         with open("dev_input.txt", mode='w', encoding='utf-8') as input:
#              input.write("\n".join(sentences) + "\n")
#         with open("dev_labels.txt", mode='w', encoding='utf-8') as labels:
#              labels.write("\n".join(chars) + "\n")

def main():
    print('Loading Data')
    dataset = load_data()
    print('Making Sentences')
    train_sentences, train_labels, dev_sentences, dev_labels = cutoff_sentence(dataset)
    print('Writing training data')
    create_train(train_sentences, train_labels)
    print('Writing dev data')
    create_dev(dev_sentences, dev_labels)

if __name__ == '__main__':
    main()