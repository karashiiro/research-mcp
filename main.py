import asyncio
import json
import logging
import os
import re
import unicodedata
from typing import List, Dict, Any
from dotenv import load_dotenv
from strands import Agent
from strands.types.content import ContentBlock
from strands.models.bedrock import BedrockModel
from strands.models.model import Model
from strands.models.ollama import OllamaModel
from web_search import web_search

# Load environment variables from .env file
load_dotenv()

# Configure strands logging to write to file instead of console
def setup_logging():
    """Configure strands logging to write to files to avoid unicode console issues."""
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
    temperature = float(os.getenv("MODEL_TEMPERATURE", 0.3))
    if os.getenv("MODEL_TYPE") == "ollama":
        return OllamaModel(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            model_id=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
            temperature=temperature
        )
    else:
        return BedrockModel(
            model_id=os.getenv("BEDROCK_MODEL", "openai.gpt-oss-20b-1:0"),
            temperature=temperature
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
        
        # Create the lead researcher agent
        self.lead_researcher = Agent(model=self.model)
        
        # Pool of subagents for research tasks
        self.subagents = []
        for _ in range(5):  # Create 5 subagents
            self.subagents.append(Agent(model=self.model))
    
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
    
    async def research_subtopic(self, subtopic: str, agent_id: int) -> Dict[str, Any]:
        """
        Use a subagent to research a specific subtopic
        """
        agent = self.subagents[agent_id % len(self.subagents)]
        
        # Perform real web search
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
        
        # Create research prompt with search results
        prompt = f"""
        Research the topic: "{subtopic}"
        
        Based on these search results:
        {json.dumps(search_results, indent=2)}
        
        Provide a comprehensive research summary that includes:
        1. Key findings and insights
        2. Important facts and statistics
        3. Current trends or developments
        4. Potential implications or applications
        
        Format your response as a structured research report.
        """
        
        research_summary = agent(prompt)
        
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
        safe_print(f"🔬 Starting research orchestration for: {main_topic}")
        
        # Step 1: Generate subtopics
        safe_print("📝 Generating subtopics...")
        subtopics = self.generate_subtopics(main_topic)
        safe_print(f"✅ Generated {len(subtopics)} subtopics:")
        for i, subtopic in enumerate(subtopics, 1):
            safe_print(f"   {i}. {subtopic}")
        
        # Step 2: Research each subtopic in parallel
        safe_print("\n🔍 Delegating research to subagents...")
        research_tasks = [
            self.research_subtopic(subtopic, i) 
            for i, subtopic in enumerate(subtopics)
        ]
        
        research_results = await asyncio.gather(*research_tasks)
        
        # Step 3: Compile final report
        safe_print("\n📊 Compiling research results...")
        final_report = {
            "main_topic": main_topic,
            "subtopics_count": len(subtopics),
            "subtopic_research": research_results,
            "summary": f"Comprehensive research conducted on '{main_topic}' across {len(subtopics)} specialized areas."
        }
        
        return final_report


def safe_print(text: str) -> None:
    """Print text safely and also log to file with full unicode support."""
    # Log to file with full unicode support
    research_logger.info(text)
    
    # Also print to console with unicode handling
    try:
        # NFKD normalization decomposes characters and converts compatibility variants
        normalized = unicodedata.normalize('NFKD', text)
        # Convert to ASCII with fallback for any remaining unicode
        ascii_text = normalized.encode('ascii', errors='replace').decode('ascii')
        print(ascii_text)
    except Exception:
        # Ultimate fallback - just print what we can
        try:
            safe_text = str(text).encode('ascii', errors='replace').decode('ascii')
            print(safe_text)
        except Exception:
            print("[Unable to display text due to encoding issues]")


async def main():
    """
    Test the research orchestration system
    """
    orchestrator = ResearchOrchestrator()
    
    test_topic = "Quantum Computing Applications in Machine Learning"
    
    safe_print("🚀 Research Orchestration System Test")
    safe_print("=" * 50)
    
    try:
        results = await orchestrator.conduct_research(test_topic)
        
        safe_print("\n✨ Research Complete!")
        safe_print(f"📋 Final Report Summary:")
        safe_print(f"   Main Topic: {results['main_topic']}")
        safe_print(f"   Subtopics Researched: {results['subtopics_count']}")
        
        safe_print(f"\n📚 Detailed Research Results:")
        for i, research in enumerate(results['subtopic_research'], 1):
            safe_print(f"\n--- Subtopic {i}: {research['subtopic']} ---")
            safe_print(f"Agent ID: {research['agent_id']}")
            
            # Extract text content safely from AI response
            summary_text = "".join(map(extract_content_text, research['research_summary'].message["content"]))
            safe_print(f"Research Summary Preview: {summary_text[:200]}...")
            safe_print(f"\nFull Research Summary:")
            safe_print(summary_text)
        
    except Exception as e:
        safe_print(f"❌ Error during research: {e}")


if __name__ == "__main__":
    asyncio.run(main())
