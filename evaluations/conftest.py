import sys
from pathlib import Path

import pydantic_ai.models

sys.path.insert(0, str(Path(__file__).parents[1] / "src" / "ai-runtime"))

# Evaluation cases run against fake/deterministic models only; never allow a real
# model request to escape from this suite.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False
