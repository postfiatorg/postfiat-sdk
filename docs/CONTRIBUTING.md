# Contributing to PostFiat SDK

Thank you for your interest in contributing to the PostFiat SDK! This document outlines our development workflow, branch protection rules, and contribution guidelines.

## 🏗️ Repository Structure

This is a **proto-first SDK** with automated code generation:

```
postfiat-sdk/
├── .github/workflows/             # CI/CD automation
├── docs/                          # Documentation
├── overrides/                     # MkDocs overrides
├── proto/                         # Protocol buffer definitions
│   ├── postfiat/v3/              # Proto files (source of truth)
│   ├── buf.yaml                  # Buf configuration
│   └── buf.gen.yaml              # Code generation config
├── python/                        # Python SDK
│   ├── postfiat/                 # Python package
│   │   ├── v3/                   # Generated protobuf classes (ignored)
│   │   ├── types/                # Generated types (ignored)
│   │   ├── models/               # Generated models (ignored)
│   │   ├── services/             # Generated services (ignored)
│   │   └── client/               # Generated clients (ignored)
│   ├── scripts/                  # Python generation scripts
│   └── tests/                    # Python tests
│       ├── manual/               # Manual tests (committed)
│       └── generated/            # Auto-generated tests (ignored)
├── typescript/                    # TypeScript SDK
│   ├── src/                      # TypeScript source
│   ├── scripts/                  # TypeScript generation scripts
│   └── tests/                    # TypeScript tests
├── solidity/                      # Solidity contracts
│   ├── src/                      # Solidity source
│   └── test/                     # Solidity tests
├── scripts/                       # Root-level scripts
├── third_party/                   # Third-party dependencies
├── Makefile                       # Build orchestration
├── mkdocs.yml                     # Documentation config
└── VERSION                        # Version file
```

## 🔄 Development Workflow

### Branch Strategy

- **`main`** - Stable releases, managed via PR from dev
- **`dev`** - Development branch with clean source code only

### Branch Protection Rules

Both branches are protected with the following rules:

**Main Branch:**
- ✅ Requires PR with 1 approval
- ✅ Requires all CI checks to pass
- ✅ Prevents direct pushes
- ✅ Prevents force pushes and deletion
- ✅ Enforced on administrators

**Dev Branch:**
- ✅ Requires PR with 1 approval  
- ✅ Requires CI checks to pass
- ✅ More permissive for development

### Release Strategy

We use **git tags with artifacts** for releases:

**Development:**
- Generated files are **ignored** by .gitignore
- Developers run generation scripts locally
- Focus on source code changes

**Releases:**
- Create tags with "release-" prefix (e.g., `release-{{VERSION}}-rc1`)
- CI automatically builds Python (.whl/.tar.gz) and TypeScript (.tgz) packages
- Artifacts attached to GitHub releases for download
- No automatic publishing to npm/PyPI registries

## 🚀 Getting Started

### Prerequisites

