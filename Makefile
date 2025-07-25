# PostFiat SDK Development Makefile
# 
# Common development tasks for the PostFiat SDK

.PHONY: help proto types tests tests-dynamic tests-core clean install dev-setup ts-build ts-test ts-test-all sol-deps sol-build sol-test sol-clean test bump-version bump-ts-version build-py build-ts build-sol docs release deps

# Default target
help:
	@echo "PostFiat SDK Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  install      Install package in development mode"
	@echo "  dev-setup    Complete development environment setup"
	@echo "  deps         Install all Python and TypeScript dependencies"
	@echo ""
	@echo "Code Generation:"
	@echo "  proto        Generate protobuf classes from .proto files"
	@echo "  types        Generate Python types (enums, exceptions)"
	@echo "  tests        Run all tests (Python + TypeScript + Solidity, canonical)"
	@echo "  tests-all    Run all generated and manual tests (Python + TypeScript + Solidity)"
	@echo "  tests-manual Run manual tests only (Python)"
	@echo "  ts-build     Build TypeScript SDK (npm run build)"
	@echo "  ts-test      Run TypeScript tests (npm test)"
	@echo "  ts-test-all  Run all TypeScript unit and integration tests"
	@echo "  test         Alias for 'tests' (run all tests)"
	@echo ""
	@echo "Build & Release:"
	@echo "  build-py     Build Python package(s) (.whl, .tar.gz)"
	@echo "  build-ts     Build TypeScript package(s) (.tgz)"
	@echo "  build-sol    Build Solidity contracts (Foundry)"
	@echo "  sol-deps     Install Solidity dependencies + protoc-gen-sol plugin"
	@echo "  sol-build    Compile Solidity contracts"
	@echo "  sol-test     Run Solidity tests"
	@echo "  sol-clean    Clean Solidity build artifacts"
	@echo "  release      Build all release artifacts (Python + TypeScript + Solidity)"
	@echo ""
	@echo "Documentation:"
	@echo "  docs         Build all documentation (mkdocs, Sphinx, TypeDoc, Swagger, etc.)"
	@echo ""
	@echo "Version Management:"
	@echo "  bump-version     Update all version strings from VERSION file (Python + TypeScript)"
	@echo "  bump-ts-version  Update TypeScript version strings only"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean        Clean generated files and caches"
	@echo "  regen-all    Regenerate everything (proto + types + tests)"

# Installation and setup
install:
	pip install -e .

dev-setup: install
	@echo "🚀 Setting up PostFiat SDK development environment..."
	@echo "📦 Installing development dependencies..."
	pip install -e ".[dev]"
	@echo "🔧 Generating initial code..."
	$(MAKE) regen-all
	@echo "✅ Development setup complete!"

# Install all dependencies
deps:
	@echo "📦 Installing Python dependencies..."
	pip install -e .
	pip install -e "python/[dev]"
	pip install build twine mkdocs mkdocs-material mkdocs-swagger-ui-tag mkdocstrings[python] mkdocs-mermaid2-plugin
	@echo "📦 Installing TypeScript dependencies..."
	cd typescript && (test -d node_modules || npm ci || npm install)
	@echo "🔧 Installing buf CLI tool..."
	@if [ ! -f bin/buf ]; then \
		echo "📥 Downloading buf CLI tool..."; \
		mkdir -p bin && \
		curl -sSL "https://github.com/bufbuild/buf/releases/latest/download/buf-$$(uname -s)-$$(uname -m)" -o bin/buf && \
		chmod +x bin/buf && \
		echo "✅ buf CLI tool installed successfully"; \
	else \
		echo "✅ buf CLI tool already exists"; \
	fi
	@$(MAKE) sol-deps

# Code generation
proto: deps
	@echo "🔄 Generating protobuf classes..."
	cd proto && ../bin/buf generate --template buf.gen.yaml
	@echo "🔧 Fixing empty structs in Solidity files..."
	@cd . && ./scripts/fix-empty-structs.sh
	@echo "✅ Protobuf generation complete (Python, TypeScript, Solidity)"

types:
	@echo "🔄 Generating Python types..."
	cd python && python scripts/generate_python_types.py

tests-dynamic:
	@echo "🔄 Generating dynamic proto tests..."
	cd python && python scripts/generate_dynamic_protobuf_tests.py

# Testing
# Canonical: run all tests in all languages
tests:
	@echo "🧪 Running manual Python tests..."
	cd python && python -m pytest tests/manual/ -v
	@echo "🧪 Running core dynamic Python tests..."
	cd python && python scripts/dev_test_regen.py --run-tests --core-only
	@echo "🧪 Running all TypeScript unit and integration tests..."
	cd typescript && (test -d node_modules || timeout 300 npm install) && npm run test:all
	@echo "🧪 Running Solidity tests..."
	cd solidity && export PATH="$$HOME/.foundry/bin:$$PATH" && forge test
	@echo "✅ All Python, TypeScript, and Solidity tests completed!"

test: tests

# All generated and manual tests (Python + TypeScript + Solidity)
tests-all:
	@echo "🧪 Running all generated Python tests..."
	cd python && python -m pytest tests/generated/ -v
	@echo "🧪 Running manual Python tests..."
	cd python && python -m pytest tests/manual/ -v
	@echo "🧪 Running all TypeScript unit and integration tests..."
	cd typescript && (test -d node_modules || timeout 300 npm install) && npm run test:all
	@echo "🧪 Running Solidity tests..."
	cd solidity && export PATH="$$HOME/.foundry/bin:$$PATH" && forge test
	@echo "✅ All Python, TypeScript, and Solidity tests completed!"

