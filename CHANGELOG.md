# Changelog

## 2.2.0

### Added

- Typed `speech:synthesize` shapes: `SPEECH_SYNTHESIZE`, `SpeechSynthesizeInput`,
  `SpeechSynthesizeResult`, `SpeechWarning`, `SpeechEngine`, `SpeechPriority`.
  No new endpoint: run it with `client.capabilities.run(SPEECH_SYNTHESIZE, ...)`
  and serialize the input with `model_dump(by_alias=True, exclude_none=True)`.
  The capability is flag-gated on the platform and ships as draft.
- `client.capabilities.cancel(run_id)` for the existing
  `POST /v1/capabilities/capability-runs/:runId/cancel`. It marks the run and
  cancels its workflow run best-effort; stopping work already on a worker is a
  platform follow-up.
- `client.artifacts.download(artifact_id)` returning the artifact's bytes.
  Credentials go to the gateway only: an absolute URL on another origin, and any
  redirect off the gateway, is fetched without `Authorization` or `X-API-Key`.

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
