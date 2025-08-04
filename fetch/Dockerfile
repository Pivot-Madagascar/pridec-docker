FROM python:3.10-slim

WORKDIR /app

COPY scripts ./scripts
COPY requirements.txt .

COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

RUN pip install --upgrade pip && pip install -r requirements.txt

ENTRYPOINT ["/app/entrypoint.sh"]