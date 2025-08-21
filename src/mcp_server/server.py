"""
Research MCP Server Implementation

Provides MCP tools for comprehensive research orchestration using multi-agent systems.
"""

import asyncio
import sys
import threading
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Redirect print statements to stderr to avoid breaking MCP JSON protocol
import builtins

original_print = builtins.print


def mcp_safe_print(*args, **kwargs):
    kwargs["file"] = kwargs.get("file", sys.stderr)
    original_print(*args, **kwargs)


builtins.print = mcp_safe_print

from research_orchestrator import ResearchOrchestrator  # type: ignore  # noqa: E402

# Create the FastMCP server instance
mcp = FastMCP("Deep Research")

# Note: No global orchestrator - each job gets fresh instance to avoid state contamination

# Job storage system
_research_jobs: dict[str, dict[str, Any]] = {}

# Global progress tracking
_progress_callbacks: dict[str, Callable] = {}


class JobStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


def create_orchestrator(progress_callback=None) -> ResearchOrchestrator:
    """Create a fresh research orchestrator instance for each job."""
    # Each job gets its own orchestrator to avoid state contamination
    return ResearchOrchestrator(progress_callback)


def create_job(topic: str) -> str:
    """Create a new research job and return job ID."""
    job_id = str(uuid.uuid4())
    _research_jobs[job_id] = {
        "id": job_id,
        "topic": topic,
        "status": JobStatus.PENDING,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
        "progress": {
            "subtopics_total": 0,
            "subtopics_completed": 0,
            "current_subtopic": None,
            "estimated_remaining": None,
        },
    }
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    """Get job by ID."""
    return _research_jobs.get(job_id)


def update_job_status(job_id: str, status: str, **kwargs) -> None:
    """Update job status and other fields."""
    if job_id in _research_jobs:
        _research_jobs[job_id]["status"] = status
        if (
            status == JobStatus.IN_PROGRESS
            and "started_at" not in _research_jobs[job_id]
        ):
            _research_jobs[job_id]["started_at"] = datetime.now().isoformat()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            _research_jobs[job_id]["completed_at"] = datetime.now().isoformat()

        # Update any additional fields
        for key, value in kwargs.items():
            _research_jobs[job_id][key] = value


def register_progress_callback(job_id: str, callback: Callable) -> None:
    """Register progress callback for a job."""
    _progress_callbacks[job_id] = callback


def update_job_progress(
    job_id: str,
    subtopics_total: int,
    subtopics_completed: int,
    current_subtopic: str | None = None,
) -> None:
    """Update job progress information."""
    if job_id in _research_jobs:
        progress = _research_jobs[job_id]["progress"]
        progress["subtopics_total"] = subtopics_total
        progress["subtopics_completed"] = subtopics_completed
        if current_subtopic:
            progress["current_subtopic"] = current_subtopic

        # Calculate estimated remaining time
        if subtopics_total > 0 and subtopics_completed > 0:
            started_at = _research_jobs[job_id].get("started_at")
            if started_at:
                elapsed_seconds = (
                    datetime.now() - datetime.fromisoformat(started_at)
                ).total_seconds()
                avg_time_per_subtopic = elapsed_seconds / subtopics_completed
                remaining_subtopics = subtopics_total - subtopics_completed
                estimated_remaining = int(avg_time_per_subtopic * remaining_subtopics)
                progress["estimated_remaining"] = (
                    f"{estimated_remaining // 60}m {estimated_remaining % 60}s"
                )


