FROM python:3.12-slim

RUN apt-get update && apt-get install -y git

COPY requirements.txt .

#for prod
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt 
# RUN pip install --upgrade pip && pip install  -r requirements.txt

WORKDIR /app
COPY scripts ./scripts
COPY cli.sh .
RUN chmod +x cli.sh


ENTRYPOINT ["./cli.sh"]

