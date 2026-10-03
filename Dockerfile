FROM python:3.12-slim

# Install system dependencies including curl to fetch OPA binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download official static OPA binary
RUN curl -L -o /usr/local/bin/opa https://openpolicyagent.org/downloads/v0.68.0/opa_linux_amd64_static \
    && chmod 755 /usr/local/bin/opa

WORKDIR /app

# Install Python backend dependencies
COPY backend/pyproject.toml /app/
RUN pip install --no-cache-dir --upgrade pip setuptools \
    && pip install --no-cache-dir -e .

# Copy policies and backend source code
COPY policies /app/policies
COPY backend /app

# Prepare entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Expose FastAPI port
EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV OPA_URL="http://127.0.0.1:8181"

ENTRYPOINT ["/app/entrypoint.sh"]
