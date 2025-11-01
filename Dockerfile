FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY main.py .
COPY local_agent.py .
COPY cloud_agent_wrapper.py .
COPY prompt_enhancer.py .
COPY local_bridge.pyw .

COPY reaper_all_actions.txt .
COPY reaper_actions.txt .
COPY reaper_plugins_list.txt .
COPY sound_knowledge_base.json .
COPY action_index.json .

# Expose port
EXPOSE 8080

# Run the application (main site + agent API)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]