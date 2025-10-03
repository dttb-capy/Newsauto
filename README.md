# 🚀 Newsauto - Automated Newsletter Platform

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ollama](https://img.shields.io/badge/Powered%20by-Ollama-green.svg)](https://ollama.com/)
[![GPU: NVIDIA](https://img.shields.io/badge/GPU-NVIDIA%20RTX-76B900.svg)](https://www.nvidia.com/)

A zero-cost, fully automated newsletter platform that leverages local LLMs to aggregate, summarize, and distribute high-quality content to targeted audiences.

## ✨ Features

- **🤖 Local LLM Integration**: Runs entirely on your GPU with Mistral, DeepSeek, and other models
- **📰 Multi-Source Aggregation**: RSS feeds, Reddit, HackerNews, and web scraping
- **✉️ Automated Delivery**: Schedule and send newsletters automatically
- **📊 Analytics Dashboard**: Track opens, clicks, and engagement
- **🎯 Audience Segmentation**: Target specific subscriber groups
- **💰 Zero Operating Cost**: No API fees, runs locally
- **🔒 Privacy-First**: Your data never leaves your machine
- **⚡ High Performance**: Process 100+ articles per minute on RTX 4070+

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/newsauto.git
cd newsauto

# Run the setup script
./scripts/setup.sh

# Start the application
python main.py
```

Visit `http://localhost:8000` to access the dashboard.

## 📋 Requirements

### Hardware
- **GPU**: NVIDIA GPU with 8GB+ VRAM (RTX 3060 or better)
- **RAM**: 16GB recommended
- **Storage**: 20GB free space

### Software
- Ubuntu 22.04+ / macOS 12+ / Windows 11
- Python 3.12+
- CUDA 11.8+ (for NVIDIA GPUs)
- Ollama

## 🛠️ Installation

### 1. Install Ollama

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull mistral:7b-instruct
ollama pull deepseek-r1:7b
```

### 2. Set up Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
python scripts/init_db.py
```

### 4. Configure Settings

```bash
cp .env.example .env
# Edit .env with your settings
```

## 📖 Documentation

- [Getting Started Guide](docs/getting-started/quickstart.md)
- [Architecture Overview](ARCHITECTURE.md)
- [API Reference](docs/technical/api-reference.md)
- [LLM Configuration](docs/technical/llm-integration.md)
- [Deployment Guide](docs/deployment/local-setup.md)
- [Contributing](CONTRIBUTING.md)

## 🎯 Use Cases

Perfect for creating automated newsletters for:
- **Tech Leaders**: CISO security briefings, CTO insights
- **Developers**: Language-specific updates, framework news
- **Investors**: Market analysis, startup trends
- **Researchers**: Academic papers, industry reports
- **Communities**: Niche interest groups, professional networks

## 🏗️ Project Structure

```
Newsauto/
├── core/               # Core business logic
├── scrapers/           # Content aggregation modules
├── newsletter/         # Newsletter generation
├── subscribers/        # Subscriber management
├── delivery/           # Email delivery system
├── api/                # FastAPI backend
├── web/                # Frontend interface
├── data/               # Database and cache
├── scripts/            # Automation scripts
└── docs/               # Documentation
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linter
ruff check .

# Format code
black .
```

## 📊 Performance

On an RTX 4070 Ti SUPER (16GB VRAM):
- **Summarization Speed**: 60-80 tokens/sec
- **Articles Processed**: 100+ per minute
- **Newsletter Generation**: < 30 seconds
- **Memory Usage**: 8-10GB VRAM

## 🗺️ Roadmap

- [x] Local LLM integration
- [x] Multi-source content aggregation
- [x] Email delivery system
- [x] Basic analytics
- [ ] Web-based template editor
- [ ] Advanced personalization
- [ ] Multi-language support
- [ ] Mobile app
- [ ] Cloud deployment option

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.com/) for local LLM serving
- [Mistral AI](https://mistral.ai/) for their excellent models
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- The open-source community

## 💬 Support

- [Documentation](https://github.com/yourusername/newsauto/wiki)
- [Issues](https://github.com/yourusername/newsauto/issues)
- [Discussions](https://github.com/yourusername/newsauto/discussions)

---

**Built with ❤️ for the newsletter automation community**