def execute_research_job_sync(job_id: str, topic: str) -> None:
    """Execute research job in background thread (synchronous wrapper)."""
    try:
        update_job_status(job_id, JobStatus.IN_PROGRESS)

        # Create real progress callback
        def progress_callback(event_type: str, **kwargs):
            if event_type == "research_started":
                total_count = kwargs.get("total_count", 5)
                update_job_progress(
                    job_id, total_count, 0, "Starting research on subtopics..."
                )
            elif event_type == "subtopic_completed":
                subtopic = kwargs.get("subtopic", "Unknown")
                completed_count = kwargs.get("completed_count", 0)
                # Get the total from current job state
                current_total = _research_jobs[job_id]["progress"]["subtopics_total"]
                update_job_progress(
                    job_id, current_total, completed_count, f"Completed: {subtopic}"
                )
            elif event_type == "research_completed":
                update_job_progress(
                    job_id,
                    _research_jobs[job_id]["progress"]["subtopics_total"],
                    _research_jobs[job_id]["progress"]["subtopics_total"],
                    "Synthesizing final report...",
                )

        orchestrator = create_orchestrator(
            progress_callback
        )  # Fresh instance with real progress!

        # Run the async orchestrator in a new event loop (thread-safe)
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Conduct full research orchestration
            results = loop.run_until_complete(orchestrator.conduct_research(topic))

            # Update job with results (store the full results object for source tracking)
            update_job_status(
                job_id,
                JobStatus.COMPLETED,
                result=results["master_synthesis"],
                full_results=results,
            )

            # Schedule cleanup after 1 hour
            cleanup_timer = threading.Timer(3600, lambda: cleanup_job_sync(job_id))
            cleanup_timer.daemon = True
            cleanup_timer.start()

        finally:
            loop.close()

    except Exception as e:
        update_job_status(job_id, JobStatus.FAILED, error=str(e))
        # Schedule cleanup for failed jobs after 10 minutes
        cleanup_timer = threading.Timer(600, lambda: cleanup_job_sync(job_id))
        cleanup_timer.daemon = True
        cleanup_timer.start()


# Removed fake progress simulation - now using real progress callbacks!


def cleanup_job_sync(job_id: str) -> None:
    """Clean up job synchronously."""
    if job_id in _research_jobs:
        del _research_jobs[job_id]


def cleanup_old_jobs() -> int:
    """Clean up jobs older than 24 hours. Returns number of jobs cleaned."""
    cutoff_time = datetime.now() - timedelta(hours=24)
    jobs_to_remove = []

    for job_id, job in _research_jobs.items():
        created_at = datetime.fromisoformat(job["created_at"])
        if created_at < cutoff_time:
            jobs_to_remove.append(job_id)

    for job_id in jobs_to_remove:
        del _research_jobs[job_id]

    return len(jobs_to_remove)


@mcp.tool()
async def create_research_report(topic: str) -> str:
    """
    <tool_description>
    Start asynchronous comprehensive multi-agent research on a given topic.

    This tool creates a background research job that:
    - Breaks down the topic into focused subtopics
    - Conducts parallel web search and analysis
    - Generates detailed reports with proper citations
    - Creates a master synthesis combining all findings
    </tool_description>

    <tool_usage_guidelines>
    Use this tool for comprehensive guides, mastery-level explanations, or when someone asks for 'research' on complex topics!
    Perfect for any subject where you'd need multiple sources to give a truly complete answer - whether it's academic research, hobby deep-dives, professional strategies, or detailed how-to guides.

    This tool returns immediately with a job ID. Use get_research_report(job_id) to check status and retrieve results.
    Research jobs typically take 3-5 minutes to complete for complex topics.

    Also use this tool for ANY comprehensive guides, strategy guides, or 'tell me everything about X' requests, even for topics like gaming, hobbies, or specialized interests.
    Gaming strategies, meta analysis, or evolving systems especially benefit from current research.

    DO NOT use this tool for lifestyle advice, creative writing, or other opinion-based responses.

    However, this tool is also expensive, so you MUST ASK the user for confirmation before running it.
    </tool_usage_guidelines>

    Args:
        topic: The research topic to investigate comprehensively. Format this as a single,
        focused question or statement (e.g., "Impact of AI on Healthcare"). The research
        agent will break it down into subtopics and conduct detailed research.

    Returns:
        Job ID and instructions for polling the research status
    """
    try:
        # Create job and start background execution
        job_id = create_job(topic)

        # Start background research in separate thread (truly detached!)
        research_thread = threading.Thread(
            target=execute_research_job_sync, args=(job_id, topic), daemon=True
        )
        research_thread.start()

        return f"""Research job started successfully! 🚀

Job ID: {job_id}
Topic: {topic}

Your research is now running in the background. This typically takes 3-5 minutes to complete.

Recommended workflow:
1. Wait for research to start: wait_for_research_report(60)
2. Check status: get_research_report("{job_id}")
3. If still in progress, repeat: wait_for_research_report(30) then get_research_report("{job_id}")

The research will continue running even if you don't poll immediately.

Next step: Call wait_for_research_report(60) to wait for research to begin, then check status."""

    except Exception as e:
        return f"Error starting research job: {str(e)}"


