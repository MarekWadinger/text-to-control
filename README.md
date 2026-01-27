# Text-to-control: Agent-based framework for automated control system design

[![Quality and Tests](https://github.com/yourusername/text-to-control/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/text-to-control/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yourusername/text-to-control/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/text-to-control)

Text-to-control is a framework that automatically generates and tests control algorithms from natural language using agent-based architecture. It translates requirements, produces code, and validates performance, enabling transition from traditional to advanced control.

## 🚀 Quickstart

Basic usage:

```python
# TODO: Add quickstart example
```

## 🛠 Installation

Requires Python 3.12 or higher.

**Requirements:**

- Python 3.12+
- [UV](https://docs.astral.sh/uv/) package manager
- [Just](https://github.com/casey/just) (optional, for task running)

**Installation:**

```bash
git clone https://github.com/MarekWadinger/text-to-control.git
cd text-to-control
```

**Environment:**

Install dependencies using `uv`:

```bash
just install
# or manually:
uv sync
```

### Development Workflow

```bash
just install-hooks
just check
```

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss what you would like to change.

### Development Setup

1. Fork the repository
1. Create a feature branch (`git checkout -b feature/amazing-feature`)
1. Install development dependencies (`uv sync --dev`)
1. Install pre-commit hooks (`uv run pre-commit install`)
1. Make your changes
1. Commit your changes (`git commit -m 'feat: add amazing feature'`)
1. Push to the branch (`git push origin feature/amazing-feature`)
1. Open a Pull Request

## 📄 License

Run-only. No modification or redistribution without explicit author permission - see the [LICENSE](LICENSE) file for details.

## 📞 Support

If you encounter any issues or have questions:

- Open an [issue](https://github.com/MarekWadinger/text-to-control/issues) on GitHub
- Check the existing documentation and examples
- Review the test cases for usage patterns
