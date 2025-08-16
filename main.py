from strands import Agent
from strands.models.ollama import OllamaModel

# Create an Ollama model instance
ollama_model = OllamaModel(
    host="http://localhost:11434",
    model_id="gpt-oss:20b",
    temperature=0.3
)

# Create an agent with default settings
agent = Agent(model=ollama_model)

# Ask the agent a question
agent("Tell me about agentic AI")
