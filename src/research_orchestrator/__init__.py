"""
Research Orchestrator Package

A sophisticated multi-agent research orchestration system built on the Strands Agents framework.
Provides hierarchical research coordination with lead researchers and specialized subagents.
"""

from .orchestrator import ResearchOrchestrator
from .config import get_model, setup_logging

__version__ = "1.0.0"
__all__ = ["ResearchOrchestrator", "get_model", "setup_logging"]
