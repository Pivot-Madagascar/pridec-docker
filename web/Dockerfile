FROM python:3.12-slim

RUN apt-get update && apt-get install -y git

WORKDIR /app

# Copy the web directory contents
COPY . .

# Install dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Run the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]