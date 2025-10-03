# Multi-stage build for Newsauto
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r newsauto && useradd -r -g newsauto newsauto

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/newsauto/.local

# Copy application code
COPY --chown=newsauto:newsauto . .

# Set Python path
ENV PATH=/home/newsauto/.local/bin:$PATH
ENV PYTHONPATH=/app

# Create data directories
RUN mkdir -p /app/data /app/logs && \
    chown -R newsauto:newsauto /app/data /app/logs

# Switch to non-root user
USER newsauto

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command
CMD ["python", "main.py"]