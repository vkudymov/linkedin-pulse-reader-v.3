# PostAnalyzer

Source-agnostic post analysis library. It accepts a `list[dict]` of posts, uses an injected LLM client to:

- filter posts by relevance (LLM),
- generate comments for relevant posts (LLM),
- return a structured analysis result.

## Runtime-switchable LLM configuration

The library provides `LLMProviderManager` + `LLMFactory` to create and switch LLM providers/models at runtime **without changing business logic** (`RelevanceFilter`, `CommentGenerator`, `PostAnalyzer` only depend on the `LLMClient` protocol).

### Env variables (primary)

- `POST_ANALYZER_LLM_PROVIDER`: `openai` | `ollama` | `fake`
- `POST_ANALYZER_LLM_MODEL`: model name (required for `openai`/`ollama` in `real` mode)
- `POST_ANALYZER_LLM_MODE`: `real` | `fake` (default: `real`)
- `POST_ANALYZER_LLM_TIMEOUT_S`: request timeout (default: `30`)

OpenAI:

- `POST_ANALYZER_OPENAI_API_KEY` (backward compatible: `OPENAI_API_KEY`)
- `POST_ANALYZER_OPENAI_BASE_URL` (backward compatible: `OPENAI_BASE_URL`)
- `POST_ANALYZER_OPENAI_MODEL` (backward compatible: `OPENAI_MODEL`)

Ollama:

- `POST_ANALYZER_OLLAMA_BASE_URL` (backward compatible: `OLLAMA_BASE_URL` / `OLLAMA_HOST`)
- `POST_ANALYZER_OLLAMA_MODEL` (backward compatible: `OLLAMA_MODEL`)

### Env variables (fallback)

- `POST_ANALYZER_LLM_FALLBACK_PROVIDER`
- `POST_ANALYZER_LLM_FALLBACK_MODEL`
- `POST_ANALYZER_LLM_FALLBACK_MODE`
- `POST_ANALYZER_LLM_ENABLE_FALLBACK` (default: `true`)
- `POST_ANALYZER_LLM_FAILOVER_TO_FALLBACK` (default: `true`)

### Example: OpenAI (real)

```bash
export POST_ANALYZER_LLM_PROVIDER=openai
export POST_ANALYZER_LLM_MODEL=gpt-4.1-mini
export POST_ANALYZER_OPENAI_API_KEY=sk-...
```

### Example: Ollama (real)

```bash
export POST_ANALYZER_LLM_PROVIDER=ollama
export POST_ANALYZER_LLM_MODEL=llama3.1
export POST_ANALYZER_OLLAMA_BASE_URL=http://localhost:11434
```

### Example: Fake mode (tests/offline)

```bash
export POST_ANALYZER_LLM_MODE=fake
```

### Example: Fallback chain (OpenAI primary → Ollama fallback)

```bash
export POST_ANALYZER_LLM_PROVIDER=openai
export POST_ANALYZER_LLM_MODEL=gpt-4.1-mini
export POST_ANALYZER_OPENAI_API_KEY=sk-...

export POST_ANALYZER_LLM_FALLBACK_PROVIDER=ollama
export POST_ANALYZER_LLM_FALLBACK_MODEL=llama3.1
export POST_ANALYZER_OLLAMA_BASE_URL=http://localhost:11434
```

### Runtime switch example

```python
from post_analyzer import LLMProviderManager, LLMProviderSettings, load_llm_manager_settings_from_env

mgr = LLMProviderManager(settings=load_llm_manager_settings_from_env())

# Switch at runtime (with validation + health-check + rollback on failure)
mgr.switch(
    primary=LLMProviderSettings(provider="ollama", model="llama3.1", mode="real", base_url="http://localhost:11434"),
    fallback=None,
)
```

## Tests

```bash
pytest -q
```

