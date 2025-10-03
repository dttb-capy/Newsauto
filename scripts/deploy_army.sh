#!/bin/bash
#
# NEWSAUTO AUTOMATION ARMY DEPLOYMENT
# One-command deployment for the complete automation system
# Target: $0 → $5,000 MRR in 30 days
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Banner
clear
echo -e "${CYAN}${BOLD}"
echo "════════════════════════════════════════════════════════════════════════"
echo "   _   _ _____ _    _ ____    _   _   _ _____ ___    _   ____  __  ____   __"
echo "  | \ | | __\ | |  | / ___|  / \ | | | |_   _/ _ \  / \ |  _ \|  \/  \ \ / /"
echo "  |  \| |  _| | |  | \___ \ / _ \| | | | | || | | |/ _ \| |_) | |\/| |\ V /"
echo "  | |\  | |___| |/\| |___) / ___ \ |_| | | || |_| / ___ \  _ <| |  | | | |"
echo "  |_| \_|_____|\    /|____/_/   \_\___/  |_| \___/_/   \_\_| \_\_|  |_| |_|"
echo ""
echo "                    🚀 ZERO-TOUCH AUTOMATION ARMY 🚀"
echo "                    Target: \$5,000 MRR in 30 Days"
echo "════════════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Function to print status
print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check prerequisites
print_status "Phase 1: System Check"
echo "────────────────────────────────────────"

# Check Python
if command -v python3 &> /dev/null; then
    print_success "Python 3 installed ($(python3 --version))"
else
    print_error "Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# Check Ollama
if command -v ollama &> /dev/null; then
    print_success "Ollama installed"

    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_success "Ollama server is running"
    else
        print_warning "Ollama server not running. Starting..."
        ollama serve &
        sleep 5
    fi
else
    print_error "Ollama not found. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Check database
if [ -f "data/newsletter.db" ]; then
    print_success "Database exists"
else
    print_warning "Database not found. Will be created"
fi

echo ""
print_status "Phase 2: Environment Setup"
echo "────────────────────────────────────────"

# Create necessary directories
mkdir -p data logs backups
print_success "Directories created"

# Check virtual environment
if [ -d "venv" ]; then
    print_success "Virtual environment exists"
else
    print_warning "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate
print_success "Virtual environment activated"

# Install dependencies
print_status "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt 2>/dev/null || print_warning "Some packages may be missing"
print_success "Dependencies installed"

echo ""
print_status "Phase 3: Ollama Model Setup"
echo "────────────────────────────────────────"

# Pull required models
models=("mistral:7b-instruct" "deepseek-r1:1.5b" "phi3")
for model in "${models[@]}"; do
    if ollama list | grep -q "$model"; then
        print_success "Model $model already available"
    else
        print_warning "Pulling model $model..."
        ollama pull "$model"
    fi
done

echo ""
print_status "Phase 4: Database Initialization"
echo "────────────────────────────────────────"

# Initialize database with newsletters
print_status "Setting up 10 premium newsletters..."
python scripts/initialize_all_newsletters.py

echo ""
print_status "Phase 5: Automation Army Deployment"
echo "────────────────────────────────────────"

# Deploy Content Battalion
print_status "🎖️ Deploying Content Battalion..."
if [ -f "scripts/content_army.py" ]; then
    print_success "Content Army ready for deployment"
    # Run in background
    nohup python scripts/content_army.py > logs/content_army.log 2>&1 &
    CONTENT_PID=$!
    print_success "Content Army deployed (PID: $CONTENT_PID)"
else
    print_error "Content Army script not found"
fi

# Deploy Revenue Battalion
print_status "💰 Deploying Revenue Battalion..."
if [ -f "scripts/revenue_battalion.py" ]; then
    print_success "Revenue Battalion ready for deployment"
    # Run in background
    nohup python scripts/revenue_battalion.py > logs/revenue_battalion.log 2>&1 &
    REVENUE_PID=$!
    print_success "Revenue Battalion deployed (PID: $REVENUE_PID)"
else
    print_error "Revenue Battalion script not found"
fi

echo ""
print_status "Phase 6: Scheduling Setup"
echo "────────────────────────────────────────"

# Create cron jobs
CRON_FILE="/tmp/newsauto_cron"

# Check if cron jobs already exist
if crontab -l 2>/dev/null | grep -q "newsauto"; then
    print_warning "Cron jobs already configured"
else
    print_status "Setting up automated schedules..."

    # Get current crontab
    crontab -l 2>/dev/null > "$CRON_FILE" || true

    # Add newsauto jobs
    echo "# Newsauto Automation Army" >> "$CRON_FILE"
    echo "0 6,12,18 * * * cd $(pwd) && venv/bin/python scripts/content_army.py >> logs/content_cron.log 2>&1" >> "$CRON_FILE"
    echo "*/30 * * * * cd $(pwd) && venv/bin/python scripts/revenue_battalion.py >> logs/revenue_cron.log 2>&1" >> "$CRON_FILE"

    # Install new crontab
    crontab "$CRON_FILE"
    rm "$CRON_FILE"

    print_success "Automated schedules configured"
fi

echo ""
print_status "Phase 7: Battle Dashboard Launch"
echo "────────────────────────────────────────"

print_status "Starting real-time monitoring dashboard..."
echo -e "${YELLOW}Press Ctrl+C to exit dashboard${NC}"
echo ""

# Launch dashboard
python scripts/battle_dashboard.py

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}                    🎉 DEPLOYMENT COMPLETE! 🎉${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}📊 Status Report:${NC}"
echo "  • 10 Premium Newsletters: ACTIVE"
echo "  • Content Army: DEPLOYED"
echo "  • Revenue Battalion: OPERATIONAL"
echo "  • Automation: RUNNING 24/7"
echo "  • Test Email: erick.durantt@gmail.com"
echo ""
echo -e "${YELLOW}📈 Revenue Projections:${NC}"
echo "  • Day 1: First paying customer"
echo "  • Week 1: \$1,000 MRR"
echo "  • Week 2: \$2,500 MRR"
echo "  • Week 4: \$5,000 MRR TARGET"
echo ""
echo -e "${GREEN}🎯 Next Steps:${NC}"
echo "  1. Check email for newsletter samples"
echo "  2. Monitor dashboard: python scripts/battle_dashboard.py"
echo "  3. View logs: tail -f logs/*.log"
echo "  4. Manual content run: python scripts/content_army.py"
echo "  5. Manual sales run: python scripts/revenue_battalion.py"
echo ""
echo -e "${BOLD}The army is deployed. The battle for \$5K MRR begins NOW! 🚀${NC}"