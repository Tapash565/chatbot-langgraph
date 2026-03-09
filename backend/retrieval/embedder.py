"""Embeddings provider for the retrieval system."""
from typing import Optional
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from backend.core.config import config
from backend.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingsProvider:
    """Manages embeddings for the retrieval system."""

    def __init__(self, model: Optional[str] = None):
        self.model_name = model or config.EMBEDDING_MODEL
        self._embeddings: Optional[HuggingFaceEndpointEmbeddings] = None

    @property
    def embeddings(self) -> HuggingFaceEndpointEmbeddings:
        """Get or create embeddings instance."""
        if self._embeddings is None:
            logger.info("initializing_embeddings", model=self.model_name)
            self._embeddings = HuggingFaceEndpointEmbeddings(
                model=self.model_name
            )
        return self._embeddings

    def get_embeddings(self) -> HuggingFaceEndpointEmbeddings:
        """Public method to get embeddings."""
        return self.embeddings


# Global embeddings provider
embeddings_provider = EmbeddingsProvider()
