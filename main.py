import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from strands import Agent
from strands.telemetry import StrandsTelemetry
from strands.types.content import ContentBlock
from strands.models.bedrock import BedrockModel
from strands.models.model import Model
from strands.models.ollama import OllamaModel
from web_search import web_search
from report_formatter import ReportFormatter

# Load environment variables from .env file
load_dotenv()

# Initialize Strands telemetry for logging
strands_telemetry = StrandsTelemetry()
if "OTEL_EXPORTER_OTLP_ENDPOINT" in os.environ:
    strands_telemetry.setup_otlp_exporter()

# Configure strands logging to write to file instead of console
def setup_logging():
    """Configure strands logging to write to files."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure strands logger to write to file
    strands_logger = logging.getLogger("strands")
    strands_logger.setLevel(logging.DEBUG)
    
    # Create file handler for strands logs
    file_handler = logging.FileHandler("logs/strands_agents.log", encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    strands_logger.addHandler(file_handler)
    
    # Create file handler for research results
    research_handler = logging.FileHandler("logs/research_results.log", encoding='utf-8')
    research_handler.setFormatter(logging.Formatter("%(message)s"))
    
    # Create research logger
    research_logger = logging.getLogger("research")
    research_logger.setLevel(logging.INFO)
    research_logger.addHandler(research_handler)
    
    return research_logger

# Set up logging
research_logger = setup_logging()


def get_model():
    temperature = float(os.getenv("MODEL_TEMPERATURE", 0.0))
    if os.getenv("MODEL_TYPE") == "ollama":
        return OllamaModel(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            model_id=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
            temperature=temperature
        )
    else:
        return BedrockModel(
            model_id=os.getenv("BEDROCK_MODEL", "openai.gpt-oss-20b-1:0"),
            temperature=temperature,
            max_tokens=4000
        )


def extract_content_text(c: ContentBlock) -> str:
    return c.get("text", "")


class ResearchOrchestrator:
    """
    Lead researcher agent that orchestrates research by generating subtopics
    and delegating them to subagents for detailed investigation
    """

    model: Model
    lead_researcher: Agent
    subagents: List[Agent]

    def __init__(self):
        # Create model instance for all agents
        self.model = get_model()
        
        # Create the lead researcher agent with system prompt
        self.lead_researcher = Agent(
            model=self.model,
            system_prompt="You are a lead researcher who generates JSON lists of research subtopics. Be concise and direct. Avoid excessive reasoning.",
        )
        
        # Pool of subagents for research tasks with system prompts
        research_system_prompt = """You are a professional research agent. Your task is to:
