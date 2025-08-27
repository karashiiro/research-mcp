"""
Agents package for research orchestration.

This package contains individual agent implementations organized by type.
"""

from .agent_manager import AgentManager, create_agent_manager
from .lead_researcher import LeadResearcher
from .research_agent import ResearchAgent
from .reviewer_agent import ReviewerAgent
from .synthesis_agent import SynthesisAgent

__all__ = [
    "AgentManager",
    "create_agent_manager",
    "LeadResearcher",
    "ResearchAgent",
    "ReviewerAgent",
    "SynthesisAgent",
]
