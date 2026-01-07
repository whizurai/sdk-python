# whizurai-sdk

Official Python SDK for the Whizurai Platform.

## Installation

```bash
pip install whizurai-sdk
```

## Quick Start

```python
from whizurai import WhizuraiClient, ClientConfig, GenerateRequest

config = ClientConfig(
    api_key='your-api-key',
    base_url='https://api.whizurai.com'  # Optional
)

async with WhizuraiClient(config) as client:
    response = await client.generate(
        GenerateRequest(prompt='Hello, world!', model='gpt-4')
    )
    print(response.content)
```

## Documentation

- [Full Documentation](https://github.com/whizurai/docs)
- [API Reference](https://github.com/whizurai/docs/blob/main/api/README.md)
- [Examples](https://github.com/whizurai/examples)

## License

MIT
