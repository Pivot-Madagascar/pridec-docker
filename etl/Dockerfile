FROM python:3.12-slim

RUN apt-get update && apt-get install -y git

WORKDIR /app

COPY scripts ./scripts
COPY requirements.txt .

COPY cli.sh .
RUN chmod +x cli.sh

# RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt #for prod
RUN pip install --upgrade pip && pip install  -r requirements.txt

ENTRYPOINT ["./cli.sh"]
