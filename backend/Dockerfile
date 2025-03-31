FROM python:3.11-slim

# Create a working directory
WORKDIR /app

# Copy requirements first, install
COPY pyproject.toml .
RUN pip install .

# Copy source code
COPY app/ /app

# Expose the port if needed
EXPOSE 8000

# Default environment variables can be set here or in docker-compose
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
