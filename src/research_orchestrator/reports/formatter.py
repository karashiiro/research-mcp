"""
Research Report Formatting Module
Provides standardized templates and formatting for research reports
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ReportSection:
    """Structure for a research report section"""
    title: str
    content: str
    subsections: Optional[List['ReportSection']] = None


class ReportFormatter:
    """
    Standardizes formatting for research reports to ensure consistency
    across all generated content
    """
    
    @staticmethod
    def create_standard_prompt(subtopic: str, search_results: Dict[str, Any]) -> str:
        """
        Create a standardized prompt for research agents that enforces
        consistent formatting and citation style
        """
        
        # Format search results with numbered references
        formatted_sources = ReportFormatter._format_sources_for_prompt(search_results)
        
        prompt = f"""
        Research the topic: "{subtopic}"
        
        Based on these search results:
        {formatted_sources}
        
        Provide a comprehensive research summary using this EXACT format:

        # Research Report
        **Topic:** *{subtopic}*

        ---

        ## 1. Executive Summary
        [Provide a word executive summary that captures the key insights]

        ---

        ## 2. Key Findings & Insights

        | Finding | Source | Implication |
        |---------|--------|-------------|
        | [Key finding 1] | [Source number, e.g., [1]] | [What this means for the field] |
        | [Key finding 2] | [Source number, e.g., [2]] | [What this means for the field] |

        ---

        ## 3. Important Facts & Statistics

        | Metric | Value | Source |
        |--------|-------|--------|
        | [Specific metric] | [Specific value] | [Source number, e.g., [1]] |
        | [Specific metric] | [Specific value] | [Source number, e.g., [2]] |

        *Note: Only include statistics that are explicitly mentioned in the source material.*

        ---

        ## 4. Current Trends & Developments

        1. **[Trend Name]**
           - [Description based on source material]
           - Source: [Source number]

        2. **[Trend Name]**
           - [Description based on source material]  
           - Source: [Source number]

        ---

        ## 5. Potential Implications & Applications

        | Domain | Application | Quantum Advantage/Benefit |
        |--------|-------------|---------------------------|
        | [Domain name] | [Specific application] | [Specific benefit from sources] |
        | [Domain name] | [Specific application] | [Specific benefit from sources] |

        ---

        ## 6. Conclusion

        [2-3 sentence conclusion summarizing the key takeaways from the research]

        ---

        ## 7. References

        [List all sources in numbered format]

