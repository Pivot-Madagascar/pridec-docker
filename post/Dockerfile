FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

COPY entrypoint.py .
RUN chmod +x /app/entrypoint.py

RUN pip install --upgrade pip && pip install -r requirements.txt

# we do this to protect the production instance
# You must use `docker run -e DRYRUN=false post` to override
# ENV DRYRUN=true

ENTRYPOINT ["python", "/app/entrypoint.py"]