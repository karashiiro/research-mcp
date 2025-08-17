"""
Research Orchestration Logic

Main orchestrator that coordinates research workflow with lead researcher and subagents.
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List
from strands.types.content import ContentBlock

from .agents import create_agent_manager
from .config import setup_logging
from .models import create_model
from .search import web_search
from .reports import ReportFormatter
from .types import (
    SubtopicResearch,
    ResearchResults,
    CompatSearchResults,
    CompatSearchResultItem,
)


def extract_content_text(c: ContentBlock) -> str:
    """Extract text content from a content block."""
    return c.get("text", "")


class ResearchOrchestrator:
    """
    Lead researcher agent that orchestrates research by generating subtopics
    and delegating them to subagents for detailed investigation
    """

    def __init__(self):
        # Create model instance for all agents
        self.model = create_model()

        # Create agent manager
        self.agent_manager = create_agent_manager(self.model)

        # Set up logging
        self.research_logger = setup_logging()

    def generate_subtopics(self, main_topic: str) -> List[str]:
        """
        Use the lead researcher to break down a main topic into 2-5 subtopics
        """
        prompt = f"""
        As a lead researcher, break down the topic "{main_topic}" into 2-5 specific subtopics that would provide comprehensive coverage of the subject.
        
        Each subtopic should be:
        - Specific and focused
        - Researchable with web searches
        - Complementary to the other subtopics
        - Contributing to a complete understanding of the main topic
        
        Return ONLY a JSON list of subtopic strings, nothing else.
        Example format: ["Subtopic 1", "Subtopic 2", "Subtopic 3"]
        """

        lead_researcher = self.agent_manager.get_lead_researcher()
        response = lead_researcher(prompt)
        response_text = "".join(map(extract_content_text, response.message["content"]))

        # Extract JSON array from the response using regex
        json_pattern = r'\[(?:\s*"[^"]*"\s*,?\s*)+\]'
        json_matches = re.findall(json_pattern, response_text)

        if not json_matches:
            raise ValueError(
                f"No JSON array found in AI response for topic '{main_topic}'.\\n"
                f"Full response: {response_text}"
            )

        # Take the last JSON match (most likely to be the final answer)
        json_string = json_matches[-1]

        try:
            subtopics = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON array for topic '{main_topic}'.\\n"
                f"Extracted JSON: {json_string}\\n"
                f"JSON Error: {e}\\n"
                f"Full response: {response_text}"
            )

        # Validate the result
        if not isinstance(subtopics, list):
            raise ValueError(
                f"AI response was not a list for topic '{main_topic}'.\\n"
                f"Got: {type(subtopics).__name__}\\n"
                f"Value: {subtopics}\\n"
                f"Full response: {response_text}"
            )

        if not (2 <= len(subtopics) <= 5):
            raise ValueError(
                f"AI generated {len(subtopics)} subtopics for '{main_topic}', expected 2-5.\\n"
                f"Subtopics: {subtopics}\\n"
                f"Full response: {response_text}"
            )

        if not all(isinstance(item, str) for item in subtopics):
            raise ValueError(
                f"AI response contains non-string items for topic '{main_topic}'.\\n"
                f"Subtopics: {subtopics}\\n"
                f"Full response: {response_text}"
            )

        return subtopics

    async def research_subtopic(
        self, main_topic: str, subtopic: str, agent_id: int
    ) -> SubtopicResearch:
        """
        Use a subagent to research a specific subtopic with improved error handling
        """
        agent = self.agent_manager.get_subagent(agent_id)

        # Create contextual search query by combining main topic with subtopic
        contextual_query = f"{main_topic} {subtopic}"

        try:
            # Perform real web search with caching
            raw_search_data = await web_search(contextual_query, count=5)

            # Convert to expected format for compatibility
            search_results = CompatSearchResults(
                query=contextual_query,
                results=[
                    CompatSearchResultItem(
                        title=result.get("title", ""),
                        snippet=result.get("description", ""),
                        url=result.get("url", ""),
                    )
                    for result in raw_search_data.get("results", [])
                ],
                error=None,
            )

            # Log search success
            self.research_logger.info(
                f"Search completed for '{contextual_query}': {len(search_results['results'])} results found"
            )

        except Exception as e:
            # Handle search failures gracefully
            self.research_logger.error(f"Search failed for '{contextual_query}': {e}")
            search_results = CompatSearchResults(
                query=contextual_query, results=[], error=str(e)
            )

        try:
            # Create standardized research prompt with consistent formatting
            prompt = ReportFormatter.create_standard_prompt(subtopic, search_results)

            # Generate research summary
            research_summary = agent(prompt)

            # Log research completion
            self.research_logger.info(
                f"Research completed for '{subtopic}' by agent {agent_id}"
            )

        except Exception as e:
            # Handle AI generation failures
            self.research_logger.error(
                f"Research generation failed for '{subtopic}': {e}"
            )
            research_summary = {
                "message": {
                    "content": [{"text": f"Error generating research summary: {e}"}]
                }
            }

        return SubtopicResearch(
            subtopic=subtopic,
            agent_id=agent_id,
            search_results=search_results,
            research_summary=research_summary,
        )

    async def conduct_research(self, main_topic: str) -> ResearchResults:
        """
        Orchestrate the complete research process
        """
        print(f"🔬 Starting research orchestration for: {main_topic}")

        # Step 1: Generate subtopics
        print("📝 Generating subtopics...")
        subtopics = self.generate_subtopics(main_topic)
        print(f"✅ Generated {len(subtopics)} subtopics:")
        for i, subtopic in enumerate(subtopics, 1):
            print(f"   {i}. {subtopic}")

        # Step 2: Research each subtopic in parallel
        print("\\n🔍 Delegating research to subagents...")
        research_tasks = [
            self.research_subtopic(main_topic, subtopic, i)
            for i, subtopic in enumerate(subtopics)
        ]

        research_results = await asyncio.gather(*research_tasks)

        # Step 3: Create master synthesis report (imported from reports package)
        print("\\n📊 Creating master synthesis report...")
        from .reports.synthesis import create_master_synthesis

        master_synthesis = create_master_synthesis(
            main_topic, research_results, self.agent_manager.get_lead_researcher()
        )

        # Step 3.5: Add cross-references and table of contents
        print("🔗 Adding cross-references and table of contents...")
        master_synthesis = ReportFormatter.add_cross_references(
            master_synthesis, research_results
        )

        # Step 3.6: Add style guidelines
        master_synthesis = master_synthesis + "\n\n" + """## Style Guidelines
When using findings from this report (including deriving new reports from it):
- Carefully vet and maintain citations
- Ensure all factual claims are properly cited
- Use the provided references list for accurate source attribution
- Follow the formatting guidelines to ensure clarity and consistency
"""

        # Step 4: Compile final report
        print("✅ Compiling final research package...")
        final_report = ResearchResults(
            main_topic=main_topic,
            subtopics_count=len(subtopics),
            subtopic_research=research_results,
            master_synthesis=master_synthesis,
            summary=f"Comprehensive research conducted on '{main_topic}' across {len(subtopics)} specialized areas with master synthesis.",
            generated_at=datetime.now().isoformat(),
        )

        return final_report
