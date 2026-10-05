# Changelog

## 2.1.1

### Fixed

- Runtime dependencies are compatible ranges instead of exact pins:
  `httpx>=0.25,<1`, `pydantic>=2.5,<3`, `python-dotenv>=1.0,<2`. They were
  `httpx==0.25.2`, `pydantic==2.5.0` and `python-dotenv==1.0.0`. Because
  `setup.py` installs `requirements.txt` as `install_requires`, the pins made the
  SDK impossible to install beside any application that needs a newer patch
  release, for example `httpx>=0.27`.

## 2.1.0

### Added

- `client.embed()` and `client.rerank()` for model-router's `POST /v1/embeddings`
  and `POST /v1/rerank`, with `whizai` provenance (`embedding_space`) and the
  `inference_base_url` option they require (#4).
- `rerank(..., fallback="original-order", timeout=...)` degradation mode.
- `assert_same_embedding_space()`, `embedding_space_of()`, `EmbeddingSpaceError`.
