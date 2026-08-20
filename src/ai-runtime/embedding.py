from __future__ import annotations

import hashlib
import os
import re
from typing import Protocol

from openai import AsyncAzureOpenAI
from pydantic import AnyUrl, BaseModel, ConfigDict, Field, SecretStr


class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class EmbeddingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    endpoint: AnyUrl
    api_version: str = Field(min_length=1)
    api_key: SecretStr
    deployment: str = Field(min_length=1)

    @classmethod
    def from_env(cls) -> "EmbeddingSettings":
        values = {
            "endpoint": os.getenv("INCIDENTWEAVER_AZURE_OPENAI_ENDPOINT"),
            "api_version": os.getenv("INCIDENTWEAVER_AZURE_OPENAI_API_VERSION"),
            "api_key": os.getenv("INCIDENTWEAVER_AZURE_OPENAI_API_KEY"),
            "deployment": os.getenv("INCIDENTWEAVER_EMBEDDING_DEPLOYMENT"),
        }
        missing = [f"INCIDENTWEAVER_{name.upper()}" for name, value in values.items() if not value]
        if missing:
            raise ValueError(f"Missing required embedding configuration: {', '.join(missing)}")
        return cls.model_validate(values)


class AzureOpenAIEmbeddingProvider:
    def __init__(self, settings: EmbeddingSettings) -> None:
        self.settings = settings
        self.client = AsyncAzureOpenAI(
            api_key=settings.api_key.get_secret_value(),
            azure_endpoint=str(settings.endpoint),
            api_version=settings.api_version,
        )

    async def embed(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(input=text, model=self.settings.deployment)
        return list(response.data[0].embedding)


class DeterministicEmbeddingProvider:
    """Small offline embedding substitute for tests and local retrieval checks."""

    def __init__(self, dimensions: int = 32) -> None:
        self.dimensions = dimensions
        self.calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9][a-z0-9-]*", text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dimensions] += 1.0
        return vector