@mcp.tool()
async def get_research_report(job_id: str) -> str:
    """
    <tool_description>
    Check status of research job and retrieve results when complete.

    Returns job status and research results. If job is still running,
    continue polling this function until status is 'completed' or 'failed'.
    </tool_description>

    <tool_usage_guidelines>
    Use this tool to:
    - Check the progress of a research job created with create_research_report
    - Retrieve completed research reports
    - Monitor job status and estimated completion time

    Keep calling this tool with the same job_id until you receive a 'completed' status.
    Typical research jobs take 3-5 minutes to complete.
    </tool_usage_guidelines>

    <output_formatting_requirements>
    When research is complete, follow these guidelines for presenting results:

    MAIN RESPONSE FORMATTING:
    - Even when creating artifacts, the main conversational response should follow prose formatting guidelines.
    - Avoid bullet points, numbered lists, or excessive formatting in explanatory text.
    - Use natural language flow: "The key elements include: A, B, and C" rather than bulleted lists.

    CITATION REQUIREMENTS:
    - Use linked inline reference numbers in Markdown format [[1](link)], [[2](link)], etc. and ensure the references list from the research report is included at the end of your response
    - ALWAYS preserve source attribution regardless of citation method available

    CRITICAL: CITATION REQUIREMENTS (HIGH PRIORITY)
    - MUST cite all factual claims from research
    - Use factual claim for every specific detail, strategy, or data point
    - This is mandatory, not optional - factual claims without citations undermine research credibility
    - No exceptions - if you reference research findings, cite them immediately
    - Use specific index numbers from the research report
    - Failure to cite = academic integrity violation

    CONTENT FORMATTING:
    - IF you have artifact creation capabilities AND the research produces substantial structured content (guides, reports, reference materials): Create an appropriate artifact containing the complete information
    - IF you do NOT have artifact capabilities: Format the content clearly in your response using proper markdown structure with headers, sections, and lists
    - ALWAYS prioritize making the information easily scannable and referenceable

    FALLBACK BEHAVIOR:
    - When specific formatting tools are unavailable, compensate with clear structure, proper headings, and explicit source attribution
    - Ensure information remains credible and verifiable regardless of presentation format
    - Include complete reference list at the end of response when citation markup is unavailable
    </output_formatting_requirements>

    Args:
        job_id: The job ID returned by create_research_report

    Returns:
        Job status and research results (when complete) or progress information
    """
    try:
        job = get_job(job_id)

        if not job:
            return (
                f"Job ID '{job_id}' not found. Please check the job ID and try again."
            )

        status = job["status"]
        topic = job["topic"]
        created_at = job["created_at"]

        if status == JobStatus.PENDING:
            return f"""Research Job Status: PENDING ⏳

Job ID: {job_id}
Topic: {topic}
Created: {created_at}

Your research job is queued and will start shortly.

Next step: Call wait_for_research_report(30) to wait, then get_research_report("{job_id}") to check status."""

        elif status == JobStatus.IN_PROGRESS:
            started_at = job.get("started_at", "Unknown")
            progress = job.get("progress", {})

            # Build progress display
            progress_info = ""
            subtopics_total = progress.get("subtopics_total", 0)
            subtopics_completed = progress.get("subtopics_completed", 0)
            current_subtopic = progress.get("current_subtopic")
            estimated_remaining = progress.get("estimated_remaining")

            if subtopics_total > 0:
                percentage = int((subtopics_completed / subtopics_total) * 100)
                progress_bar = "█" * (percentage // 10) + "░" * (
                    10 - (percentage // 10)
                )
                progress_info = f"""
Progress: [{progress_bar}] {percentage}% ({subtopics_completed}/{subtopics_total} subtopics)"""

                if current_subtopic:
                    progress_info += f"\nCurrent: {current_subtopic}"

                if estimated_remaining:
                    progress_info += f"\nEstimated remaining: {estimated_remaining}"

            return f"""Research Job Status: IN PROGRESS 🔬

Job ID: {job_id}
Topic: {topic}
Started: {started_at}{progress_info}

Research is actively running with multiple agents conducting comprehensive analysis.
This typically takes 3-5 minutes for complex topics.

Next step: Call wait_for_research_report(30) to wait, then get_research_report("{job_id}") to check progress again."""

        elif status == JobStatus.COMPLETED:
            completed_at = job.get("completed_at", "Unknown")
            result = job.get("result", "No result available")

            # Get source statistics from full results if available
            full_results = job.get("full_results", {})
            source_count = full_results.get("total_unique_sources", 0)
            source_info = ""
            if source_count > 0:
                source_info = f"📊 Research consulted {source_count} unique sources\n\n"

            return f"""Research Job Status: COMPLETED ✅

Job ID: {job_id}
Topic: {topic}
Completed: {completed_at}
{source_info}Here is your comprehensive research report:

{result}"""

        elif status == JobStatus.FAILED:
            completed_at = job.get("completed_at", "Unknown")
            error = job.get("error", "Unknown error")

            return f"""Research Job Status: FAILED ❌

Job ID: {job_id}
Topic: {topic}
Failed: {completed_at}
Error: {error}

The research job encountered an error. You can try creating a new research job with create_research_report if needed."""

        else:
            return f"Unknown job status: {status}"

    except Exception as e:
        return f"Error retrieving job status: {str(e)}"


# Dummy waiting tool for agents without backgrounding to call so they
# think they're doing something useful while research runs in background
@mcp.tool()
async def wait_for_research_report(seconds: int = 30) -> str:
    """
    <tool_description>
    Wait for a specified number of seconds, then prompt to check research status again.

    This tool provides a concrete "waiting" action for agents to use
    while research jobs are running in the background.
    </tool_description>

    <tool_usage_guidelines>
    Use this tool when:
    - A research job is IN PROGRESS and you need to wait before checking again
    - You want to pause before calling get_research_report again
    - You need a structured way to wait for background research to complete

    Typical usage pattern:
    1. create_research_report("topic") → get job_id
    2. wait_for_research_report(30) → wait 30 seconds
    3. get_research_report("job_id") → check status
    4. If still in progress, repeat steps 2-3

    Recommended wait times:
    - First check: 30-60 seconds (research is just starting)
    - Subsequent checks: 30-45 seconds (research in progress)
    - Near completion: 15-30 seconds (final synthesis)
    </tool_usage_guidelines>

    Args:
        seconds: Number of seconds to wait (default: 30, max: 120 for reasonableness)

    Returns:
        Message indicating wait is complete and next action to take
    """

    # Clamp seconds to reasonable range
    wait_seconds = max(5, min(seconds, 120))

    try:
        # Actually wait the specified time
        await asyncio.sleep(wait_seconds)

        return f"""⏳ Wait Complete!

Waited {wait_seconds} seconds as requested.

Next step: Call get_research_report("your_job_id") to check the current status of your research job.

If the research is still in progress, you can call wait_for_research_report() again to wait before the next status check."""

    except Exception as e:
        return f"Error during wait: {str(e)}"


@mcp.tool()
async def list_research_jobs() -> str:
    """
    <tool_description>
    List all active research jobs with their current status.

    Useful for debugging and managing research jobs.
    </tool_description>

    <tool_usage_guidelines>
    Use this tool to:
    - See all currently active research jobs
    - Debug job status issues
    - Clean up or check on running research
    </tool_usage_guidelines>

    Returns:
        List of all research jobs with their status and basic information
    """
    try:
        if not _research_jobs:
            return "No active research jobs found."

        # Clean up old jobs first
        cleaned = cleanup_old_jobs()

        job_list = []
        for job_id, job in _research_jobs.items():
            status = job["status"]
            topic = (
                job["topic"][:50] + "..." if len(job["topic"]) > 50 else job["topic"]
            )
            created = job["created_at"][:19]  # Remove milliseconds

            status_emoji = {
                JobStatus.PENDING: "⏳",
                JobStatus.IN_PROGRESS: "🔬",
                JobStatus.COMPLETED: "✅",
                JobStatus.FAILED: "❌",
            }.get(status, "❓")

            job_list.append(
                f"{status_emoji} {job_id[:8]}... | {status.upper()} | {topic} | Created: {created}"
            )

        result = "Research Jobs:\n\n" + "\n".join(job_list)

        if cleaned > 0:
            result += f"\n\n(Cleaned up {cleaned} old jobs)"

        return result

    except Exception as e:
        return f"Error listing jobs: {str(e)}"


if __name__ == "__main__":
    mcp.run()
