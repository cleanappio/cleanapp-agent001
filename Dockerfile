# Builder stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r cleanapp && useradd -r -g cleanapp cleanapp

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/cleanapp/.local

# Copy application code
COPY src/ src/
COPY hello_world/ hello_world/
COPY scripts/ scripts/

# Create data directory with correct permissions
RUN mkdir -p data && chown cleanapp:cleanapp data

# Set ownership
RUN chown -R cleanapp:cleanapp /app

# Switch to non-root user
USER cleanapp

# Set environment variables
ENV PATH=/home/cleanapp/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the agent
CMD ["python", "-m", "src"]
