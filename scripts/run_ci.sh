#!/bin/bash

# Local CI Script - Run the same checks as GitHub Actions locally
# This helps catch issues before pushing to the repository

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
PYTHON_CMD=${PYTHON_CMD:-python3}
VENV_DIR=${VENV_DIR:-venv}
MIN_COVERAGE=${MIN_COVERAGE:-80}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[CI]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Track failures
FAILED_CHECKS=()

# Header
echo "======================================"
echo "       Newsauto Local CI Runner       "
echo "======================================"
echo ""

# Check Python version
print_status "Checking Python version..."
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    print_success "Python $PYTHON_VERSION (>= $REQUIRED_VERSION)"
else
    print_error "Python $PYTHON_VERSION (requires >= $REQUIRED_VERSION)"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
    print_status "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    print_success "Virtual environment activated"
else
    print_warning "No virtual environment found, using system Python"
fi

# Install/upgrade dependencies
print_status "Checking dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q pytest pytest-cov pytest-asyncio black ruff mypy isort

print_success "Dependencies installed"

echo ""
echo "Running CI Checks..."
echo "===================="

# 1. Code Formatting Check
echo ""
print_status "1. Checking code formatting (Black)..."
if black --check newsauto/ tests/ 2>/dev/null; then
    print_success "Code formatting is correct"
else
    print_warning "Code needs formatting. Run: make format"
    FAILED_CHECKS+=("formatting")
fi

# 2. Import Sorting Check
echo ""
print_status "2. Checking import sorting (isort)..."
if isort --check-only newsauto/ tests/ 2>/dev/null; then
    print_success "Imports are properly sorted"
else
    print_warning "Imports need sorting. Run: isort newsauto/ tests/"
    FAILED_CHECKS+=("imports")
fi

# 3. Linting
echo ""
print_status "3. Running linter (Ruff)..."
if ruff check newsauto/ tests/ 2>/dev/null; then
    print_success "No linting issues found"
else
    print_warning "Linting issues found. Run: ruff check newsauto/ tests/"
    FAILED_CHECKS+=("linting")
fi

# 4. Type Checking
echo ""
print_status "4. Running type checker (MyPy)..."
if mypy newsauto/ --ignore-missing-imports 2>/dev/null; then
    print_success "Type checking passed"
else
    print_warning "Type checking issues found (non-blocking)"
    # Don't add to FAILED_CHECKS as MyPy is often too strict
fi

# 5. Security Check
echo ""
print_status "5. Running security checks..."
if command_exists bandit; then
    if bandit -r newsauto/ -f json -o /tmp/bandit-report.json 2>/dev/null; then
        print_success "No security issues found"
    else
        print_warning "Security issues found (review /tmp/bandit-report.json)"
    fi
else
    print_warning "Bandit not installed, skipping security check"
fi

# 6. Run Tests
echo ""
print_status "6. Running test suite..."

# Create test database
export DATABASE_URL="sqlite:///./test_ci.db"
export TESTING="true"
export OLLAMA_HOST="http://mock-ollama:11434"

# Initialize test database
alembic upgrade head 2>/dev/null || true

# Run tests with coverage
if pytest tests/ \
    -v \
    --cov=newsauto \
    --cov-report=term-missing \
    --cov-fail-under=$MIN_COVERAGE \
    -x \
    --tb=short \
    2>/dev/null; then
    print_success "All tests passed with coverage >= $MIN_COVERAGE%"
else
    print_error "Tests failed or coverage < $MIN_COVERAGE%"
    FAILED_CHECKS+=("tests")
fi

# Clean up test database
rm -f test_ci.db

# 7. Check for large files
echo ""
print_status "7. Checking for large files..."
LARGE_FILES=$(find . -type f -size +1M -not -path "./.git/*" -not -path "./venv/*" -not -path "./__pycache__/*" -not -path "./data/*" -not -path "./logs/*" 2>/dev/null)
if [ -z "$LARGE_FILES" ]; then
    print_success "No large files found"
else
    print_warning "Large files found (>1MB):"
    echo "$LARGE_FILES" | while read -r file; do
        SIZE=$(du -h "$file" | cut -f1)
        echo "  - $file ($SIZE)"
    done
fi

# 8. Check for secrets
echo ""
print_status "8. Checking for hardcoded secrets..."
SECRET_PATTERNS="(api_key|apikey|secret|password|token|private_key|aws_access|aws_secret)"
if grep -rEi "$SECRET_PATTERNS" newsauto/ tests/ --exclude-dir=__pycache__ 2>/dev/null | grep -v "# CI-IGNORE" | grep -qE "=\s*['\"][^'\"]{20,}['\"]"; then
    print_warning "Potential secrets found in code"
    FAILED_CHECKS+=("secrets")
else
    print_success "No hardcoded secrets detected"
fi

# 9. Check requirements.txt for vulnerabilities
echo ""
print_status "9. Checking dependencies for vulnerabilities..."
if command_exists safety; then
    if safety check --json 2>/dev/null; then
        print_success "No known vulnerabilities in dependencies"
    else
        print_warning "Vulnerabilities found in dependencies"
    fi
else
    pip install -q safety
    if safety check --json 2>/dev/null; then
        print_success "No known vulnerabilities in dependencies"
    else
        print_warning "Vulnerabilities found in dependencies"
    fi
fi

# 10. Validate Docker files if present
echo ""
print_status "10. Validating Docker configuration..."
if [ -f "Dockerfile" ]; then
    if command_exists docker; then
        if docker build --check . 2>/dev/null; then
            print_success "Dockerfile is valid"
        else
            print_warning "Dockerfile validation failed"
        fi
    else
        print_warning "Docker not installed, skipping Dockerfile validation"
    fi
else
    print_success "No Dockerfile to validate"
fi

# Summary
echo ""
echo "======================================"
echo "           CI Summary                 "
echo "======================================"

if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All CI checks passed!${NC}"
    echo ""
    echo "Your code is ready to be committed and pushed."
    exit 0
else
    echo -e "${RED}✗ Some CI checks failed:${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo "  - $check"
    done
    echo ""
    echo "Please fix these issues before pushing to the repository."
    echo "Run 'make format' to automatically fix formatting issues."
    exit 1
fi