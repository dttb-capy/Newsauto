# Contributing to Newsauto

Thank you for your interest in contributing to Newsauto! We welcome contributions from the community and are grateful for any help you can provide.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Pull Request Process](#pull-request-process)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:

- **Be respectful** of different viewpoints and experiences
- **Be constructive** in your feedback and criticism
- **Be inclusive** and welcoming to all contributors
- **Be professional** in all interactions

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/newsauto.git
   cd newsauto
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/originalowner/newsauto.git
   ```
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## How to Contribute

### Reporting Bugs

Before reporting a bug, please:
1. Check the [existing issues](https://github.com/yourusername/newsauto/issues) to avoid duplicates
2. Use the bug report template
3. Include:
   - Clear description of the issue
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, GPU)
   - Relevant logs or error messages

### Suggesting Features

We love feature suggestions! Please:
1. Check if the feature is already requested
2. Use the feature request template
3. Explain the use case and benefits
4. Consider if it aligns with project goals

### Contributing Code

#### Types of Contributions

- **Bug fixes**: Fix reported issues
- **Features**: Implement new functionality
- **Performance**: Optimize existing code
- **Documentation**: Improve or add documentation
- **Tests**: Add missing tests
- **Refactoring**: Improve code quality

#### Small Changes
For small changes (typos, simple bug fixes):
1. Make your changes
2. Test locally
3. Submit a pull request

#### Large Changes
For significant features or changes:
1. **Discuss first** by opening an issue
2. Wait for maintainer feedback
3. Implement after approval
4. Submit pull request

## Development Setup

### Prerequisites

```bash
# System requirements
- Python 3.12+
- NVIDIA GPU with CUDA support
- 16GB RAM minimum
- Git

# Install development dependencies
pip install -r requirements-dev.txt
```

### Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate      # Windows

# Install dependencies
pip install -e .  # Install in development mode
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=newsauto --cov-report=html

# Run specific test file
pytest tests/test_llm_integration.py

# Run with verbose output
pytest -v

# Run only fast tests
pytest -m "not slow"
```

## Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:
- **Line length**: 88 characters (Black default)
- **Imports**: Sorted with `isort`
- **Formatting**: Enforced with `Black`
- **Linting**: Checked with `ruff`

```bash
# Format code
black .

# Sort imports
isort .

# Lint code
ruff check .

# Type checking
mypy newsauto/
```

### Code Structure

```python
# Good example
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class NewsletterGenerator:
    """Generate newsletters from content items.

    Attributes:
        template: Email template to use
        max_items: Maximum number of items per newsletter
    """

    def __init__(self, template: str, max_items: int = 10):
        self.template = template
        self.max_items = max_items

    def generate(self, content: List[dict]) -> Optional[str]:
        """Generate newsletter HTML from content.

        Args:
            content: List of content items

        Returns:
            Generated HTML or None if generation fails
        """
        try:
            # Implementation
            pass
        except Exception as e:
            logger.error(f"Failed to generate newsletter: {e}")
            return None
```

### Commit Messages

Follow the Conventional Commits specification:

```
type(scope): subject

body

footer
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```bash
feat(llm): add support for Llama 3.2 model
fix(api): handle missing subscriber email
docs(readme): update installation instructions
perf(cache): optimize LLM response caching
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring
- `test/description` - Test additions

## Pull Request Process

### Before Submitting

1. **Update your fork**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests**:
   ```bash
   pytest
   black --check .
   ruff check .
   ```

3. **Update documentation** if needed

4. **Add tests** for new features

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Updated existing tests

## Checklist
- [ ] Code follows style guide
- [ ] Self-reviewed code
- [ ] Updated documentation
- [ ] Added changelog entry
```

### Review Process

1. **Automated checks** must pass
2. **Code review** by maintainers
3. **Address feedback** promptly
4. **Approval** from at least one maintainer
5. **Merge** when ready

## Testing Guidelines

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
└── fixtures/      # Test data
```

### Writing Tests

```python
# tests/unit/test_summarizer.py
import pytest
from newsauto.llm import Summarizer


class TestSummarizer:
    @pytest.fixture
    def summarizer(self):
        return Summarizer(model="test-model")

    def test_summarize_short_text(self, summarizer):
        text = "Short article about AI."
        summary = summarizer.summarize(text)
        assert len(summary) < len(text)
        assert summary is not None

    @pytest.mark.slow
    def test_summarize_long_text(self, summarizer):
        text = "Very long article..." * 1000
        summary = summarizer.summarize(text, max_length=100)
        assert len(summary) <= 100
```

### Test Coverage

We aim for:
- **80% overall coverage**
- **100% for critical paths**
- **Integration tests for APIs**
- **E2E tests for workflows**

## Documentation

### Documentation Types

1. **Code comments**: Explain complex logic
2. **Docstrings**: Document all public functions/classes
3. **README**: Project overview and setup
4. **API docs**: Generated from docstrings
5. **User guides**: How-to documentation
6. **Architecture**: System design documentation

### Docstring Format

```python
def process_content(
    content: str,
    model: str = "mistral",
    max_length: int = 500
) -> dict:
    """Process content and generate summary.

    Args:
        content: Raw content to process
        model: LLM model to use for summarization
        max_length: Maximum summary length in tokens

    Returns:
        Dictionary containing:
            - summary: Generated summary text
            - model_used: Model that was used
            - processing_time: Time in milliseconds

    Raises:
        ValueError: If content is empty
        ModelError: If model fails to generate summary

    Example:
        >>> result = process_content("Long article text...")
        >>> print(result["summary"])
        "This article discusses..."
    """
    pass
```

## Project Structure

### Adding New Features

1. **Create module** in appropriate package
2. **Add tests** in corresponding test directory
3. **Update documentation**
4. **Add to API** if user-facing
5. **Update changelog**

### File Organization

```
newsauto/
├── core/          # Core business logic
├── api/           # API endpoints
├── llm/           # LLM integration
├── scrapers/      # Content scrapers
├── models/        # Database models
├── utils/         # Utility functions
└── config/        # Configuration
```

## Performance Guidelines

### Optimization Checklist

- [ ] Profile before optimizing
- [ ] Use appropriate data structures
- [ ] Implement caching where beneficial
- [ ] Batch operations when possible
- [ ] Use async/await for I/O operations
- [ ] Monitor memory usage

### Benchmarking

```python
# Add benchmarks for performance-critical code
import time


def benchmark_summarization():
    start = time.perf_counter()
    # Run summarization
    end = time.perf_counter()
    assert (end - start) < 1.0  # Should complete in under 1 second
```

## Security Guidelines

### Security Checklist

- [ ] Never commit secrets or API keys
- [ ] Validate all user input
- [ ] Use parameterized queries
- [ ] Implement rate limiting
- [ ] Follow OWASP guidelines
- [ ] Keep dependencies updated

### Reporting Security Issues

For security vulnerabilities:
1. **DO NOT** open a public issue
2. Email security@newsauto.io
3. Include detailed description
4. Wait for acknowledgment

## Release Process

### Version Numbers

We use Semantic Versioning (SemVer):
- **MAJOR**: Breaking API changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes

### Release Checklist

1. Update version in `__init__.py`
2. Update CHANGELOG.md
3. Run full test suite
4. Build documentation
5. Create release PR
6. Tag release after merge
7. Publish to PyPI

## Community

### Getting Help

- **Documentation**: Read the docs first
- **Issues**: Search existing issues
- **Discussions**: Ask in GitHub Discussions
- **Discord**: Join our community server

### Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to:
- Open an issue for clarification
- Ask in discussions
- Contact maintainers

Thank you for contributing to Newsauto! 🚀