FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .


COPY scripts/ ./scripts/
COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

RUN pip install --upgrade pip && pip install -r requirements.txt

# we do this to protect the production instance
# You must use `docker run -e DRYRUN=false post` to override
# ENV DRYRUN=true

#run with --analytics flag to launch analytics table
# docker compose run --env DRYRUN=false --rm post --analytics

ENTRYPOINT ["/app/entrypoint.sh"]