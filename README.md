# PostFiat SDK

SDK for the Post Fiat Network, a blockchain (currently XRPL) to have AI agents coordinate and communicate task workflows to allow users to work for them in exchange for PFT rewards.

## Table of Contents
- [Project Structure](#project-structure)
- [Local Development](#local-development)
  - [Setting Up Virtual Environment](#setting-up-virtual-environment)
  - [Running Services Locally](#running-services-locally)
- [Package Management](#package-management)
  - [AWS CodeArtifact Configuration](#aws-codeartifact-configuration)
  - [Installing Packages](#installing-packages)
  - [Publishing Packages](#publishing-packages)

## Project Structure

### Modules

- **Top-level Models** (`postfiat/models`)
  - Data models for the Post Fiat Network general to all node types
  - `Transaction` is our model for blockchain transactions that can be converted to internal models or to XRPL transactions

- **Task Node Libraries** (`postfiat/nodes/task/`)
  - Codecs for encoding and decoding messages to and from transactions
  - Models for the task node's state and message types
  - Event sourcing of current state from a stream of messages

- **RPC Clients** (`postfiat/rpc/`)
  - PFT clients (currently XRPL) for fetching and submitting transactions
  - Local caching of transaction history

- **Utils** (`postfiat/utils/`)
  - `streams.py` contains utilities for working with streams of events

### Directory Structure

- src/
  - postfiat/
    - models/
    - nodes/
      - task/
        - codecs/  # codecs to go between task node messages and transactions
        - models/  # models for the task node's message types
        - state/   # event sourcing of current state from a stream of messages
        - constants.py
    - rpc/         # RPC clients for PFTs
    - utils/
      - streams/  # utilities for working with streams of events
    - pyproject.toml
