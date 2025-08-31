# (WIP) Deep Research MCP Server

A research orchestration MCP server. This system implements a hierarchical research architecture where a lead researcher coordinates multiple specialized research agents to conduct investigations on complex topics, generating detailed reports with proper citations and analysis.

Modeled loosely after Claude's [Research Tool](https://www.anthropic.com/engineering/multi-agent-research-system).

## Quick Start

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Brave Search API key
- AWS Bedrock access (recommended) or Ollama setup

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd research-mcp
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and model settings
   ```

### Environment Variables

```bash
# Required: Brave Search API
BRAVE_API_KEY=your_brave_api_key_here

# Model Configuration
MODEL_TYPE=bedrock  # or "ollama"

# For Bedrock (recommended)
BEDROCK_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_REGION=us-east-1

# For Ollama (alternative)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=your_model_name
```

## Usage

### MCP Server

**Start the MCP server:**
```bash
uv run mcp dev src/mcp_server/server.py
```

**Use via MCP client:**
The server provides a `conduct_research` tool that accepts a topic string and returns a research report.

### Using Docker (with Bedrock backend)

Create a `.env` file with appropriate environment variables, and then
Add the following command to your MCP configuration:

```bash
docker run -i --rm -v /path/to/your.env:/app/.env:ro -v /home/you/.aws:/home/mcp/.aws ghcr.io/karashiiro/research-mcp:main
```

## Advanced Usage

**Clear cache (for fresh web searches):**
```bash
rm -rf cache/
```

**View research progress logs:**
```bash
cat logs/research_results.log
```

## Architecture

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant Server as MCP Server
    participant Orchestrator as Research Orchestrator
    participant Lead as Lead Researcher
    participant Cache as Search Cache
    participant Web as Web Search API
    participant Pool as Research Agent Pool
    participant Citations as Citation Processor
    participant Synthesis as Synthesis Agent

    Client->>Server: conduct_research(topic)
    Server->>Orchestrator: create_research_job(topic)
    
    Orchestrator->>Lead: generate_subtopics(topic)
    Lead->>Cache: check_cache(topic)
    alt cache miss
        Lead->>Web: search(topic)
        Web-->>Lead: search_results
        Lead->>Cache: store_results(topic, results)
    else cache hit
        Cache-->>Lead: cached_results
    end
    Lead-->>Orchestrator: subtopics[2..5]
    
    loop for each subtopic
        Orchestrator->>Pool: research(subtopic_n)
        Pool->>Cache: check_cache(subtopic_n)
        alt cache miss
            Pool->>Web: search(subtopic_n)
            Web-->>Pool: search_results
            Pool->>Cache: store_results(subtopic_n, results)
        else cache hit
            Cache-->>Pool: cached_results
        end
        Pool-->>Orchestrator: research_report_n
    end
    
    opt refinement needed
        Orchestrator->>Lead: generate_additional_subtopics()
        Lead-->>Orchestrator: refined_subtopics
        loop refined research
            Orchestrator->>Pool: research(refined_subtopic)
            Pool->>Web: search(refined_subtopic)
            Web-->>Pool: search_results
            Pool-->>Orchestrator: refined_report
        end
    end
    
    Orchestrator->>Citations: process_citations(all_reports)
    Citations-->>Orchestrator: formatted_citations
    
    Orchestrator->>Synthesis: synthesize_reports(reports, citations)
    Synthesis-->>Orchestrator: master_research_report
    
    Orchestrator-->>Server: complete_research_report
    Server-->>Client: research_report_with_citations
```
