# Changelog

## 2.7.0

### Added

- `client.outcomes` (`OutcomesResource`) for interactive outcome runs
  (whizai-platform#905): `run(slug, inputs, execution_policy=..., app_id=...,
  variant=..., idempotency_key=..., customer_id=...)`, `get_run(id)`
  (`OutcomeRun.interactive`), `workspace(id)`, `command(id, command,
  client_action_id=None)` (UUID4 generated when omitted, none sent for a
  `preview` command), `invocation(id, invocation_id)` and `events(id)`.
  Types: `OutcomeExecutionPolicy`, `OutcomeRunHandle`, `OutcomeRun`,
  `OutcomeRunEvent` (mirroring `@whizurai/types` 1.9.0). The workspace,
  command response and invocation detail are plain dicts.

### Fixed

- `SDK_VERSION` (the `User-Agent` version) read 2.5.0 in 2.6.0; it now matches
  the package version, and a test keeps them equal.

## 2.6.0

### Added

- Typed `image:generate@v4` input: `IMAGE_GENERATE`, `ImageGenerateInput`,
  `ImageGenerateReference` (mirroring `@whizurai/types` 1.6.0). v4 adds an
  optional reference image (`reference_image_url` | `reference_image_artifact_id`
  | `reference_image_base64` + `reference_image_content_type`, with
  `reference_strength` 0.05-0.95), honoured on the local fleet as img2img. The
  model refuses two sources, a reference without a strength and a strength
  without a reference. No new method: `client.capabilities.run(IMAGE_GENERATE, ...)`.

## 2.5.0

### Added

- `client.get_video_routes()` for `GET /v1/model-router/video-routes`: which
  video models a requirements-routed shot can land on, per route tier, and
  whether the router picks each automatically or only when named. Types:
  `VideoRouteTable`, `VideoRouteTableEntry`, `VideoRouteTierSummary`
  (snake_case attributes over the camelCase wire; mirrors `@whizurai/types` 1.5.0).

## 2.4.0

### Added

- `client.generate_text(prompt, ...)` for the gateway's `POST /v1/generate/text`
  and `client.describe_image(image=... | image_url=..., ...)` for
  `POST /v1/images/describe`. Both go to `base_url` (the api-gateway), not
  model-router: the gateway takes the app from the key, rate-limits, and leases
  the work on the fleet under that app's policy. Declare
  `metadata={"priority": ...}`. Keyword arguments are snake_case and map to the
  camelCase wire; `timeout` (seconds) bounds the HTTP call. Neither is retried
  by the client, so one call is at most one inference. Types:
  `GenerateTextResponse`, `GenerateTextChoice`, `DescribeImageResponse`
  (mirroring `@whizurai/types/gateway-inference` 1.4.0 and sdk-js 3.3.0).

## 2.3.1

### Fixed

- The default `base_url` (and the `WHIZURAI_BASE_URL` fallback) is now
  `https://api.whizur.ai`. It was `https://api.whizurai.com`, which does not
  resolve, so a client created without `base_url` could not connect.

## 2.3.0

### Added

- `speech:synthesize` third engine `qwen3-tts` (Qwen3-TTS 1.7B Base, voice
  cloning). `SpeechEngine` gains `"qwen3-tts"`; `SpeechSynthesizeInput` gains
  `reference_text` (wire `referenceText`, 1-2000 chars). For `qwen3-tts`,
  `reference_audio_artifact_id` and `reference_text` are required and `voice`,
  `speed`, `exaggeration`, `cfg_weight` are refused; `reference_text` is refused
  for the other engines. The platform enforces this (400 `invalid_option`).
- `SpeechSynthesizeResult` gains `reference_audio_sha256` and
  `reference_text_sha256` (`Optional[str]`, default `None` so older results
  still parse). Never `None` for `qwen3-tts`.
- `client.transcribe(...)` for model-router's `POST /v1/audio/transcriptions`
  (needs `inference_base_url`), returning `AudioTranscriptionResponse`
  (`text`, `language`, `duration`, `segments`, `provider`, `model`,
  `request_id`). A `202` pending answer raises `TranscriptionPendingError`.
  New exports: `AudioTranscriptionResponse`, `TranscriptionSegment`,
  `TranscriptionResponseFormat`, `TranscriptionPendingError`.
- `SpeechSynthesizeResult` gains `words` (`List[SpeechWordTiming]`:
  `start_ms`, `end_ms`, `char_start`, `char_end` in the text as sent; no word
  text) and `timing` (`SpeechTimingProvenance`: `source` `engine` or `aligned`,
  the aligner `model`, a `confidence`) for read-along. Both default to `None`,
  so results from older platforms still parse. New exports: `SpeechWordTiming`,
  `SpeechTimingProvenance`.

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