tests-manual:
	@echo "🧪 Running manual tests..."
	cd python && python -m pytest tests/manual/ -v

# TypeScript build and test
ts-build:
	@echo "🔨 Building TypeScript SDK..."
	cd typescript && (test -d node_modules || timeout 300 npm install) && npm run build

ts-test:
	@echo "🧪 Running TypeScript tests..."
	cd typescript && (test -d node_modules || timeout 300 npm install) && npm test

ts-test-all:
	@echo "🧪 Running all TypeScript unit and integration tests..."
	cd typescript && (test -d node_modules || timeout 300 npm install) && npm run test:all

# Unified test target
# test: tests-manual tests-core ts-test-all # This line is now redundant as 'test' is an alias for 'tests'

# Maintenance
clean:
	@echo "🧹 Cleaning generated files and caches..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf tests/generated/*.py 2>/dev/null || true
	rm -f bin/buf 2>/dev/null || true
	@echo "✅ Cleanup complete"

regen-all: proto types tests
	@echo "✅ All code generation complete!"

# CI simulation
ci-check:
	@echo "🔍 Running CI checks locally..."
	python scripts/ci_test_generation.py --validate-only
	python scripts/ci_test_generation.py --force

# Development workflow shortcuts
dev-proto: proto types tests tests-core
	@echo "✅ Proto development workflow complete!"

dev-quick: tests tests-core
	@echo "✅ Quick test regeneration complete!"

# Version bumping
bump-version: proto
	@echo "🔢 Bumping all version strings from VERSION file..."
	./scripts/update-all-versions.sh

bump-ts-version:
	@echo "🔢 Bumping TypeScript version strings from VERSION file..."
	cd typescript && node scripts/update-version.js

# Build Python package(s)
build-py:
	@echo "📦 Building Python package(s)..."
	cd python && python -m build

# Build TypeScript package(s)
build-ts:
	@echo "📦 Generating TypeScript code..."
	cd typescript && npm run generate:all
	@echo "📦 Building TypeScript package(s)..."
	cd typescript && npm run build && npm pack

# Build all documentation (mkdocs, Sphinx, TypeDoc, Swagger, etc.)
docs:
	@echo "📚 Building documentation..."
	# Generate OpenAPI specification from protobuf
	cd proto && ../bin/buf generate --template buf.gen.openapi-only.yaml
	# Generate protobuf documentation and copy API specs
	python scripts/generate_docs.py
	# TypeScript codegen (ensure src/index.ts exists)
	cd typescript && npm run generate:all
	# TypeScript API docs (TypeDoc)
	cd typescript && npx typedoc --out ../docs/generated/typescript src/index.ts --plugin typedoc-plugin-markdown --theme markdown --skipErrorChecking
	# Update documentation with current version info
	@echo "🔢 Updating documentation versions..."
	@./scripts/update-all-versions.sh > /dev/null 2>&1 || echo "⚠️  Version update had some warnings (proto generation issues - this is normal)"
	# MkDocs site (now includes Python API docs via mkdocstrings)
	mkdocs build
	@echo "✅ Documentation build complete!"

# Solidity development
sol-deps:
	@echo "📦 Installing Solidity dependencies..."
	cd solidity && (test -d node_modules || npm install)
	@echo "🔧 Building protoc-gen-sol plugin from submodule..."
	@if [ ! -f solidity/protoc-gen-sol/bin/protoc-gen-sol ]; then \
		echo "🔨 Building protoc-gen-sol binary from submodule..."; \
		cd solidity/protoc-gen-sol && make build && \
		echo "✅ protoc-gen-sol plugin built successfully"; \
	else \
		echo "✅ protoc-gen-sol plugin already built"; \
	fi

sol-build: sol-deps
	@echo "🔨 Building Solidity contracts..."
	cd solidity && export PATH="$$HOME/.foundry/bin:$$PATH" && forge build

sol-test: sol-deps
	@echo "🧪 Running Solidity tests..."
	cd solidity && export PATH="$$HOME/.foundry/bin:$$PATH" && forge test

sol-clean:
	@echo "🧹 Cleaning Solidity build artifacts..."
	cd solidity && forge clean
	rm -rf solidity/src/generated/* 2>/dev/null || true
	rm -f solidity/protoc-gen-sol 2>/dev/null || true

# Build Solidity package
build-sol: sol-deps
	@echo "📦 Building Solidity contracts..."
	@echo "🔧 Running fix-empty-structs.sh first..."
	./scripts/fix-empty-structs.sh
	@echo "🔧 Fixing remaining issues..."
	cd solidity && find src/generated -name "*.sol" -exec sed -i '' '/^struct Empty {/,/^}/d' {} \;
	cd solidity && find src/generated -name "*.sol" -exec sed -i '' '/^library Google_Protobuf {/,/^}/d' {} \;
	cd solidity && find src/generated -name "*.sol" -exec sed -i '' 's/UnknownType/Google_Protobuf.UnknownType/g' {} \;
	cd solidity && find src/generated -name "*.sol" -exec sed -i '' 's/SendMessageConfiguration memory/A2a_V1.SendMessageConfiguration memory/g' {} \;
	cd solidity && find src/generated -name "*.sol" -exec sed -i '' 's/Task memory/A2a_V1.Task memory/g' {} \;

	@echo "📦 Compiling Solidity contracts..."
	cd solidity && export PATH="$$HOME/.foundry/bin:$$PATH" && forge build

# Build all release artifacts (Python + TypeScript + Solidity)
release: build-py build-ts build-sol
	@echo "🎉 All release artifacts built!"
