# PostFiat SDK

A proto-first, multi-language SDK with Python, TypeScript, and Solidity support for building AI-powered applications and smart contracts.

## 📚 Documentation

**[📖 Full Documentation](https://postfiat.org/postfiat-sdk)**

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Contributing Guidelines](docs/CONTRIBUTING.md)
- [API Reference](https://allenday.github.io/pfsdk/api/openapi/)

## 🚀 Quick Start

### Python
```bash
pip install postfiat-sdk
```

### TypeScript
```bash
npm install @postfiat/sdk
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

# Run tests
cd solidity && forge test

# Deploy contracts (local development)
cd solidity && npm run deploy:local
```

## 🏗️ Architecture

The SDK follows a **proto-first architecture** where Protocol Buffer definitions are the single source of truth for all generated code across multiple languages and platforms, including smart contracts.

See the [Architecture Documentation](docs/ARCHITECTURE.md) for detailed information.

## 🔧 Development

For development setup and contributing guidelines, see:
- [Development Guide](docs/DEVELOPMENT.md)
- [Contributing Guidelines](docs/CONTRIBUTING.md)
# Workflow Trigger Test
