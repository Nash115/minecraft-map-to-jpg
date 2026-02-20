FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential python3-dev gcc g++ make
RUN rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get purge -y build-essential python3-dev gcc g++ make
RUN apt-get autoremove -y

COPY ./tools/*.py ./tools/
COPY ./main.py .

CMD ["python", "main.py"]