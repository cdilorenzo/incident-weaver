# Knowledge Base

The V1 knowledge base contains a small curated set of fictional operational documents for the canonical `checkout-api` incident.

Documents are written specifically for this repository. A later slice will add
one document containing an indirect prompt-injection payload used by the
security/evaluation suite; it is intentionally absent from Slice 006.

The knowledge base is intentionally small; retrieval quality and evaluation matter more than corpus size.

Index explicitly from the repository root after setting Azure OpenAI and
PostgreSQL configuration:

```text
python src/ai-runtime/index_knowledge.py
```
