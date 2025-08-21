"""
Research Orchestration Logic

Streaming architecture with real-time event processing.
Uses async iterators and framework-native optimizations for enhanced performance.
"""

import time
import uuid
from datetime import datetime
from typing import Any

from strands.types.content import ContentBlock

from .agents import create_agent_manager
from .config import setup_logging
from .models import create_model
from .types import ResearchResults


def extract_content_text(c: ContentBlock) -> str:
    """Extract text content from a content block, handling reasoning content."""
    # Handle direct text content
    if "text" in c:
        return c["text"]
    # Handle reasoning content format
    elif "reasoningContent" in c:
        reasoning = c["reasoningContent"]
        if "reasoningText" in reasoning and "text" in reasoning["reasoningText"]:
            return reasoning["reasoningText"]["text"]
    return ""


class ResearchOrchestrator:
    """
    Streaming research orchestrator with real-time processing.
    Uses async iterators for performance optimization.
    """

    def __init__(self, progress_callback=None):
        # Create model instance for all agents
        self.model = create_model()

        # Create agent manager with callback support
        self.agent_manager = create_agent_manager(self.model, progress_callback)

        # Set up logging
        self.research_logger = setup_logging()

        # Streaming performance tracking
        self.performance_buffer: dict[str, Any] = {}

        # Progress callback for real-time updates
        self.progress_callback = progress_callback

    async def streaming_research_workflow(self, main_topic: str) -> ResearchResults:
        """
        Streaming workflow with real-time processing.
        Uses async iterators for enhanced performance.
        """
        workflow_id = str(uuid.uuid4())
        workflow_start = time.time()
        self.research_logger.info(
            f"🚀 [{workflow_id}] Starting STREAMING research workflow for: {main_topic}"
        )

        # Reset performance tracking state
        self.performance_buffer = {"partial_synthesis": ""}

        lead_researcher = self.agent_manager.get_lead_researcher()

        # Use simplified approach to avoid conversation state conflicts
        # Focus on streaming without complex coordination

        prompt = f"""As lead researcher, conduct a STREAMING research workflow for the topic: "{main_topic}"

STREAMING WORKFLOW:
1. Generate subtopics one by one (don't wait for all!)
2. Use research_specialist tool to get concurrent research reports
3. Start creating synthesis sections as research data becomes available
4. Build comprehensive master report progressively

Process everything in REAL-TIME - don't wait for completion before starting next steps!"""

        try:
            # Start streaming workflow!!
            streaming_start = time.time()
            self.research_logger.info(
                f"⚡ [{workflow_id}] Starting streaming delegation..."
            )

            # Use async iterator for real-time processing
            accumulated_text = ""
            tool_usage_count = 0
            performance_metrics: dict[str, Any] = {
                "tools": {},
                "tokens": {"input": 0, "output": 0},
                "timing": {},
            }

            async for event in lead_researcher.stream_async(prompt):
                self.research_logger.debug(f"📡 [{workflow_id}] Stream event: {event}")

                # Process text generation events
                if "data" in event:
                    text_chunk = event["data"]
                    accumulated_text += text_chunk
                    self.performance_buffer["partial_synthesis"] += text_chunk
                    # Track output tokens for performance metrics
                    performance_metrics["tokens"]["output"] += len(text_chunk.split())

                # Process tool usage events with performance tracking
                elif "current_tool_use" in event:
                    tool_info = event["current_tool_use"]
                    tool_name = tool_info.get("name", "unknown")
                    tool_usage_count += 1

                    # Track tool performance metrics
                    if tool_name not in performance_metrics["tools"]:
                        performance_metrics["tools"][tool_name] = {
                            "count": 0,
                            "start_time": time.time(),
                        }
                    performance_metrics["tools"][tool_name]["count"] += 1

                    self.research_logger.info(
                        f"🔧 [{workflow_id}] Tool execution #{tool_usage_count}: {tool_name} (usage #{performance_metrics['tools'][tool_name]['count']})"
                    )

                # Process lifecycle events for coordination
                elif "lifecycle" in event:
                    lifecycle_info = event["lifecycle"]
                    self.research_logger.info(
                        f"📈 [{workflow_id}] Lifecycle event: {lifecycle_info}"
                    )

            streaming_end = time.time()
            streaming_time = streaming_end - streaming_start
            performance_metrics["timing"]["streaming_duration"] = streaming_time

            # Log performance metrics
            self.research_logger.info(
                f"⚡ [{workflow_id}] Streaming completed in {streaming_time:.2f} seconds"
            )
            self.research_logger.info(
                f"📊 [{workflow_id}] Performance metrics: {tool_usage_count} tools used, "
                f"{performance_metrics['tokens']['output']} output tokens generated"
            )

            # Log individual tool performance
            for tool_name, tool_stats in performance_metrics["tools"].items():
                self.research_logger.info(
                    f"🔧 [{workflow_id}] Tool '{tool_name}': {tool_stats['count']} executions"
                )

            # Create performance summary for the report
            perf_summary = f"Tools used: {tool_usage_count} | Output tokens: {performance_metrics['tokens']['output']} | "
            perf_summary += f"Streaming duration: {streaming_time:.2f}s"

            final_report = ResearchResults(
                main_topic=main_topic,
                subtopics_count=0,  # Handled via streaming
                subtopic_research=[],  # Handled via streaming
                master_synthesis=accumulated_text
                or self.performance_buffer["partial_synthesis"],
                summary=f"Streaming research conducted on '{main_topic}' with real-time processing | {perf_summary}",
                generated_at=datetime.now().isoformat(),
            )

            workflow_end = time.time()
            total_time = workflow_end - workflow_start

            self.research_logger.info(
                f"🎯 [{workflow_id}] STREAMING workflow completed for '{main_topic}' in {total_time:.2f} seconds total"
            )

            return final_report

        except Exception as e:
            workflow_end = time.time()
            total_time = workflow_end - workflow_start
            self.research_logger.error(
                f"❌ [{workflow_id}] Streaming workflow failed for '{main_topic}' after {total_time:.2f} seconds: {e}"
            )
            raise RuntimeError(
                f"Streaming research workflow failed for topic '{main_topic}': {str(e)}"
            ) from e

    async def complete_research_workflow(self, main_topic: str) -> ResearchResults:
        """
        Delegates the complete research workflow to the lead researcher.
        """
        workflow_id = str(uuid.uuid4())
        workflow_start = time.time()
        self.research_logger.info(
            f"🕐 [{workflow_id}] Starting complete research workflow for: {main_topic}"
        )

        lead_researcher = self.agent_manager.get_lead_researcher()

        prompt = f"""As lead researcher, conduct a complete research workflow for the topic: "{main_topic}"

COMPLETE WORKFLOW:
1. Generate 2-5 focused subtopics for comprehensive coverage
2. Use research_specialist tool with ALL subtopics to get concurrent research reports
3. Create a comprehensive master synthesis report combining all findings
4. Include proper citations, structure, and formatting

Return ONLY the final master synthesis report as your complete response. No JSON, no metadata, just the comprehensive research report that synthesizes all your findings."""

        try:
            delegation_start = time.time()
            self.research_logger.info(
                f"⏱️ [{workflow_id}] Delegating to lead researcher..."
            )

            response = lead_researcher(prompt)

            delegation_end = time.time()
            delegation_time = delegation_end - delegation_start
            self.research_logger.info(
                f"✅ [{workflow_id}] Lead researcher completed in {delegation_time:.2f} seconds"
            )

            processing_start = time.time()
            self.research_logger.info(f"🔄 [{workflow_id}] Processing response...")

            master_synthesis = "".join(
                map(extract_content_text, response.message["content"])
            )

            final_report = ResearchResults(
                main_topic=main_topic,
                subtopics_count=0,
                subtopic_research=[],
                master_synthesis=master_synthesis,
                summary=f"Comprehensive research conducted on '{main_topic}' via delegation to lead researcher.",
                generated_at=datetime.now().isoformat(),
            )

            processing_end = time.time()
            processing_time = processing_end - processing_start
            workflow_end = time.time()
            total_time = workflow_end - workflow_start

            self.research_logger.info(
                f"⚡ [{workflow_id}] Response processing completed in {processing_time:.2f} seconds"
            )
            self.research_logger.info(
                f"🎯 [{workflow_id}] Complete research workflow finished for '{main_topic}' in {total_time:.2f} seconds total"
            )

            return final_report

        except Exception as e:
            workflow_end = time.time()
            total_time = workflow_end - workflow_start
            self.research_logger.error(
                f"❌ [{workflow_id}] Complete workflow delegation failed for '{main_topic}' after {total_time:.2f} seconds: {e}"
            )
            raise RuntimeError(
                f"Research workflow failed for topic '{main_topic}': {str(e)}"
            ) from e

    async def conduct_research(self, main_topic: str) -> ResearchResults:
        """
        Research orchestration with stable blocking calls to avoid ValidationExceptions.
        """
        self.research_logger.info(
            f"🚀 Starting research orchestration for: {main_topic}"
        )
        self.research_logger.info("⚡ Using stable architecture with hybrid model pool")

        # Use stable workflow to avoid ValidationExceptions
        final_report = await self.complete_research_workflow(main_topic)

        self.research_logger.info("✨ Research workflow completed")
        return final_report
