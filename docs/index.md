# PostFiat SDK Documentation

Welcome to the PostFiat SDK documentation. This is a proto-first, multi-language SDK with Python, TypeScript, and Solidity support.

## Quick Start

### Python
```bash
# Install from PyPI (when published)
pip install postfiat-sdk=={{ config.extra.version }}

# Or download from GitHub releases
# wget {{ config.extra.release_url | replace("/tag/", "/download/") }}/postfiat-sdk-{{ config.extra.version }}.whl
# pip install postfiat-sdk-{{ config.extra.version }}.whl
```

### TypeScript
```bash
# Install from npm (when published)
npm install @postfiat/sdk@{{ config.extra.version }}

# Or download from GitHub releases
# wget {{ config.extra.release_url | replace("/tag/", "/download/") }}/postfiat-sdk-{{ config.extra.version }}.tgz
# npm install postfiat-sdk-{{ config.extra.version }}.tgz
```

### Solidity
```bash
# Clone the repository for Solidity development
git clone https://github.com/postfiatorg/postfiat-sdk.git
cd postfiat-sdk

# Install dependencies and generate contracts
make sol-deps
make proto
make sol-build
```

## Features

- **Proto-first architecture**: Single source of truth for all APIs
- **Multi-language support**: Python, TypeScript, and Solidity SDKs
- **Type-safe**: Generated types and validation across all languages
- **Modern tooling**: FastAPI, Pydantic, React hooks, Foundry
- **AI integration**: PydanticAI support for agents
- **Blockchain integration**: Smart contract generation and deployment

## API Documentation

- **[Python SDK API](python-api/)** - Complete Python API reference with mkdocstrings
- **[OpenAPI Specification](api/openapi/)** - Interactive REST API documentation

## Architecture

This SDK follows a **proto-first architecture** where Protocol Buffer definitions serve as the single source of truth for all generated code across multiple languages and platforms.