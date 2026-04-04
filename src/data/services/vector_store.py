"""Vector store service using Qdrant for news embeddings."""

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.data.config import config
from src.data.models.news import NewsArticle


class VectorStore:
    """Vector store for news articles using Qdrant."""

    def __init__(self, collection_name: str | None = None) -> None:
        """Initialize the vector store.

        Args:
            collection_name: Name of the Qdrant collection
        """
        self.collection_name = collection_name or config.qdrant_collection
        self.vector_size = 384  # all-MiniLM-L6-v2 embedding size

        # Initialize Qdrant client
        self.client = QdrantClient(url=config.qdrant_url)

    def init_collection(self) -> None:
        """Initialize the Qdrant collection if it doesn't exist."""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"Created Qdrant collection: {self.collection_name}")
            else:
                print(f"Qdrant collection already exists: {self.collection_name}")

        except Exception as e:
            raise ValueError(f"Failed to initialize collection: {e}") from e

    def upsert_news(self, articles: list[NewsArticle]) -> None:
        """Upsert news articles into the vector store.

        Args:
            articles: List of NewsArticle objects with embeddings
        """
        if not articles:
            return

        points: list[PointStruct] = []
        for article in articles:
            if not article.embedding:
                continue

            point = PointStruct(
                id=article.id,
                vector=article.embedding,
                payload=article.to_qdrant_payload(),
            )
            points.append(point)

        if points:
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
            except Exception as e:
                raise ValueError(f"Failed to upsert articles: {e}") from e

    def search_similar_news(
        self,
        query_vector: list[float],
        top_k: int = 5,
        commodity: str | None = None,
    ) -> list[NewsArticle]:
        """Search for similar news articles.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            commodity: Optional filter by commodity

        Returns:
            List of matching NewsArticle objects
        """
        try:
            # Build filter if commodity specified
            query_filter = None
            if commodity:
                query_filter = {
                    "must": [
                        {"key": "commodity", "match": {"value": commodity}}
                    ]
                }

            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
            )

            articles = []
            for result in results:
                article = NewsArticle.from_qdrant_payload(
                    payload=result.payload,
                    embedding=result.vector if result.vector else [],
                )
                articles.append(article)

            return articles

        except Exception as e:
            raise ValueError(f"Failed to search news: {e}") from e

    def get_news_by_commodity(
        self,
        commodity: str,
        days: int = 7,
        limit: int = 20,
    ) -> list[NewsArticle]:
        """Get news articles for a specific commodity.

        Args:
            commodity: Commodity symbol
            days: Number of days to look back
            limit: Maximum number of articles

        Returns:
            List of NewsArticle objects
        """
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {"key": "commodity", "match": {"value": commodity}}
                    ]
                },
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            articles = []
            for result in results[0]:
                article = NewsArticle.from_qdrant_payload(
                    payload=result.payload,
                    embedding=[],
                )
                articles.append(article)

            # Sort by date (newest first)
            articles.sort(key=lambda x: x.date, reverse=True)
            return articles

        except Exception as e:
            raise ValueError(f"Failed to get news for {commodity}: {e}") from e

    def delete_old_news(self, days: int = 30) -> int:
        """Delete news articles older than specified days.

        Args:
            days: Delete articles older than this many days

        Returns:
            Number of deleted articles
        """
        # This would require timestamp-based filtering
        # For now, return 0 as placeholder
        return 0

    def get_collection_info(self) -> dict[str, Any]:
        """Get information about the collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vector_size": info.config.params.vectors.size,
                "distance": str(info.config.params.vectors.distance),
                "points_count": info.points_count,
            }
        except Exception as e:
            return {"error": str(e)}
