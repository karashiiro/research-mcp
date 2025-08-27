"""
Research processing components.

This package contains focused components for processing research results,
managing citations, tracking sources, and formatting outputs.
"""

from .citation_processor import CitationProcessor
from .result_formatter import ResultFormatter
from .source_tracker import SourceTracker

__all__ = [
    "CitationProcessor",
    "ResultFormatter",
    "SourceTracker",
]
