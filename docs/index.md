# PostFiat SDK Documentation

Welcome to the PostFiat SDK documentation. This is a proto-first, multi-language SDK with Python, TypeScript, and Solidity support.

## Latest Release: __RELEASE_TAG_PLACEHOLDER__

## Quick Start

### Python
```bash
# Install from PyPI (when published)
pip install postfiat-sdk==__VERSION_PLACEHOLDER__

# Or download from GitHub releases
# wget __DOWNLOAD_URL_PLACEHOLDER__/postfiat-sdk-__VERSION_PLACEHOLDER__.whl
# pip install postfiat-sdk-__VERSION_PLACEHOLDER__.whl
```

### TypeScript
```bash
# Install from npm (when published)
npm install @postfiat/sdk@__VERSION_PLACEHOLDER__

# Or download from GitHub releases
# wget __DOWNLOAD_URL_PLACEHOLDER__/postfiat-sdk-__VERSION_PLACEHOLDER__.tgz
# npm install postfiat-sdk-__VERSION_PLACEHOLDER__.tgz
```

### Solidity
```bash
# Clone the repository for Solidity development
git clone __REPO_URL_PLACEHOLDER__.git
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