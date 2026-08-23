import pandas as pd
import numpy as np
import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
import os

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {
        "precision": precision_score(labels, predictions, zero_division=0),
        "recall": recall_score(labels, predictions, zero_division=0),
        "f1": f1_score(labels, predictions, zero_division=0),
        "accuracy": accuracy_score(labels, predictions)
    }

def main():
    print("Loading dataset...")
    df = pd.read_csv("DataSet.csv/internship_job_scam_dataset.csv")
    
    # We want original_fraudulent as label (1 = scam, 0 = safe)
    df["label"] = df["original_fraudulent"]
    # Drop rows without text
    df = df.dropna(subset=["text"])
    
    texts = df["text"].tolist()
    labels = df["label"].tolist()
    
    train_texts, test_texts, train_labels, test_labels = train_test_split(texts, labels, test_size=0.2, random_state=42)
    
    train_df = pd.DataFrame({"text": train_texts, "label": train_labels})
    test_df = pd.DataFrame({"text": test_texts, "label": test_labels})
    
    train_dataset = Dataset.from_pandas(train_df)
    test_dataset = Dataset.from_pandas(test_df)
    
    model_name = "distilbert-base-uncased"
    print(f"Loading tokenizer {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=512)
        
    print("Tokenizing dataset...")
    train_dataset = train_dataset.map(tokenize_function, batched=True)
    test_dataset = test_dataset.map(tokenize_function, batched=True)
    
    print(f"Loading model {model_name}...")
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
    
    training_args = TrainingArguments(
        output_dir="./results",
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=3,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        compute_metrics=compute_metrics,
    )
    
    print("Starting training...")
    trainer.train()
    
    print("Evaluating model...")
    results = trainer.evaluate()
    print(f"Evaluation Metrics:")
    print(f" - Precision: {results.get('eval_precision', 0):.4f}")
    print(f" - Recall: {results.get('eval_recall', 0):.4f}")
    print(f" - F1 Score: {results.get('eval_f1', 0):.4f}")
    print(f" - Accuracy: {results.get('eval_accuracy', 0):.4f}")
    
    output_dir = "app/resources/transformer_model"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving model to {output_dir}...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("Done!")

if __name__ == "__main__":
    main()
