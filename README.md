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
    participant Agent1 as Research Agent 1
    participant Agent2 as Research Agent 2
    participant Agent3 as Research Agent 3
    participant Agent4 as Research Agent 4
    participant Agent5 as Research Agent 5
    participant Synthesis as Synthesis Agent

    Client->>Server: conduct_research(topic)
    Server->>Orchestrator: create_research_job(topic)
    
    Orchestrator->>Lead: generate_subtopics(topic)
    Lead->>Cache: check_cache(topic)
    Cache-->>Lead: cache_miss
    Lead->>Web: search(topic)
    Web-->>Lead: search_results
    Lead->>Cache: store_results(topic, results)
    Lead-->>Orchestrator: subtopics[1..5]
    
    par Parallel Research Phase
        Orchestrator->>Agent1: research(subtopic_1)
        Agent1->>Cache: check_cache(subtopic_1)
        Cache-->>Agent1: cache_miss
        Agent1->>Web: search(subtopic_1)
        Web-->>Agent1: search_results
        Agent1->>Cache: store_results(subtopic_1, results)
        Agent1-->>Orchestrator: research_report_1
    and
        Orchestrator->>Agent2: research(subtopic_2)
        Agent2->>Cache: check_cache(subtopic_2)
        Cache-->>Agent2: cache_hit
        Cache-->>Agent2: cached_results
        Agent2-->>Orchestrator: research_report_2
    and
        Orchestrator->>Agent3: research(subtopic_3)
        Agent3->>Cache: check_cache(subtopic_3)
        Cache-->>Agent3: cache_miss
        Agent3->>Web: search(subtopic_3)
        Web-->>Agent3: search_results
        Agent3->>Cache: store_results(subtopic_3, results)
        Agent3-->>Orchestrator: research_report_3
    and
        Orchestrator->>Agent4: research(subtopic_4)
        Agent4->>Cache: check_cache(subtopic_4)
        Cache-->>Agent4: cache_miss
        Agent4->>Web: search(subtopic_4)
        Web-->>Agent4: search_results
        Agent4->>Cache: store_results(subtopic_4, results)
        Agent4-->>Orchestrator: research_report_4
    and
        Orchestrator->>Agent5: research(subtopic_5)
        Agent5->>Cache: check_cache(subtopic_5)
        Cache-->>Agent5: cache_miss
        Agent5->>Web: search(subtopic_5)
        Web-->>Agent5: search_results
        Agent5->>Cache: store_results(subtopic_5, results)
        Agent5-->>Orchestrator: research_report_5
    end
    
    Orchestrator->>Synthesis: synthesize_reports(all_reports)
    Synthesis-->>Orchestrator: master_research_report
    
    Orchestrator-->>Server: complete_research_report
    Server-->>Client: research_report_with_citations
```
