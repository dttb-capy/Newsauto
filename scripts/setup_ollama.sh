#!/bin/bash

# Ollama Setup Script
# Installs Ollama and pulls required models

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🤖 Setting up Ollama for Newsauto${NC}"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Installing Ollama...${NC}"

    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Please download Ollama from https://ollama.com/download/mac"
        exit 1
    else
        echo -e "${RED}Unsupported OS: $OSTYPE${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Ollama installed${NC}"
else
    echo -e "${GREEN}✓ Ollama already installed$(NC)"
fi

# Start Ollama service
echo -e "${YELLOW}Starting Ollama service...${NC}"
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to start
sleep 5

# Function to pull model with progress
pull_model() {
    local model=$1
    echo -e "${YELLOW}Pulling model: $model${NC}"

    if ollama list | grep -q "$model"; then
        echo -e "${GREEN}  ✓ $model already available${NC}"
    else
        ollama pull "$model"
        echo -e "${GREEN}  ✓ $model pulled successfully${NC}"
    fi
}

# Pull required models
echo -e "${YELLOW}Pulling required models...${NC}"

# Primary models
pull_model "mistral:7b-instruct"
pull_model "deepseek-r1:1.5b"

# Optional models (uncomment if needed)
# pull_model "llama3.2:3b"
# pull_model "phi3:mini"
# pull_model "qwen2.5:7b"

echo -e "${GREEN}✅ All models ready!${NC}"

# Show available models
echo -e "${YELLOW}Available models:${NC}"
ollama list

# Test model
echo -e "${YELLOW}Testing Mistral model...${NC}"
echo "Hello, can you respond?" | ollama run mistral:7b-instruct --verbose 2>/dev/null | head -5

echo -e "${GREEN}✅ Ollama setup complete!${NC}"
echo -e "${YELLOW}Ollama is running on http://localhost:11434${NC}"
echo -e "${YELLOW}To stop Ollama, run: pkill ollama${NC}"

# Keep Ollama running if this is the main process
if [ "$1" == "serve" ]; then
    wait $OLLAMA_PID
fi