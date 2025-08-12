FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .


COPY analytics.py .
COPY post.py .

RUN pip install --upgrade pip && pip install -r requirements.txt

# we do this to protect the production instance
# You must use `docker run -e DRYRUN=false post` to override
# ENV DRYRUN=true

#run by specifying which script to use
# docker compose run --env DRYRUN=false --rm post analytics.py
# docker compose run --env DRYRUN=true --rm post post.py

ENTRYPOINT ["python"]