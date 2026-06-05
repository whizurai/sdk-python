# whizurai-sdk

Official Python SDK for the Whizurai Platform.

## Installation

```bash
pip install whizurai-sdk
```

## Quick Start

The SDK is **capability-first**: you execute published capabilities, track their
runs, and read the resulting artifacts.

```python
import asyncio
from whizurai import WhizuraiClient, ClientConfig

async def main():
    config = ClientConfig(
        api_key='your-api-key',
        base_url='https://api.whizurai.com',  # Optional
    )

    async with WhizuraiClient(config) as client:
        # 1. List published capabilities
        caps = await client.capabilities.list(status='published')

        # 2. Execute a capability
        run = await client.capabilities.run(
            'image.generate',
            {'prompt': 'a red bicycle'},
            idempotency_key='req-123',
        )

        # 3. Poll the run to completion
        done = await client.runs.poll_until_done(run.id)

        # 4. Read the produced artifacts
        artifacts = await client.runs.artifacts(done.id)
        for art in artifacts:
            print(art.url)

asyncio.run(main())
```

## Resources

| Resource | Methods |
|---|---|
| `client.capabilities` | `list`, `get`, `run`, `dry_run` |
| `client.runs` | `get`, `list`, `logs`, `artifacts`, `poll_until_done` |
| `client.artifacts` | `list`, `get` |
| `client.triggers` | `list`, `get`, `create`, `update`, `delete`, `test` |

Plus `client.health_check()`, `client.get_status()`, and `client.ping()`.

## Error Handling

All errors extend `WhizuraiError`:

```python
from whizurai import NotFoundError, AuthenticationError, WhizuraiError

try:
    await client.capabilities.run('invalid-id', {})
except NotFoundError:
    print('Capability not found')
except AuthenticationError:
    print('Check your API key')
except WhizuraiError as e:
    print('Platform error:', e)
```

## Documentation

- [Full Documentation](https://github.com/whizurai/docs)
- [API Reference](https://github.com/whizurai/docs/blob/main/api/README.md)
- [Examples](https://github.com/whizurai/examples)

## License

MIT
