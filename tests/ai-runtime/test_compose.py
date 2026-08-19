from pathlib import Path


def test_ai_runtime_has_no_published_host_port() -> None:
    compose = (Path(__file__).parents[2] / "compose.yaml").read_text()
    ai_runtime = compose.split("  ai-runtime:\n", maxsplit=1)[1]

    assert "\n    ports:" not in ai_runtime