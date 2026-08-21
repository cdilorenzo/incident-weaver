import pytest

from model_provider import ModelSettings, create_model


def test_valid_azure_openai_configuration_is_parsed_successfully() -> None:
    settings = ModelSettings.model_validate(
        {
            "provider": "azure-openai",
            "deployment_name": "gpt-4o-mini",
            "azure_openai_endpoint": "https://example-resource.openai.azure.com",
            "azure_openai_api_version": "2024-10-21",
            "azure_openai_api_key": "test-key",
        }
    )

    assert settings.provider == "azure-openai"
    assert settings.deployment_name == "gpt-4o-mini"
    assert str(settings.azure_openai_endpoint) == "https://example-resource.openai.azure.com/"


def test_missing_required_configuration_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INCIDENTWEAVER_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("INCIDENTWEAVER_MODEL_DEPLOYMENT", raising=False)
    monkeypatch.delenv("INCIDENTWEAVER_AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("INCIDENTWEAVER_AZURE_OPENAI_API_VERSION", raising=False)
    monkeypatch.delenv("INCIDENTWEAVER_AZURE_OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Missing required model configuration"):
        ModelSettings.from_env()


def test_unsupported_provider_values_fail_clearly() -> None:
    with pytest.raises(ValueError, match="Unsupported model provider 'ollama'"):
        ModelSettings.model_validate(
            {
                "provider": "ollama",
                "deployment_name": "llama3",
                "azure_openai_endpoint": "https://example-resource.openai.azure.com",
                "azure_openai_api_version": "2024-10-21",
                "azure_openai_api_key": "test-key",
            }
        )


def test_azure_openai_model_can_be_constructed_from_valid_settings() -> None:
    settings = ModelSettings.model_validate(
        {
            "provider": "azure-openai",
            "deployment_name": "gpt-4o-mini",
            "azure_openai_endpoint": "https://example-resource.openai.azure.com",
            "azure_openai_api_version": "2024-10-21",
            "azure_openai_api_key": "test-key",
        }
    )

    model = create_model(settings)

    assert model is not None
    assert model.model_name == "gpt-4o-mini"
    assert type(model).__module__.startswith("pydantic_ai")


def test_provider_specific_objects_remain_in_infrastructure_layer() -> None:
    settings = ModelSettings.model_validate(
        {
            "provider": "azure-openai",
            "deployment_name": "gpt-4o-mini",
            "azure_openai_endpoint": "https://example-resource.openai.azure.com",
            "azure_openai_api_version": "2024-10-21",
            "azure_openai_api_key": "test-key",
        }
    )

    model = create_model(settings)

    assert type(model).__module__.startswith("pydantic_ai")
    assert "model_provider" not in type(model).__module__


def test_no_real_model_request_can_occur_in_test_suite() -> None:
    import pydantic_ai.models

    assert pydantic_ai.models.ALLOW_MODEL_REQUESTS is False
    with pytest.raises(RuntimeError, match="Model requests are not allowed"):
        pydantic_ai.models.check_allow_model_requests()
