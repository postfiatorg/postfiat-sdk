# PostFiat SDK Documentation

Welcome to the PostFiat SDK documentation. This is a proto-first, multi-language SDK with Python, TypeScript, and Solidity support.

## Latest Release: release-0.1.0-rc1

## Quick Start

### Python
```bash
# Install from PyPI (when published)
pip install postfiat-sdk==0.1.0-rc1

# Or download from GitHub releases
# wget https://github.com/allenday/pfsdk/releases/download/release-0.1.0-rc1/postfiat-sdk-0.1.0-rc1.whl
# pip install postfiat-sdk-0.1.0-rc1.whl
```

### TypeScript
```bash
# Install from npm (when published)
npm install @postfiat/sdk@0.1.0-rc1

# Or download from GitHub releases
# wget https://github.com/allenday/pfsdk/releases/download/release-0.1.0-rc1/postfiat-sdk-0.1.0-rc1.tgz
# npm install postfiat-sdk-0.1.0-rc1.tgz
```

### Solidity
```bash
# Clone the repository for Solidity development
git clone https://github.com/postfiat/pfsdk.git
cd pfsdk

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