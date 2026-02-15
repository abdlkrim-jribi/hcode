"""
Local embedding generation using sentence-transformers.
No external API calls required - runs entirely locally.
"""

import hashlib
import json
from typing import List, Optional, Union

import numpy as np
from hcode.memory.config import config


class EmbeddingModel:
    """
    Local embedding model using sentence-transformers.
    Lazy loads model on first use to avoid startup overhead.
    """

    _instance: Optional["EmbeddingModel"] = None
    _model = None

    def __new__(cls) -> "EmbeddingModel":
        """Singleton pattern for shared model instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize embedding model (lazy loaded)."""
        self.model_name = config.embedding_model
        self.embedding_dim = config.embedding_dim
        self._cache: dict = {}  # Simple in-memory cache
        self._cache_file = config.global_dir / "embedding_cache.json"
        self._load_cache()

    def _load_cache(self):
        """Load embedding cache from disk."""
        if self._cache_file.exists():
            try:
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    # Convert lists back to tuples for hashable keys
                    self._cache = {k: np.array(v) for k, v in cached.items()}
            except Exception:
                self._cache = {}

    def _save_cache(self):
        """Save embedding cache to disk."""
        try:
            # Convert numpy arrays to lists for JSON serialization
            serializable = {k: v.tolist() for k, v in self._cache.items()}
            # Only save if cache is reasonable size
            if len(serializable) <= 10000:
                with open(self._cache_file, "w", encoding="utf-8") as f:
                    json.dump(serializable, f)
        except Exception:
            pass  # Cache save failure is not critical

    def _get_model(self):
        """Lazy load the model on first use."""
        if EmbeddingModel._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                EmbeddingModel._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for embeddings. "
                    "Install with: pip install sentence-transformers"
                )
        return EmbeddingModel._model

    def _hash_text(self, text: str) -> str:
        """Create a hash key for text."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def embed(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            use_cache: Whether to use caching

        Returns:
            numpy array of shape (embedding_dim,)
        """
        if not text.strip():
            return np.zeros(self.embedding_dim)

        # Check cache
        cache_key = self._hash_text(text)
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # Generate embedding
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)

        # Cache result
        if use_cache:
            self._cache[cache_key] = embedding
            # Periodically save cache
            if len(self._cache) % 100 == 0:
                self._save_cache()

        return embedding

    def embed_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed
            use_cache: Whether to use caching
            batch_size: Batch size for encoding
            show_progress: Show progress bar

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.zeros((0, self.embedding_dim))

        results = np.zeros((len(texts), self.embedding_dim))
        texts_to_encode = []
        indices_to_encode = []

        # Check cache for each text
        for i, text in enumerate(texts):
            if not text.strip():
                continue

            cache_key = self._hash_text(text)
            if use_cache and cache_key in self._cache:
                results[i] = self._cache[cache_key]
            else:
                texts_to_encode.append(text)
                indices_to_encode.append(i)

        # Encode uncached texts
        if texts_to_encode:
            model = self._get_model()
            embeddings = model.encode(
                texts_to_encode,
                convert_to_numpy=True,
                batch_size=batch_size,
                show_progress_bar=show_progress,
            )

            # Store results and update cache
            for j, (idx, text) in enumerate(zip(indices_to_encode, texts_to_encode)):
                results[idx] = embeddings[j]
                if use_cache:
                    cache_key = self._hash_text(text)
                    self._cache[cache_key] = embeddings[j]

        # Save cache after batch
        if use_cache and texts_to_encode:
            self._save_cache()

        return results

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity score (0-1)
        """
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))


# Convenience functions
def get_embedding_model() -> EmbeddingModel:
    """Get the singleton embedding model instance."""
    return EmbeddingModel()


def embed_text(text: str) -> np.ndarray:
    """Quick helper to embed a single text."""
    return get_embedding_model().embed(text)


def embed_texts(texts: List[str]) -> np.ndarray:
    """Quick helper to embed multiple texts."""
    return get_embedding_model().embed_batch(texts)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Quick helper for cosine similarity."""
    return get_embedding_model().similarity(a, b)


class FallbackEmbedding:
    """
    Simple fallback embedding when sentence-transformers is not available.
    Uses basic TF-IDF-like hashing for minimal functionality.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, text: str) -> np.ndarray:
        """Create a simple hash-based embedding."""
        if not text.strip():
            return np.zeros(self.dim)

        # Simple character n-gram hashing
        embedding = np.zeros(self.dim)
        words = text.lower().split()

        for word in words:
            # Hash each word to embedding dimensions
            for i, char in enumerate(word):
                idx = (ord(char) * (i + 1)) % self.dim
                embedding[idx] += 1.0

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Embed multiple texts."""
        return np.array([self.embed(t) for t in texts])


def get_embedding_model_safe() -> Union[EmbeddingModel, FallbackEmbedding]:
    """
    Get embedding model with fallback if sentence-transformers unavailable.
    """
    try:
        import sentence_transformers  # noqa: F401

        return EmbeddingModel()
    except ImportError:
        return FallbackEmbedding(config.embedding_dim)
