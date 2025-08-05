# Generated from tiny_demo.ipynb
# Python cells extracted in order


# ========== Cell 2 ==========
# Import necessary libraries
import pandas as pd
from langchain import OpenAI
import numpy as np

# ========== Cell 3 ==========
# Helper function to clean text
def clean_text(text):
    """Remove extra whitespace and normalize text."""
    return ' '.join(text.split())

# Another helper
def tokenize(text):
    """Simple tokenization."""
    return text.lower().split()

# ========== Cell 4 ==========
class VectorStore:
    """Simple vector storage for embeddings."""
    def __init__(self):
        self.vectors = []
    
    def add(self, vector):
        self.vectors.append(vector)
    
    def search(self, query_vector, k=5):
        # Simplified search
        return self.vectors[:k]

# ========== Cell 5 ==========
def build_rag_graph(documents):
    """Main function to build RAG pipeline."""
    store = VectorStore()
    
    for doc in documents:
        cleaned = clean_text(doc)
        tokens = tokenize(cleaned)
        # Add to store (simplified)
        store.add(tokens)
    
    return store

# Configuration
MAX_TOKENS = 100
TEMPERATURE = 0.7