- Produce research reports using ONLY the provided source material
- Be concise and factual - avoid excessive reasoning or internal thoughts
- Cite all claims with source numbers [1], [2], etc.
- Maintain consistent table formatting
- Keep executive summary brief
- Use markdown formatting exactly as shown
- Include source URLs where available
- Focus on extracting key information from sources"""
        
        self.subagents = []
        for _ in range(5):  # Create 5 subagents
            self.subagents.append(Agent(
                model=self.model,
                system_prompt=research_system_prompt,
            ))
    
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
        
        response = self.lead_researcher(prompt)
        response_text = "".join(map(extract_content_text, response.message["content"]))
        
        # Extract JSON array from the response using regex
        json_pattern = r'\[(?:\s*"[^"]*"\s*,?\s*)+\]'
        json_matches = re.findall(json_pattern, response_text)
        
        if not json_matches:
            raise ValueError(f"No JSON array found in AI response for topic '{main_topic}'.\n"
                           f"Full response: {response_text}")
        
        # Take the last JSON match (most likely to be the final answer)
        json_string = json_matches[-1]
        
        try:
            subtopics = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON array for topic '{main_topic}'.\n"
                           f"Extracted JSON: {json_string}\n"
                           f"JSON Error: {e}\n"
                           f"Full response: {response_text}")
        
        # Validate the result
        if not isinstance(subtopics, list):
            raise ValueError(f"AI response was not a list for topic '{main_topic}'.\n"
                           f"Got: {type(subtopics).__name__}\n"
                           f"Value: {subtopics}\n"
                           f"Full response: {response_text}")
        
        if not (2 <= len(subtopics) <= 5):
            raise ValueError(f"AI generated {len(subtopics)} subtopics for '{main_topic}', expected 2-5.\n"
                           f"Subtopics: {subtopics}\n"
                           f"Full response: {response_text}")
        
        if not all(isinstance(item, str) for item in subtopics):
            raise ValueError(f"AI response contains non-string items for topic '{main_topic}'.\n"
                           f"Subtopics: {subtopics}\n"
                           f"Full response: {response_text}")
        
        return subtopics
    
    def create_master_synthesis(self, main_topic: str, research_results: List[Dict[str, Any]]) -> str:
        """
        Create a master synthesis report combining all subtopic research
        """
        try:
            # Extract all research content
            research_summaries = []
            for result in research_results:
                # Handle both dict and object response formats
                research_summary = result['research_summary']
                if hasattr(research_summary, 'message'):
                    summary_text = "".join(map(extract_content_text, research_summary.message["content"]))
                else:
                    # Handle dict format
                    summary_text = "".join(map(extract_content_text, research_summary.get("message", {}).get("content", [])))
                
                research_summaries.append({
                    "subtopic": result["subtopic"],
                    "content": summary_text,
                    "sources": result.get("search_results", {}).get("results", [])
                })
            
            # Create synthesis prompt
            synthesis_prompt = f"""
            Create a comprehensive master synthesis report for: "{main_topic}"
            
            You have been provided with detailed research on {len(research_summaries)} subtopics.
            Your task is to synthesize these into a cohesive master report.
            
            SUBTOPIC RESEARCH:
            {chr(10).join([f"{'='*50}{chr(10)}SUBTOPIC: {r['subtopic']}{chr(10)}{'='*50}{chr(10)}{r['content']}{chr(10)}" for r in research_summaries])}
            
            Create a master synthesis using this structure:

            # Comprehensive Research Report: {main_topic}
            **Date:** {datetime.now().strftime('%Y-%m-%d')}

            ---

            ## Executive Summary
            [300-400 word synthesis of key findings across all subtopics]

            ---

            ## 1. Introduction & Background
            [Overview of {main_topic} and why it matters]

            ---

            ## 2. Key Findings by Research Area
            
            {chr(10).join([f"### 2.{i+1} {r['subtopic']}{chr(10)}- [Key insights from this area]{chr(10)}- [Important developments]{chr(10)}" for i, r in enumerate(research_summaries)])}

            ---

            ## 3. Cross-Cutting Themes & Patterns
            [Identify connections and patterns across all subtopic areas]

            ---

            ## 4. Current State of the Field
            [Synthesis of trends, developments, and current capabilities]

            ---

            ## 5. Future Directions & Implications
            [Combined implications, applications, and future outlook]

            ---

            ## 6. Conclusion
            [Overall synthesis and key takeaways about {main_topic}]

            ---

            ## 7. Comprehensive Bibliography
            [All sources from subtopic research, deduplicated and organized]

            SYNTHESIS REQUIREMENTS:
            - Draw meaningful connections between different research areas
            - Identify overarching themes and patterns
            - Avoid simple repetition of subtopic content
            - Focus on synthesis rather than summarization
            - Maintain consistent citation format
            - Only include information that was found in the source research
            """
            
            # Generate synthesis using lead researcher
            synthesis_response = self.lead_researcher(synthesis_prompt)
            
            return "".join(map(extract_content_text, synthesis_response.message["content"]))
            
        except Exception as e:
            research_logger.error(f"Failed to create master synthesis: {e}")
            return f"Error creating master synthesis: {e}"
    
    async def research_subtopic(self, subtopic: str, agent_id: int) -> Dict[str, Any]:
        """
        Use a subagent to research a specific subtopic with improved error handling
        """
        agent = self.subagents[agent_id % len(self.subagents)]
        
        try:
            # Perform real web search with caching
            raw_search_data = await web_search(subtopic, count=5)
            
            # Convert to expected format for compatibility
            search_results = {
                "query": subtopic,
                "results": [
                    {
                        "title": result.get("title", ""),
                        "snippet": result.get("description", ""),
                        "url": result.get("url", "")
                    }
                    for result in raw_search_data.get("results", [])
                ]
            }
            
            # Log search success
            research_logger.info(f"Search completed for '{subtopic}': {len(search_results['results'])} results found")
            
        except Exception as e:
            # Handle search failures gracefully
            research_logger.error(f"Search failed for '{subtopic}': {e}")
            search_results = {
                "query": subtopic,
                "results": [],
                "error": str(e)
            }
        
        try:
            # Create standardized research prompt with consistent formatting
            prompt = ReportFormatter.create_standard_prompt(subtopic, search_results)
            
            # Generate research summary
            research_summary = agent(prompt)
            
            # Log research completion
            research_logger.info(f"Research completed for '{subtopic}' by agent {agent_id}")
            
        except Exception as e:
            # Handle AI generation failures
            research_logger.error(f"Research generation failed for '{subtopic}': {e}")
            research_summary = {
                "message": {
                    "content": [{"text": f"Error generating research summary: {e}"}]
                }
            }
        
        return {
            "subtopic": subtopic,
            "agent_id": agent_id,
            "search_results": search_results,
            "research_summary": research_summary
        }
    
    async def conduct_research(self, main_topic: str) -> Dict[str, Any]:
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
        print("\n🔍 Delegating research to subagents...")
        research_tasks = [
            self.research_subtopic(subtopic, i) 
            for i, subtopic in enumerate(subtopics)
        ]
        
        research_results = await asyncio.gather(*research_tasks)
        
        # Step 3: Create master synthesis report
        print("\n📊 Creating master synthesis report...")
        master_synthesis = self.create_master_synthesis(main_topic, research_results)
        
        # Step 3.5: Add cross-references and table of contents
        print("🔗 Adding cross-references and table of contents...")
        master_synthesis = ReportFormatter.add_cross_references(master_synthesis, research_results)
        
        # Step 4: Compile final report
        print("✅ Compiling final research package...")
        final_report = {
            "main_topic": main_topic,
            "subtopics_count": len(subtopics),
            "subtopic_research": research_results,
            "master_synthesis": master_synthesis,
            "summary": f"Comprehensive research conducted on '{main_topic}' across {len(subtopics)} specialized areas with master synthesis.",
            "generated_at": datetime.now().isoformat()
        }
        
        return final_report


async def main():
    """
    Test the research orchestration system
    """
    orchestrator = ResearchOrchestrator()
    
    test_topic = "Imaginarium Theatre Optimization Strategies in Genshin Impact"
    
    print("🚀 Research Orchestration System Test")
    print("=" * 50)
    
    try:
        results = await orchestrator.conduct_research(test_topic)
        
        print("\n✨ Research Complete!")
        print(f"📋 Final Report Summary:")
        print(f"   Main Topic: {results['main_topic']}")
        print(f"   Subtopics Researched: {results['subtopics_count']}")
        print(f"   Generated At: {results['generated_at']}")
        
        # Display master synthesis
        print(f"\n🎯 MASTER SYNTHESIS REPORT:")
        print("=" * 60)
        print(results['master_synthesis'])
        print("=" * 60)
        
        print(f"\n📚 Individual Subtopic Research:")
        for i, research in enumerate(results['subtopic_research'], 1):
            print(f"\n--- Subtopic {i}: {research['subtopic']} ---")
            print(f"Agent ID: {research['agent_id']}")
            
            # Extract text content safely from AI response
            research_summary = research['research_summary']
            if hasattr(research_summary, 'message'):
                summary_text = "".join(map(extract_content_text, research_summary.message["content"]))
            else:
                # Handle dict format
                summary_text = "".join(map(extract_content_text, research_summary.get("message", {}).get("content", [])))
            print(f"Research Summary Preview: {summary_text[:200]}...")
            # Don't print full summary since we have master synthesis now
        
    except Exception as e:
        print(f"❌ Error during research: {e}")


if __name__ == "__main__":
    asyncio.run(main())