FORMATTING REQUIREMENTS:
        - Follow the exact format shown above
        - Use only information from the provided sources
        - Keep executive summary concise and factual
        """
        
        return prompt
    
    @staticmethod
    def _format_sources_for_prompt(search_results: Dict[str, Any]) -> str:
        """Format search results with numbered citations for the prompt"""
        
        if not search_results.get("results"):
            return "No search results available."
        
        formatted = f"Query: {search_results.get('query', 'Unknown')}\n\n"
        formatted += "Sources:\n"
        
        for i, result in enumerate(search_results["results"], 1):
            title = result.get("title", "No title")
            snippet = result.get("snippet", "No description available")
            url = result.get("url", "No URL")
            
            formatted += f"[{i}] **{title}**\n"
            formatted += f"    URL: {url}\n"
            formatted += f"    Description: {snippet}\n\n"
        
        return formatted
    
    @staticmethod
    def create_master_synthesis_template(main_topic: str, subtopic_count: int) -> str:
        """
        Template for creating a master synthesis document that combines
        all subtopic research into a cohesive report
        """
        
        prompt = f"""
        Create a master synthesis report for: "{main_topic}"
        
        You will be provided with {subtopic_count} detailed research reports on different aspects of this topic.
        Your task is to synthesize these into a comprehensive master report using this structure:

        # Comprehensive Research Report
        **Topic:** *{main_topic}*
        **Date:** [Current date]

        ---

        ## Executive Summary
        [300-400 word synthesis of all key findings across subtopics]

        ---

        ## 1. Introduction & Background
        [Overview of the field and why this topic matters]

        ---

        ## 2. Key Findings by Area

        ### 2.1 [Subtopic 1 Name]
        - [Key insights]
        - [Important statistics]

        ### 2.2 [Subtopic 2 Name]  
        - [Key insights]
        - [Important statistics]

        [Continue for all subtopics...]

        ---

        ## 3. Cross-Cutting Themes
        [Identify patterns and connections across subtopics]

        ---

        ## 4. Current State of the Field
        [Synthesis of current trends and developments]

        ---

        ## 5. Future Directions & Implications
        [Combined implications and applications from all areas]

        ---

        ## 6. Conclusion
        [Synthesis of overall findings and outlook]

        ---

        ## 7. Comprehensive Bibliography
        [All sources from all subtopic reports, organized and deduplicated]

        SYNTHESIS REQUIREMENTS:
        - Draw connections between different subtopic areas
        - Identify overarching themes and patterns
        - Avoid duplication of content from individual reports
        - Maintain consistent citation format [1], [2], etc.
        - Focus on synthesis rather than summarization
        """
        
        return prompt
    
    @staticmethod
    def extract_and_deduplicate_sources(research_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract all sources from research results and deduplicate them
        for the master bibliography
        """
        
        all_sources = []
        seen_urls = set()
        
        for result in research_results:
            search_results = result.get("search_results", {})
            for source in search_results.get("results", []):
                url = source.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_sources.append({
                        "title": source.get("title", "No title"),
                        "url": url,
                        "description": source.get("snippet", "No description")
                    })
        
        return all_sources
    
    @staticmethod
    def add_cross_references(master_synthesis: str, subtopic_research: List[Dict[str, Any]]) -> str:
        """
        Add cross-references and table of contents to the master synthesis
        """
        
        # Extract subtopic names for cross-referencing
        subtopic_names = [research["subtopic"] for research in subtopic_research]
        
        # Create table of contents
        toc = "\n## Table of Contents\n"
        toc += "1. [Executive Summary](#executive-summary)\n"
        toc += "2. [Introduction & Background](#1-introduction--background)\n"
        toc += "3. [Key Findings by Research Area](#2-key-findings-by-research-area)\n"
        
        for i, subtopic in enumerate(subtopic_names, 1):
            # Create anchor-friendly name
            anchor = subtopic.lower().replace(" ", "-").replace("&", "and")
            anchor = "".join(c for c in anchor if c.isalnum() or c in "-")
            toc += f"   - [{subtopic}](#2{i}-{anchor})\n"
        
        toc += "4. [Cross-Cutting Themes & Patterns](#3-cross-cutting-themes--patterns)\n"
        toc += "5. [Current State of the Field](#4-current-state-of-the-field)\n"
        toc += "6. [Future Directions & Implications](#5-future-directions--implications)\n"
        toc += "7. [Conclusion](#6-conclusion)\n"
        toc += "8. [Comprehensive Bibliography](#7-comprehensive-bibliography)\n"
        
        # Insert TOC after the title but before Executive Summary
        lines = master_synthesis.split('\n')
        toc_inserted = False
        enhanced_lines = []
        
        for line in lines:
            enhanced_lines.append(line)
            if not toc_inserted and line.startswith("---") and len(enhanced_lines) > 3:
                enhanced_lines.append(toc)
                enhanced_lines.append("---")
                toc_inserted = True
        
        # Join back together
        enhanced_synthesis = '\n'.join(enhanced_lines)
        
        # Add cross-references between sections
        for i, subtopic in enumerate(subtopic_names):
            # Add references to related subtopics
            related_pattern = f"(related to|connection with|builds on|complements)"
            # This is a simple approach - in a more sophisticated system,
            # we could use NLP to find actual semantic relationships
            
        return enhanced_synthesis
    
    @staticmethod
    def validate_report_format(report_text: str) -> Dict[str, bool]:
        """
        Validate that a research report follows the standard format
        Returns a dict indicating which formatting requirements are met
        """
        
        validation = {
            "has_title": "# Research Report" in report_text,
            "has_executive_summary": "## 1. Executive Summary" in report_text,
            "has_key_findings": "## 2. Key Findings" in report_text,
            "has_statistics": "## 3. Important Facts" in report_text,
            "has_trends": "## 4. Current Trends" in report_text,
            "has_implications": "## 5. Potential Implications" in report_text,
            "has_conclusion": "## 6. Conclusion" in report_text,
            "has_references": "## 7. References" in report_text,
            "has_tables": "|" in report_text and "---" in report_text,
            "has_citations": "[1]" in report_text or "[2]" in report_text
        }
        
        return validation


def format_research_cache_key(query: str) -> str:
    """Create a standardized cache key for research results"""
    # Remove special characters and normalize
    import re
    normalized = re.sub(r'[^\w\s-]', '', query.lower())
    normalized = re.sub(r'\s+', '_', normalized.strip())
    return f"research_{normalized}"
