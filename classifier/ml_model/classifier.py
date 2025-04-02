import torch
import joblib
import numpy as np
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)
from functools import lru_cache
from typing import Dict, Union
from collections import Counter
import logging

logger = logging.getLogger(__name__)

class WebsiteClassifier:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebsiteClassifier, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.device = self._get_device()
        self.tokenizer = None
        self.model = None
        self.label_encoder = None
        self._load_components()

    def _get_device(self) -> str:
        """Determine the best available device"""
        return "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

    def _load_components(self):
        """Load all necessary components"""
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                "distilbert-base-uncased",
                use_fast=True
            )

            # Load model
            self.model = AutoModelForSequenceClassification.from_pretrained(
                "ml_model/website_classifier",
                device_map="auto",
                torch_dtype=torch.float16 if "cuda" in self.device else torch.float32
            ).to(self.device)

            # Load label encoder - you'll need to provide this file
            self.label_encoder = joblib.load('ml_model/label_encoder.joblib')

            logger.info("Model components loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load components: {str(e)}")
            raise

    def _chunk_text(self, text: str, max_tokens: int = 400) -> list:
        """Split text into token-limited chunks"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            word_tokens = len(self.tokenizer.tokenize(word))
            if current_length + word_tokens > max_tokens:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_tokens
            else:
                current_chunk.append(word)
                current_length += word_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _predict_chunk(self, chunk: str) -> Dict[str, float]:
        """Predict a single text chunk"""
        inputs = self.tokenizer(
            chunk,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding="max_length"
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            pred_idx = torch.argmax(probs).item()
            confidence = probs[0][pred_idx].item()

        return {
            "label_index": pred_idx,
            "confidence": confidence
        }

    def predict(self, text: str) -> Dict[str, Union[str, float]]:
        """Main prediction method with chunking and majority voting"""
        if not text.strip():
            return {"error": "Empty input text"}

        try:
            # Chunk the text
            chunks = self._chunk_text(text)
            if not chunks:
                return {"error": "No valid chunks after processing"}

            # Process chunks in batches
            predictions = []
            confidences = []
            
            for chunk in chunks:
                result = self._predict_chunk(chunk)
                predictions.append(result["label_index"])
                confidences.append(result["confidence"])

            # Majority voting with confidence weighting
            majority_idx = Counter(predictions).most_common(1)[0][0]
            avg_confidence = np.mean([
                conf for idx, conf in zip(predictions, confidences) 
                if idx == majority_idx
            ])

            # Decode label
            category = self.label_encoder.inverse_transform([majority_idx])[0]

            return {
                "category": category,
                "confidence": round(avg_confidence, 4),
                "chunks_processed": len(chunks)
            }

        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            return {"error": f"Prediction error: {str(e)}"}

# Singleton instance
classifier = WebsiteClassifier()