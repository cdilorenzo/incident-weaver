from __future__ import annotations

import os
from pydantic import AnyUrl, BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.azure import AzureProvider


class ModelSettings(BaseModel):
    """Project-owned configuration for the AI runtime model layer."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    provider: str = Field(
        ...,
        description="The supported model provider for this runtime.",
    )
    deployment_name: str = Field(
        ...,
        min_length=1,
        description="The Azure OpenAI deployment or model identifier to use.",
    )
    azure_openai_endpoint: AnyUrl = Field(
        ...,
        description="Azure OpenAI resource endpoint used for model calls.",
    )
    azure_openai_api_version: str = Field(
        ...,
        min_length=1,
        description="Azure OpenAI API version for the resource.",
    )
    azure_openai_api_key: SecretStr = Field(
        ...,
        description="Azure OpenAI API key used for authentication.",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        if value != "azure-openai":
            raise ValueError(
                f"Unsupported model provider '{value}'. Only 'azure-openai' is supported in V1."
            )
        return value

    @classmethod
    def from_env(cls) -> "ModelSettings":
        provider_value = os.getenv("INCIDENTWEAVER_MODEL_PROVIDER", "azure-openai")
        endpoint_value = os.getenv("INCIDENTWEAVER_AZURE_OPENAI_ENDPOINT")
        api_version_value = os.getenv("INCIDENTWEAVER_AZURE_OPENAI_API_VERSION")
        api_key_value = os.getenv("INCIDENTWEAVER_AZURE_OPENAI_API_KEY")
        deployment_value = os.getenv("INCIDENTWEAVER_MODEL_DEPLOYMENT")

        missing = [
            name
            for name, value in {
                "INCIDENTWEAVER_MODEL_PROVIDER": provider_value,
                "INCIDENTWEAVER_MODEL_DEPLOYMENT": deployment_value,
                "INCIDENTWEAVER_AZURE_OPENAI_ENDPOINT": endpoint_value,
                "INCIDENTWEAVER_AZURE_OPENAI_API_VERSION": api_version_value,
                "INCIDENTWEAVER_AZURE_OPENAI_API_KEY": api_key_value,
            }.items()
            if not value
        ]
        if missing:
            missing_names = ", ".join(missing)
            raise ValueError(f"Missing required model configuration: {missing_names}")

        return cls.model_validate(
            {
                "provider": provider_value,
                "deployment_name": deployment_value,
                "azure_openai_endpoint": endpoint_value,
                "azure_openai_api_version": api_version_value,
                "azure_openai_api_key": api_key_value,
            }
        )


def create_model(settings: ModelSettings) -> OpenAIChatModel:
    """Construct a Pydantic AI Azure OpenAI model from project-owned settings."""

    return OpenAIChatModel(
        model_name=settings.deployment_name,
        provider=AzureProvider(
            azure_endpoint=str(settings.azure_openai_endpoint),
            api_version=settings.azure_openai_api_version,
            api_key=settings.azure_openai_api_key.get_secret_value(),
        ),
    )
