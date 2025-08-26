"""
Logger Configuration Module

Handles logging setup for research operations.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from strands.telemetry import StrandsTelemetry

# Load environment variables from .env file
load_dotenv()

# Initialize Strands telemetry for logging
strands_telemetry = StrandsTelemetry()
if "OTEL_EXPORTER_OTLP_ENDPOINT" in os.environ:
    strands_telemetry.setup_otlp_exporter()


def create_logger():
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(parents=True, exist_ok=True)

    # Configure strands logger to write to file
    strands_logger = logging.getLogger("strands")
    strands_logger.setLevel(logging.DEBUG)

    # Create file handler for strands logs
    file_handler = logging.FileHandler("logs/strands_agents.log", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    strands_logger.addHandler(file_handler)

    # Create file handler for research results
    research_handler = logging.FileHandler(
        "logs/research_results.log", encoding="utf-8"
    )
    research_handler.setFormatter(logging.Formatter("%(message)s"))

    # Create research logger
    research_logger = logging.getLogger("research")
    research_logger.setLevel(logging.INFO)
    research_logger.addHandler(research_handler)

    return research_logger


research_logger: logging.Logger | None = None


def setup_logging():
    global research_logger
    if research_logger is None:
        research_logger = create_logger()
    return research_logger
