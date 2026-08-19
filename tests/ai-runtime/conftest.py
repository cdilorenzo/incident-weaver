import sys
from pathlib import Path

import pydantic_ai.models


sys.path.insert(0, str(Path(__file__).parents[2] / "src" / "ai-runtime"))

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False