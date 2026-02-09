"""HuggingFace Model Registry — task-to-model mappings and model metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelInfo:
    model_id: str
    task: str
    description: str
    input_type: str  # "text", "image", "audio", "json"
    output_type: str  # "text", "image", "audio", "json"


# Curated default models for common tasks — these are well-known, reliable models
DEFAULT_MODELS: dict[str, list[ModelInfo]] = {
    "text-generation": [
        ModelInfo("mistralai/Mistral-7B-Instruct-v0.3", "text-generation",
                  "General-purpose text generation and chat", "text", "text"),
        ModelInfo("HuggingFaceH4/zephyr-7b-beta", "text-generation",
                  "Instruction-following text generation", "text", "text"),
    ],
    "summarization": [
        ModelInfo("facebook/bart-large-cnn", "summarization",
                  "Text summarization (news articles, documents)", "text", "text"),
        ModelInfo("sshleifer/distilbart-cnn-12-6", "summarization",
                  "Fast text summarization", "text", "text"),
    ],
    "translation": [
        ModelInfo("Helsinki-NLP/opus-mt-en-fr", "translation",
                  "English to French translation", "text", "text"),
        ModelInfo("Helsinki-NLP/opus-mt-en-de", "translation",
                  "English to German translation", "text", "text"),
        ModelInfo("Helsinki-NLP/opus-mt-en-es", "translation",
                  "English to Spanish translation", "text", "text"),
        ModelInfo("Helsinki-NLP/opus-mt-fr-en", "translation",
                  "French to English translation", "text", "text"),
    ],
    "text-classification": [
        ModelInfo("distilbert-base-uncased-finetuned-sst-2-english", "text-classification",
                  "Sentiment analysis (positive/negative)", "text", "json"),
        ModelInfo("cardiffnlp/twitter-roberta-base-sentiment-latest", "text-classification",
                  "Twitter sentiment analysis", "text", "json"),
    ],
    "question-answering": [
        ModelInfo("deepset/roberta-base-squad2", "question-answering",
                  "Extractive question answering", "json", "json"),
    ],
    "image-classification": [
        ModelInfo("google/vit-base-patch16-224", "image-classification",
                  "General image classification (ImageNet)", "image", "json"),
    ],
    "object-detection": [
        ModelInfo("facebook/detr-resnet-50", "object-detection",
                  "Object detection in images", "image", "json"),
    ],
    "image-to-text": [
        ModelInfo("Salesforce/blip-image-captioning-base", "image-to-text",
                  "Generate captions for images", "image", "text"),
    ],
    "automatic-speech-recognition": [
        ModelInfo("openai/whisper-large-v3", "automatic-speech-recognition",
                  "Speech to text transcription", "audio", "text"),
        ModelInfo("openai/whisper-base", "automatic-speech-recognition",
                  "Fast speech to text transcription", "audio", "text"),
    ],
    "text-to-speech": [
        ModelInfo("espnet/kan-bayashi_ljspeech_vits", "text-to-speech",
                  "Convert text to speech audio", "text", "audio"),
    ],
    "zero-shot-classification": [
        ModelInfo("facebook/bart-large-mnli", "zero-shot-classification",
                  "Classify text into arbitrary categories", "json", "json"),
    ],
    "feature-extraction": [
        ModelInfo("sentence-transformers/all-MiniLM-L6-v2", "feature-extraction",
                  "Generate text embeddings for semantic search", "text", "json"),
    ],
    "fill-mask": [
        ModelInfo("bert-base-uncased", "fill-mask",
                  "Fill in masked words in text", "text", "json"),
    ],
    "token-classification": [
        ModelInfo("dslim/bert-base-NER", "token-classification",
                  "Named entity recognition (NER)", "text", "json"),
    ],
}


class ModelRegistry:
    """Registry of HuggingFace models organized by task."""

    def __init__(self) -> None:
        self._models: dict[str, list[ModelInfo]] = {}
        # Load defaults
        for task, models in DEFAULT_MODELS.items():
            self._models[task] = list(models)

    def get_tasks(self) -> list[str]:
        """List all available task categories."""
        return sorted(self._models.keys())

    def get_models_for_task(self, task: str) -> list[ModelInfo]:
        """Get all registered models for a given task."""
        return self._models.get(task, [])

    def get_model(self, model_id: str) -> ModelInfo | None:
        """Find a model by its ID across all tasks."""
        for models in self._models.values():
            for model in models:
                if model.model_id == model_id:
                    return model
        return None

    def search(self, query: str) -> list[ModelInfo]:
        """Search models by keyword in ID, task, or description."""
        query_lower = query.lower()
        results = []
        for models in self._models.values():
            for model in models:
                if (query_lower in model.model_id.lower()
                        or query_lower in model.task.lower()
                        or query_lower in model.description.lower()):
                    results.append(model)
        return results

    def register_model(
        self,
        model_id: str,
        task: str,
        description: str = "",
        input_type: str = "text",
        output_type: str = "text",
    ) -> ModelInfo:
        """Register a custom model."""
        model = ModelInfo(model_id, task, description, input_type, output_type)
        if task not in self._models:
            self._models[task] = []
        self._models[task].append(model)
        return model

    def summary(self) -> list[dict[str, Any]]:
        """Return a summary for display."""
        result = []
        for task in sorted(self._models.keys()):
            models = self._models[task]
            result.append({
                "task": task,
                "model_count": len(models),
                "models": [
                    {"model_id": m.model_id, "description": m.description}
                    for m in models
                ],
            })
        return result
