# Contributing to InvenTree RMA Plugin

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/inventree-rma-plugin.git
   cd inventree-rma-plugin
   ```
3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Development Workflow

### Running Tests

```bash
pytest tests/ -v
```

### Running Linter

```bash
ruff check .
```

To auto-fix issues:
```bash
ruff check --fix .
```

### Code Style

This project uses [ruff](https://github.com/astral-sh/ruff) for linting. Please ensure your code passes all checks before submitting a PR.

## Pull Request Process

1. Create a new branch for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit with clear, descriptive messages

3. Ensure all tests pass and linting is clean:
   ```bash
   pytest tests/ -v
   ruff check .
   ```

4. Push to your fork and open a Pull Request

5. Describe your changes in the PR description, including:
   - What the change does
   - Why it's needed
   - Any breaking changes

## Testing with InvenTree

To test the plugin with a local InvenTree instance:

1. Set up InvenTree using Docker:
   ```bash
   git clone https://github.com/inventree/InvenTree.git
   cd InvenTree
   docker compose -f contrib/container/docker-compose.yml up -d
   ```

2. Install the plugin in development mode:
   ```bash
   docker compose exec inventree-server pip install -e /path/to/inventree-rma-plugin
   ```

3. Enable the required settings in InvenTree:
   - ENABLE_PLUGINS_APP
   - ENABLE_PLUGINS_URL
   - ENABLE_PLUGINS_INTERFACE

## Reporting Issues

When reporting issues, please include:
- InvenTree version
- Plugin version
- Steps to reproduce
- Expected vs actual behavior
- Any error messages or logs

## Questions?

Feel free to open an issue for any questions about contributing.
