FROM python:3.12-slim

WORKDIR /app

COPY utils ./utils
COPY COMcases.py . 
COPY CSBcases.py . 
COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

#examples of commands to run via docker compose run

ENTRYPOINT ["python"]

#just provide name of script to docker compose run
# docker compose run import-pivot-data COMcases.py
# docker compose run import-pivot-data CSBcases.py