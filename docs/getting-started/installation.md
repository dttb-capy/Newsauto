# 📦 Installation Guide

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04+ / macOS 12+ / Windows 10+
- **CPU**: 4 cores, 2.4GHz+
- **RAM**: 8GB (16GB recommended)
- **GPU**: NVIDIA GPU with 8GB+ VRAM (GTX 1070 or better)
- **Storage**: 20GB free space
- **Python**: 3.12 or higher
- **CUDA**: 11.8+ (for NVIDIA GPUs)

### Recommended Setup
- **GPU**: NVIDIA RTX 3060 or better (12GB+ VRAM)
- **RAM**: 16GB or more
- **Storage**: 50GB SSD space
- **Internet**: Stable connection for initial setup

## Pre-Installation

### 1. Check System Compatibility

```bash
# Check Python version
python3 --version

# Check GPU (NVIDIA)
nvidia-smi

# Check CUDA version
nvcc --version

# Check available disk space
df -h

# Check RAM
free -h
```

### 2. Update System Packages

#### Ubuntu/Debian
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git build-essential
```

#### macOS
```bash
brew update && brew upgrade
brew install curl wget git
```

#### Windows
Use WSL2 (Windows Subsystem for Linux) for best compatibility:
```powershell
wsl --install
# Then follow Ubuntu instructions inside WSL
```

## Installation Steps

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/newsauto.git
cd newsauto

# Or download and extract
wget https://github.com/yourusername/newsauto/archive/main.zip
unzip main.zip
cd newsauto-main
```

### Step 2: Install Ollama

#### Automatic Installation (Recommended)
```bash
# Run the Ollama installer
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
```

#### Manual Installation
```bash
# Download Ollama binary
wget https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64
chmod +x ollama-linux-amd64
sudo mv ollama-linux-amd64 /usr/local/bin/ollama

# Create systemd service
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

# Check service status
sudo systemctl status ollama
```

### Step 3: Download LLM Models

```bash
# Pull primary model (Mistral)
ollama pull mistral:7b-instruct
# Download size: ~4.1GB

# Pull analytical model (DeepSeek)
ollama pull deepseek-r1:7b
# Download size: ~4.5GB

# Pull fast classifier (Phi-3)
ollama pull phi-3
# Download size: ~2.3GB

# List installed models
ollama list
```

### Step 4: Python Environment Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip
```

### Step 5: Install Python Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Or install manually
pip install \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    sqlalchemy==2.0.25 \
    ollama==0.1.6 \
    transformers==4.37.0 \
    torch==2.1.2 \
    feedparser==6.0.11 \
    beautifulsoup4==4.12.3 \
    praw==7.7.1 \
    python-dotenv==1.0.0 \
    pydantic==2.5.3 \
    aiofiles==23.2.1 \
    httpx==0.26.0 \
    python-multipart==0.0.6 \
    python-jose[cryptography]==3.3.0 \
    passlib[bcrypt]==1.7.4 \
    schedule==1.2.0
```

### Step 6: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

Example `.env` file:
```bash
# Application Settings
APP_NAME=Newsauto
APP_VERSION=1.0.0
DEBUG=False
SECRET_KEY=your-secret-key-here-change-this

# Database
DATABASE_URL=sqlite:///./data/newsletter.db
# For PostgreSQL: postgresql://user:pass@localhost/newsauto

# Ollama Settings
OLLAMA_HOST=http://localhost:11434
OLLAMA_TIMEOUT=120
OLLAMA_GPU_LAYERS=-1

# Email Settings (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=Newsletter <your-email@gmail.com>

# Content Sources
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-secret
REDDIT_USER_AGENT=Newsauto/1.0

# Cache Settings
CACHE_DIR=./data/cache
CACHE_TTL_DAYS=7

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Frontend
FRONTEND_URL=http://localhost:3000
```

### Step 7: Initialize Database

```bash
# Create data directory
mkdir -p data/{cache,archives}

# Initialize database
python scripts/init_db.py

# Run migrations (if any)
python scripts/migrate.py
```

### Step 8: Verify Installation

```bash
# Run installation check
python scripts/check_installation.py
```

Expected output:
```
✅ Python version: 3.12.3
✅ CUDA available: True
✅ GPU detected: NVIDIA GeForce RTX 4070 Ti SUPER (16GB)
✅ Ollama running: True
✅ Models loaded: mistral:7b-instruct, deepseek-r1:7b, phi-3
✅ Database connected: True
✅ Email configured: True
✅ All checks passed! Ready to run Newsauto.
```

## Quick Start

### Running the Application

