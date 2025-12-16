# =========================================
# 1. Builder Stage
# =========================================
FROM python:3.11-slim AS builder

# Install uv
RUN pip install uv

WORKDIR /app

# Copy only dependency definitions first (better caching)
COPY pyproject.toml uv.lock ./

# Install dependencies into a .venv inside the project
RUN uv sync --frozen --no-dev

# Copy all project files
COPY . .

# =========================================
# 2. Runtime Stage
# =========================================
FROM python:3.11-slim AS runtime

# Create a non-root user
RUN useradd -m appuser

WORKDIR /app

# Install uv in the runtime environment
RUN pip install uv

# Copy everything from builder (including .venv)
COPY --from=builder /app /app

# Use uv’s virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER appuser

# Expose FastAPI port
EXPOSE 8080

# Production server
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
