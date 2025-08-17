# Multi-stage build for optimized research MCP server
FROM python:3.12-slim AS builder

# Install UV package manager for faster dependency resolution
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies in a virtual environment
RUN uv sync --frozen --no-cache

FROM python:3.12-slim AS runtime

# Install curl for health checks (if needed)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash mcp

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY src/ ./src/
COPY cli/ ./cli/

# Create required directories
RUN mkdir -p logs cache && chown -R mcp:mcp /app

# Switch to non-root user
USER mcp

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set Python path to find local modules
ENV PYTHONPATH="/app/src:/app"

# Expose port for MCP server (if using stdio transport, this may not be needed)
# EXPOSE 8000

# Health check (optional - adjust based on your health endpoint)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#   CMD curl -f http://localhost:8000/health || exit 1

# Default command to run the MCP server
CMD ["python", "-m", "mcp_server.server"]