```bash
# Start the FastAPI server
python main.py

# Or use uvicorn directly
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Access Points

- **API Documentation**: http://localhost:8000/docs
- **Admin Dashboard**: http://localhost:8000/admin
- **Health Check**: http://localhost:8000/health

### First Newsletter

```bash
# Create your first newsletter via CLI
python scripts/create_newsletter.py \
    --name "Tech Weekly" \
    --niche "technology" \
    --frequency "weekly"

# Test content fetching
python scripts/fetch_content.py --source hackernews --limit 10

# Generate test newsletter
python scripts/generate_newsletter.py --newsletter-id 1 --test
```

## Platform-Specific Instructions

### Ubuntu/Debian

```bash
# Install system dependencies
sudo apt install -y python3-pip python3-dev python3-venv
sudo apt install -y postgresql postgresql-contrib  # If using PostgreSQL
sudo apt install -y redis-server  # If using Redis

# GPU support
sudo apt install -y nvidia-cuda-toolkit
```

### macOS

```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.12
brew install postgresql  # If using PostgreSQL
brew install redis  # If using Redis

# For GPU support (Apple Silicon)
pip install torch torchvision torchaudio
```

### Windows (WSL2)

```powershell
# Enable WSL2
wsl --install

# Install Ubuntu
wsl --install -d Ubuntu-22.04

# Open Ubuntu terminal and follow Linux instructions
```

### Docker Installation (Alternative)

```bash
# Build Docker image
docker build -t newsauto .

# Run with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f
```

## Optional Components

### PostgreSQL Setup (Production)

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE newsauto;
CREATE USER newsauto_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE newsauto TO newsauto_user;
\q

# Update .env
DATABASE_URL=postgresql://newsauto_user:secure_password@localhost/newsauto
```

### Redis Setup (Caching)

```bash
# Install Redis
sudo apt install redis-server

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis

# Test connection
redis-cli ping
```

### Nginx Setup (Production)

```bash
# Install Nginx
sudo apt install nginx

# Configure reverse proxy
sudo nano /etc/nginx/sites-available/newsauto

# Add configuration
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/newsauto /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Error
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
sudo systemctl restart ollama

# Check logs
journalctl -u ollama -f
```

#### 2. GPU Not Detected
```bash
# Check CUDA installation
nvidia-smi

# Reinstall CUDA drivers
sudo apt install nvidia-driver-530 nvidia-cuda-toolkit

# Verify PyTorch GPU support
python -c "import torch; print(torch.cuda.is_available())"
```

#### 3. Permission Errors
```bash
# Fix permissions
chmod +x scripts/*.py
chmod -R 755 data/

# Run with correct user
sudo chown -R $USER:$USER .
```

#### 4. Memory Issues
```bash
# Check available memory
free -h

# Reduce batch size in config
echo "BATCH_SIZE=1" >> .env

# Use smaller models
ollama pull phi-3  # Smaller model
```

#### 5. Port Already in Use
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>

# Or use different port
uvicorn api.main:app --port 8001
```

## Verification Tests

### Test Ollama Integration
```python
# test_ollama.py
import ollama

client = ollama.Client()
response = client.chat(
    model='mistral:7b-instruct',
    messages=[{
        'role': 'user',
        'content': 'Hello, can you summarize text?'
    }]
)
print(response['message']['content'])
```

### Test Database Connection
```python
# test_db.py
from sqlalchemy import create_engine

engine = create_engine('sqlite:///./data/newsletter.db')
conn = engine.connect()
print("Database connected successfully!")
conn.close()
```

### Test Email Sending
```python
# test_email.py
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Test email from Newsauto")
msg['Subject'] = 'Test'
msg['From'] = 'your-email@gmail.com'
msg['To'] = 'test@example.com'

# Send test email
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
server.send_message(msg)
server.quit()
print("Email sent successfully!")
```

## Next Steps

1. **Configure Content Sources**: Set up RSS feeds and API keys
2. **Create First Newsletter**: Use the admin dashboard
3. **Add Subscribers**: Import or manual addition
4. **Schedule Automation**: Set up cron jobs or GitHub Actions
5. **Monitor Performance**: Check logs and metrics

## Support

If you encounter issues:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review [GitHub Issues](https://github.com/yourusername/newsauto/issues)
3. Join our [Discord Community](https://discord.gg/newsauto)
4. Read the [FAQ](../faq.md)

## Uninstallation

To completely remove Newsauto:

```bash
# Stop services
sudo systemctl stop ollama
pkill -f "python.*newsauto"

# Remove Ollama
sudo rm /usr/local/bin/ollama
sudo rm /etc/systemd/system/ollama.service

# Remove project files
cd ..
rm -rf newsauto

# Remove Python virtual environment
rm -rf venv

# Remove data (careful!)
rm -rf ~/.ollama
rm -rf ~/newsauto-data
```