- Python 3.10+ 
- Node.js 20+ (for TypeScript SDK)
- [Buf CLI](https://buf.build/docs/installation)
- Git
- [Foundry](https://getfoundry.sh/) (for Solidity development)

### Setup

1. **Clone and setup:**
   ```bash
   git clone --recurse-submodules https://github.com/postfiatorg/postfiat-sdk.git
   cd postfiat-sdk
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

   **Note:** The `--recurse-submodules` flag is important as this repository uses git submodules for third-party dependencies.

2. **Setup development environment:**
   ```bash
   # Install all dependencies and generate initial code
   make dev-setup
   ```

   **Or manually step by step:**
   ```bash
   # Install all dependencies
   make deps
   
   # Generate all code
   make regen-all
   ```

3. **Run tests:**
   ```bash
   # Run all tests (Python + TypeScript + Solidity)
   make tests
   
   # Or run individual test suites
   make tests-manual    # Manual Python tests only
   make ts-test         # TypeScript tests only
   make sol-test        # Solidity tests only
   ```

## 📝 Making Contributions

### 1. Create Feature Branch

```bash
git checkout dev
git pull origin dev
git checkout -b feature/your-feature-name
```

### 2. Make Changes

**For Proto Changes:**
- Edit files in `proto/postfiat/v3/`
- Run generation scripts to test locally
- Do NOT commit generated files

**For Manual Code:**
- **Python:** Edit source files in `python/postfiat/`
- **TypeScript:** Edit source files in `typescript/src/`
- **Solidity:** Edit source files in `solidity/src/`
- Add manual tests in respective test directories
- Follow existing code patterns and language conventions

### 3. Test Your Changes

```bash
# Regenerate all code with your changes
make regen-all

# Run all tests
make tests

# Verify package installation
pip install -e .
python -c "from postfiat.v3 import messages_pb2; print('✅ Package imports successfully')"
```

### 4. Create Pull Request

1. **Push your branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR:** `feature/your-feature-name` → `dev`

3. **PR Requirements:**
   - Clear description of changes
   - All CI checks must pass
   - 1 approval required
   - No direct pushes allowed

### 5. After Merge

The CI will automatically:
- Generate all code from your proto changes
- Run comprehensive test suite
- Auto-commit generated files to main branch (when dev → main)

## 🧪 Testing Guidelines

### Manual Tests
- Write in `tests/manual/`
- Test business logic, integration, edge cases
- Committed to git and run in CI

### Generated Tests
- Auto-created from proto definitions
- Test protobuf contracts and serialization
- Ignored by git, regenerated in CI

### Test Execution
```bash
# Run all tests (Python + TypeScript + Solidity)
make tests

# Run only manual Python tests
make tests-manual

# Run only generated Python tests
cd python && python -m pytest tests/generated/ -v

# Run TypeScript tests
make ts-test

# Run Solidity tests
make sol-test
```

## 🔧 Code Generation

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed information about the code generation process.

## 📋 PR Checklist

- [ ] Changes tested locally
- [ ] Generated code works correctly
- [ ] Manual tests added/updated if needed
- [ ] Proto changes follow existing patterns
- [ ] CI passes all checks
- [ ] Clear commit messages
- [ ] PR description explains changes

## 🆘 Getting Help

- **Issues:** Use GitHub Issues for bugs and feature requests
- **Discussions:** Use GitHub Discussions for questions
- **CI Problems:** Check the Actions tab for detailed logs

## 📜 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain code quality
- Follow existing patterns and conventions

Thank you for contributing to PostFiat SDK! 🚀

## 🛠️ Build & Test Workflow (Unified)

The Makefile at the project root now orchestrates all major development tasks for both Python and TypeScript SDKs. Use these targets for a consistent workflow:

### Setup
```bash
make dev-setup  # Installs all dependencies and generates code
```

### Code Generation
```bash
make proto          # Generate protobuf classes
make types          # Generate Python types
make tests-dynamic  # Generate dynamic proto tests (Python)
make regen-all      # Regenerate everything (proto + types + tests-dynamic)
```

### Testing
```bash
make tests-dynamic  # Generate dynamic proto tests (Python)
make tests-manual   # Run manual Python tests
make tests-core     # Run core dynamic Python tests
make tests-all      # Run all generated and manual Python tests
make ts-build       # Build TypeScript SDK
make ts-test        # Run TypeScript tests
make ts-test-all    # Run all TypeScript unit and integration tests
make sol-test       # Run Solidity tests
make tests          # Run all tests (Python + TypeScript + Solidity) - RECOMMENDED
make test           # Alias for 'tests'
```

- The `tests` target runs Python, TypeScript, and Solidity tests for full coverage.
- `test` is simply an alias for `tests`.
- All TypeScript and Solidity build/test commands are available via Makefile.

## 🧪 Running All Tests

To run all tests (Python + TypeScript + Solidity):
```bash
make tests
```

See `make help` for a full list of available targets.
