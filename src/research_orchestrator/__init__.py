"""
Research Orchestrator Package

A sophisticated multi-agent research orchestration system built on the Strands Agents framework.
Provides hierarchical research coordination with lead researchers and specialized subagents.
"""

from research_orchestrator.logger import setup_logging
from research_orchestrator.orchestrator import ResearchOrchestrator

__version__ = "1.0.0"
__all__ = ["ResearchOrchestrator", "setup_logging"]
