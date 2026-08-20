from __future__ import annotations

import asyncio
import os
from pathlib import Path

from embedding import AzureOpenAIEmbeddingProvider, EmbeddingSettings
from retrieval import PostgresKnowledgeStore, index_knowledge


async def main() -> None:
    root = Path(os.getenv("INCIDENTWEAVER_KNOWLEDGE_ROOT", "knowledge"))
    dimensions = int(os.getenv("INCIDENTWEAVER_EMBEDDING_DIMENSIONS", "1536"))
    store = PostgresKnowledgeStore(os.environ["INCIDENTWEAVER_KNOWLEDGE_DSN"], dimensions)
    await store.initialize()
    count = await index_knowledge(root, AzureOpenAIEmbeddingProvider(EmbeddingSettings.from_env()), store)
    print(f"Indexed {count} knowledge chunks.")


if __name__ == "__main__":
    asyncio.run(main())