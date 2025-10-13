FROM python:3.12.3-slim
RUN apt-get update && apt-get install build-essential -y

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

RUN chmod a+x run.sh
