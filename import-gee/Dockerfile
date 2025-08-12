FROM python:3.12-slim

RUN apt-get update && apt-get install -y git

WORKDIR app/

RUN git clone https://github.com/Pivot-Madagascar/pridec-gee.git .

# RUN python3 -m venv .venv --prompt="pridec-gee"
# RUN source .venv/bin/activate

RUN pip install --upgrade pip && pip install -r requirements.txt

ENTRYPOINT ["python", "fetch_all_climate_pridec.py"]