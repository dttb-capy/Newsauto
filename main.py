#!/usr/bin/env python3
"""Main entry point for Newsauto application."""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from newsauto.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Run the application."""
    settings = get_settings()

    logger.info(f"Starting Newsauto v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API URL: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"Docs URL: http://{settings.api_host}:{settings.api_port}/docs")

    # Run the FastAPI app
    uvicorn.run(
        "newsauto.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload or settings.debug,
        workers=1 if settings.debug else settings.api_workers,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)