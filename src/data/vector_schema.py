"""Vector database schema definitions for Qdrant collections."""

from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.data.config import config


@dataclass
class CollectionConfig:
    """Configuration for a Qdrant collection."""

    name: str
    vector_size: int
    distance: Distance
    description: str


# Collection configurations
PRICE_PATTERNS_COLLECTION = CollectionConfig(
    name="price_patterns",
    vector_size=384,  # all-MiniLM-L6-v2
    distance=Distance.COSINE,
    description="Historical price pattern embeddings for pattern matching",
)

NEWS_EVENTS_COLLECTION = CollectionConfig(
    name="news_events",
    vector_size=384,
    distance=Distance.COSINE,
    description="News articles with sentiment and market impact",
)

LLM_PREDICTIONS_COLLECTION = CollectionConfig(
    name="llm_predictions",
    vector_size=384,
    distance=Distance.COSINE,
    description="Past LLM predictions with outcomes for RL",
)

STRATEGY_OUTCOMES_COLLECTION = CollectionConfig(
    name="strategy_outcomes",
    vector_size=128,  # Smaller for strategy embeddings
    distance=Distance.COSINE,
    description="Backtest results for strategy ranking",
)

ALL_COLLECTIONS = [
    PRICE_PATTERNS_COLLECTION,
    NEWS_EVENTS_COLLECTION,
    LLM_PREDICTIONS_COLLECTION,
    STRATEGY_OUTCOMES_COLLECTION,
]


class VectorSchemaManager:
    """Manages Qdrant collection schema creation and validation."""

    def __init__(self, qdrant_url: str | None = None) -> None:
        """Initialize the schema manager.

        Args:
            qdrant_url: Qdrant server URL (defaults to config)
        """
        self.client = QdrantClient(url=qdrant_url or config.qdrant_url)

    def init_all_collections(self) -> None:
        """Initialize all required collections."""
        for collection_config in ALL_COLLECTIONS:
            self._create_collection_if_not_exists(collection_config)

    def _create_collection_if_not_exists(
        self, config: CollectionConfig
    ) -> None:
        """Create a collection if it doesn't exist.

        Args:
            config: Collection configuration
        """
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if config.name not in collection_names:
                self.client.create_collection(
                    collection_name=config.name,
                    vectors_config=VectorParams(
                        size=config.vector_size,
                        distance=config.distance,
                    ),
                )
                print(f"Created collection: {config.name}")
            else:
                print(f"Collection already exists: {config.name}")

        except Exception as e:
            raise ValueError(
                f"Failed to create collection {config.name}: {e}"
            ) from e

    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection statistics
        """
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vector_size": info.config.params.vectors.size,
                "distance": str(info.config.params.vectors.distance),
                "points_count": info.points_count,
                "status": "active",
            }
        except Exception as e:
            return {"name": collection_name, "error": str(e), "status": "error"}

    def list_collections(self) -> list[str]:
        """List all collection names.

        Returns:
            List of collection names
        """
        try:
            collections = self.client.get_collections()
            return [c.name for c in collections.collections]
        except Exception as e:
            raise ValueError(f"Failed to list collections: {e}") from e

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection.

        Args:
            collection_name: Name of the collection to delete
        """
        try:
            self.client.delete_collection(collection_name)
            print(f"Deleted collection: {collection_name}")
        except Exception as e:
            raise ValueError(
                f"Failed to delete collection {collection_name}: {e}"
            ) from e

    def reset_all_collections(self) -> None:
        """Delete and recreate all collections (use with caution!)."""
        for collection_config in ALL_COLLECTIONS:
            try:
                self.delete_collection(collection_config.name)
            except Exception:
                pass  # Collection might not exist
        self.init_all_collections()


def init_vector_schema() -> None:
    """Initialize all vector database collections.

    This is the main entry point for setting up the vector schema.
    """
    manager = VectorSchemaManager()
    manager.init_all_collections()
    print("\nVector schema initialization complete!")

    # Print collection info
    print("\nCollection Status:")
    for collection_config in ALL_COLLECTIONS:
        info = manager.get_collection_info(collection_config.name)
        points = info.get("points_count", "N/A")
        print(f"  - {collection_config.name}: {points} points")
