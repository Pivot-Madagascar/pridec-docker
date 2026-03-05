FROM python:3.12-slim

WORKDIR /app

COPY pridec_etl ./pridec_etl
COPY requirements.txt .

COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

RUN pip install --upgrade pip && pip install -r requirements.txt
