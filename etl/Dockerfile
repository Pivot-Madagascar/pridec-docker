FROM python:3.12-slim

WORKDIR /app

COPY scripts ./scripts
COPY requirements.txt .

COPY cli.sh .
RUN chmod +x /app/cli.sh

RUN pip install --upgrade pip && pip install -r requirements.txt

ENTRYPOINT ["app/cli.sh"]
