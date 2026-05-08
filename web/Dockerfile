FROM python:3.12-slim

# Install docker CLI (for running forecast containers) and git
RUN apt-get update && apt-get install -y git docker.io

WORKDIR /app

# Copy entire project (excluding volumes/secrets via .dockerignore)
COPY . .

# Install Python dependencies from web/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r web/requirements.txt

# Expose port
EXPOSE 8000

# Run the FastAPI app (module is web.main)
CMD ["uvicorn", "web.main:app", "--host", "0.0.0.0", "--port", "8000"]