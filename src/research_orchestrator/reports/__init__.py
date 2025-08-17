"""
Report Generation and Synthesis Package

Provides standardized report formatting and master synthesis capabilities.
"""

from .formatter import ReportFormatter
from .synthesis import create_master_synthesis

__all__ = ["ReportFormatter", "create_master_synthesis"]